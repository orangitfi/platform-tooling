#!/usr/bin/env python3
"""
Publish Markdown files from a directory to Confluence Cloud.
Preserves folder structure as page hierarchy.

Supports:
  - Mermaid diagrams: pre-rendered to PNG via mmdc, uploaded as attachments
  - Local images: uploaded as Confluence attachments
  - Tables, fenced code blocks
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from atlassian import Confluence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def prefixed(title, prefix):
    """Prepend prefix to a page title, or return the title unchanged if prefix is empty."""
    return f"{prefix}{title}" if prefix else title


def folder_page_title(docs_dir, folder_path):
    """
    Derive a space-unique Confluence page title for a folder.

    Confluence titles must be unique across the whole space, so we use the full
    relative path rather than just the leaf name.  Each path part has its numeric
    prefix stripped and is title-cased, then parts are joined with ' / '.

    Examples:
        docs/adr          -> "Adr"
        docs/poc/adr      -> "Poc / Adr"
        docs/00-intro     -> "Intro"
        docs/poc/00-intro -> "Poc / Intro"
    """
    rel = folder_path.relative_to(docs_dir)
    parts = []
    for part in rel.parts:
        if part and part[0].isdigit() and "-" in part:
            part = part.split("-", 1)[1]
        parts.append(part.replace("-", " ").title())
    return " / ".join(parts)


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------

def render_mermaid_diagrams(md_content, tmp_dir):
    """
    Find all ```mermaid ... ``` blocks in the markdown, render each to a PNG
    file in tmp_dir using mmdc, and return:
      - modified md_content with blocks replaced by ![mermaid-N](path/to/N.png)
      - list of (attachment_name, png_path) tuples for later upload
    """
    pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)
    attachments = []
    counter = [0]

    def replace_block(m):
        idx = counter[0]
        counter[0] += 1
        diagram_src = m.group(1)
        mmd_file = Path(tmp_dir) / f"mermaid-{idx}.mmd"
        png_file = Path(tmp_dir) / f"mermaid-{idx}.png"
        mmd_file.write_text(diagram_src, encoding="utf-8")

        try:
            subprocess.run(
                ["mmdc", "-i", str(mmd_file), "-o", str(png_file), "--backgroundColor", "white"],
                check=True,
                capture_output=True,
            )
            attachment_name = f"mermaid-{idx}.png"
            attachments.append((attachment_name, png_file))
            # Replace fenced block with a local image reference that will be
            # picked up by the image-upload step below.
            return f"![{attachment_name}]({png_file})"
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            print(f"  Warning: mmdc failed for diagram {idx}: {stderr.strip()}")
            # Fall back: keep the block as a fenced code block so at least
            # the source is visible.
            return m.group(0)
        except FileNotFoundError:
            print("  Warning: mmdc not found — Mermaid diagrams will not be rendered.")
            return m.group(0)

    modified = pattern.sub(replace_block, md_content)
    return modified, attachments


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------

def collect_local_images(md_content, md_file_path):
    """
    Find all local image references in markdown (![alt](path)) and return a
    list of (alt, abs_path, original_ref) tuples.  Remote URLs are skipped.
    """
    pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    images = []
    for m in pattern.finditer(md_content):
        alt, ref = m.group(1), m.group(2)
        if ref.startswith("http://") or ref.startswith("https://"):
            continue
        abs_path = (md_file_path.parent / ref).resolve()
        if abs_path.exists():
            images.append((alt, abs_path, ref))
        else:
            print(f"  Warning: image not found, skipping: {ref}")
    return images


def upload_attachments(conf, page_id, attachments):
    """
    Upload a list of (attachment_name, file_path) to a Confluence page.
    Returns a set of successfully uploaded attachment names.
    """
    uploaded = set()
    for name, path in attachments:
        try:
            conf.attach_file(
                str(path),
                name=name,
                page_id=page_id,
                content_type="image/png",
            )
            uploaded.add(name)
            print(f"  ✓ Uploaded attachment: {name}")
        except Exception as e:
            print(f"  Warning: could not upload {name}: {e}")
    return uploaded


def replace_images_with_ac_macros(html_content, image_map):
    """
    Replace <img src="..."> tags whose src maps to an uploaded Confluence
    attachment with Confluence <ac:image> storage-format macros.

    image_map: dict of {original_ref_or_abs_path_str: attachment_name}
    """
    def replace_img(m):
        src = m.group(1)
        alt = m.group(2) if m.group(2) else ""
        # Try exact match first, then basename
        name = image_map.get(src) or image_map.get(Path(src).name)
        if name:
            return (
                f'<ac:image ac:alt="{alt}">'
                f'<ri:attachment ri:filename="{name}" />'
                f'</ac:image>'
            )
        return m.group(0)

    # Match both <img src="..." alt="..."> and <img alt="..." src="...">
    html_content = re.sub(
        r'<img\s+src="([^"]+)"(?:\s+alt="([^"]*)")?[^>]*/?>',
        replace_img,
        html_content,
    )
    html_content = re.sub(
        r'<img\s+alt="([^"]*)"(?:\s+src="([^"]+)")?[^>]*/?>',
        lambda m: replace_img(type('M', (), {
            'group': lambda self, n: m.group(2) if n == 1 else m.group(1),
            '__call__': lambda self: None,
        })()) if m.group(2) else m.group(0),
        html_content,
    )
    return html_content


# ---------------------------------------------------------------------------
# Confluence page hierarchy
# ---------------------------------------------------------------------------

def get_or_create_folder_page(
    conf,
    space_key,
    folder_path,
    parent_id,
    folder_pages,
    docs_dir,
    confluence_prefix="",
):
    """Get or create a page for a folder"""
    folder_key = str(folder_path)
    if folder_key in folder_pages:
        return folder_pages[folder_key]

    title = prefixed(folder_page_title(docs_dir, folder_path), confluence_prefix)

    # Search for existing page among parent's children
    try:
        children = conf.get_page_child_by_type(
            parent_id, type="page", start=0, limit=100
        )
        for child in children:
            if child["title"] == title:
                print(f"  ✓ Found folder page: {title} (id: {child['id']})")
                folder_pages[folder_key] = child["id"]
                return child["id"]
    except Exception as e:
        print(f"  Warning: Could not check children: {e}")

    # Create folder page if not found
    print(f"  Creating folder page: {title} (under parent: {parent_id})")
    folder_page = conf.create_page(
        space=space_key,
        title=title,
        body=f"<p>This section contains documentation for {title}.</p>",
        parent_id=parent_id,
    )
    folder_pages[folder_key] = folder_page["id"]
    return folder_page["id"]


def get_nested_parent_id(
    conf,
    space_key,
    rel_path,
    docs_dir,
    root_page_id,
    folder_pages,
    confluence_prefix="",
):
    """Get parent page ID for nested folder structure"""
    if rel_path.parent == Path("."):
        return root_page_id

    parent_parts = rel_path.parent.parts
    current_parent_id = root_page_id

    for i, part in enumerate(parent_parts):
        folder_path = docs_dir / Path(*parent_parts[: i + 1])
        current_parent_id = get_or_create_folder_page(
            conf,
            space_key,
            folder_path,
            current_parent_id,
            folder_pages,
            docs_dir,
            confluence_prefix,
        )

    return current_parent_id


# ---------------------------------------------------------------------------
# Main publisher
# ---------------------------------------------------------------------------

def publish_docs(
    confluence_url,
    confluence_user,
    confluence_token,
    space_key,
    docs_path,
    root_page_title,
    confluence_prefix="",
):
    """Publish all markdown files to Confluence"""

    conf = Confluence(
        url=confluence_url,
        username=confluence_user,
        password=confluence_token,
        cloud=True,
    )

    # Get or create root page
    root_page_title_prefixed = prefixed(root_page_title, confluence_prefix)
    print(f"Setting up root page: {root_page_title_prefixed}")
    root_page = conf.get_page_by_title(space=space_key, title=root_page_title_prefixed)
    if root_page:
        print(f"✓ Found root page: {root_page_title_prefixed}")
        root_page_id = root_page["id"]
    else:
        print(f"Creating root page: {root_page_title_prefixed}")
        root_page = conf.create_page(
            space=space_key,
            title=root_page_title_prefixed,
            body="<p>This is the root documentation page. Content is auto-generated from GitHub.</p>",
        )
        if not root_page:
            raise RuntimeError(f"Failed to create root page: {root_page_title_prefixed}")
        print(f"✓ Created root page: {root_page_title_prefixed}")
        root_page_id = root_page["id"]

    folder_pages = {}
    docs_dir = Path(docs_path)
    md_files = list(docs_dir.rglob("*.md"))

    def sort_key(p):
        is_index = p.name == "index.md"
        depth = len(p.parts)
        return (not is_index, depth, str(p))

    md_files.sort(key=sort_key)
    print(f"\nPublishing {len(md_files)} files...\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        for md_file in md_files:
            if "template" in md_file.name.lower():
                print(f"Skipping template: {md_file.relative_to(docs_dir)}")
                continue

            rel_path = md_file.relative_to(docs_dir)
            print(f"\nPublishing {rel_path}...")

            with open(md_file, "r", encoding="utf-8") as f:
                md_content = f.read()

            # --- Mermaid: render diagrams to PNG, replace blocks with img refs ---
            md_content, mermaid_attachments = render_mermaid_diagrams(md_content, tmp_dir)

            # --- Collect local images referenced in markdown ---
            local_images = collect_local_images(md_content, md_file)
            all_attachments = mermaid_attachments + [
                (Path(ref).name, abs_path) for _, abs_path, ref in local_images
            ]

            # --- Extract title ---
            if md_content.startswith("# "):
                title = md_content.split("\n")[0].strip("# ")
            else:
                title = md_file.stem.replace("-", " ").title()

            if md_file.name == "index.md" and rel_path.parent != Path("."):
                folder_name = rel_path.parent.name
                if folder_name and folder_name[0].isdigit() and "-" in folder_name:
                    folder_name = folder_name.split("-", 1)[1]
                folder_display = folder_name.replace("-", " ").title()
                if title.lower() in ["index", "readme"]:
                    title = f"{folder_display} - Overview"

            title = prefixed(title, confluence_prefix)

            # --- Convert markdown to HTML ---
            html_content = markdown.markdown(
                md_content, extensions=["tables", "fenced_code"]
            )

            # --- Determine parent page ---
            parent_id = get_nested_parent_id(
                conf,
                space_key,
                rel_path,
                docs_dir,
                root_page_id,
                folder_pages,
                confluence_prefix,
            )

            # --- Create or update page first (need page_id for attachments) ---
            existing = conf.get_page_by_title(space=space_key, title=title)
            if existing:
                page_id = existing["id"]
            else:
                new_page = conf.create_page(
                    space=space_key,
                    title=title,
                    body="<p>Placeholder — content being uploaded.</p>",
                    parent_id=parent_id,
                )
                page_id = new_page["id"]
                print(f"  ✓ Created page: {title}")

            # --- Upload attachments (mermaid PNGs + local images) ---
            if all_attachments:
                uploaded = upload_attachments(conf, page_id, all_attachments)
            else:
                uploaded = set()

            # --- Build image_map for src→attachment_name replacement ---
            # Keys: original markdown ref strings and absolute path strings
            image_map = {}
            for name, path in mermaid_attachments:
                image_map[str(path)] = name
            for _, abs_path, ref in local_images:
                att_name = Path(ref).name
                if att_name in uploaded:
                    image_map[ref] = att_name
                    image_map[str(abs_path)] = att_name

            # --- Replace <img> tags with ac:image macros ---
            if image_map:
                html_content = replace_images_with_ac_macros(html_content, image_map)

            # --- Final update with real content ---
            conf.update_page(
                page_id=page_id,
                title=title,
                body=html_content,
                parent_id=parent_id,
            )
            print(f"  ✓ Updated: {title}")

    print("\n✓ All pages published successfully!")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    confluence_url = os.environ.get("CONFLUENCE_URL")
    confluence_user = os.environ.get("CONFLUENCE_USER")
    confluence_token = os.environ.get("CONFLUENCE_API_TOKEN")
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY")
    docs_path = os.environ.get("DOCS_PATH", "docs")
    root_page_title = os.environ.get("ROOT_PAGE_TITLE", "Documentation")
    confluence_prefix = os.environ.get("CONFLUENCE_PREFIX", "")

    if not all([confluence_url, confluence_user, confluence_token, space_key]):
        print("Error: Missing required environment variables")
        print(
            "Required: CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY"
        )
        sys.exit(1)

    try:
        publish_docs(
            confluence_url=confluence_url,
            confluence_user=confluence_user,
            confluence_token=confluence_token,
            space_key=space_key,
            docs_path=docs_path,
            root_page_title=root_page_title,
            confluence_prefix=confluence_prefix,
        )
    except Exception as e:
        print(
            f"\n✗ Error: {type(e).__name__}: {e.args[0] if e.args else 'unknown error'}"
        )
        sys.exit(1)
