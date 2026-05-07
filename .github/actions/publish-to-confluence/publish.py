#!/usr/bin/env python3
"""
Publish Markdown files from a directory to Confluence Cloud.
Preserves folder structure as page hierarchy.

Supports:
  - Mermaid diagrams: rendered to PNG via mmdc, uploaded as attachments;
    falls back to Confluence CloudScript macro if mmdc is unavailable
  - Local images: uploaded as Confluence attachments (png/jpg/gif/svg/webp/bmp/ico)
  - Tables, fenced code blocks with syntax highlighting
  - YAML frontmatter: stripped before publish, confluence_url/page_id written back
"""

import html
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

import markdown
from atlassian import Confluence

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language map: fenced-code identifier → Confluence code macro language
# ---------------------------------------------------------------------------

LANGUAGE_MAP = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "java": "java",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "sql": "sql",
    "json": "javascript",
    "xml": "xml",
    "html": "html",
    "css": "css",
    "yaml": "yaml",
    "yml": "yaml",
    "ruby": "ruby",
    "rb": "ruby",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "csharp": "csharp",
    "cs": "csharp",
    "php": "php",
    "scala": "scala",
    "terraform": "text",
    "tf": "text",
    "hcl": "text",
    "dockerfile": "bash",
    "groovy": "groovy",
    "powershell": "powershell",
    "ps1": "powershell",
    "r": "r",
    "perl": "perl",
    "swift": "swift",
    "kotlin": "kotlin",
}

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def _fm_parse(text):
    """Return (meta_dict, body) stripping YAML frontmatter from *text*.

    If no frontmatter is present returns ({}, text) unchanged.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta, text[m.end() :]


def _fm_dump(meta, body):
    """Return markdown text with *meta* serialised as YAML frontmatter."""
    if not meta:
        return body
    lines = ["---"]
    for key, value in meta.items():
        if any(c in str(value) for c in (":", "#", "[", "]", "{", "}")):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + body


def _fm_update_file(path, updates):
    """Merge *updates* into the frontmatter of *path*, preserving existing keys."""
    text = path.read_text(encoding="utf-8")
    meta, body = _fm_parse(text)
    meta.update(updates)
    path.write_text(_fm_dump(meta, body), encoding="utf-8")


# ---------------------------------------------------------------------------
# Mermaid macro (Confluence CloudScript app fallback)
# ---------------------------------------------------------------------------


def convert_mermaid_blocks(md_content):
    """
    Replace ```mermaid ... ``` fenced blocks with Confluence cloudscript-mermaid macro HTML
    before the standard markdown conversion runs.
    Requires the 'CloudScript.io Mermaid' app to be installed in Confluence.
    Used as a fallback when mmdc rendering is not available.
    """
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

    def replace(match):
        diagram = match.group(1).strip()
        return (
            '<ac:structured-macro ac:name="cloudscript-mermaid" ac:schema-version="1">'
            "<ac:plain-text-body>"
            f"<![CDATA[{diagram}]]>"
            "</ac:plain-text-body>"
            "</ac:structured-macro>"
        )

    return pattern.sub(replace, md_content)


# ---------------------------------------------------------------------------
# Code block conversion
# ---------------------------------------------------------------------------


def _replace_code_block(match):
    """Replace a single <pre><code> block with a Confluence code macro."""
    lang_attr = match.group(1) or ""
    code_body = match.group(2)

    lang = ""
    lang_match = re.search(r'language-([^\s"\']+)', lang_attr)
    if lang_match:
        lang = lang_match.group(1).lower()

    confluence_lang = LANGUAGE_MAP.get(lang, lang) if lang else "none"
    plain_code = html.unescape(code_body)

    return (
        '<ac:structured-macro ac:name="code">'
        f'<ac:parameter ac:name="language">{confluence_lang}</ac:parameter>'
        '<ac:parameter ac:name="linenumbers">true</ac:parameter>'
        "<ac:plain-text-body>"
        f"<![CDATA[{plain_code}]]>"
        "</ac:plain-text-body>"
        "</ac:structured-macro>"
    )


def convert_code_blocks_for_confluence(html_content):
    """Convert <pre><code> blocks into Confluence ac:structured-macro code blocks."""
    pattern = re.compile(
        r"<pre><code(?:\s([^>]*))?>(.*?)</code></pre>",
        re.DOTALL,
    )
    return pattern.sub(_replace_code_block, html_content)


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------


def render_mermaid_diagrams(md_content, tmp_dir):
    """
    Find all ```mermaid ... ``` blocks in the markdown, render each to a PNG
    file in tmp_dir using mmdc, and return:
      - modified md_content with blocks replaced by ![mermaid-N](abs/path/N.png)
      - list of (attachment_name, png_path) tuples for later upload

    Falls back to leaving the block unchanged if mmdc is not available.
    """
    pattern = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
    attachments = []
    counter = [0]

    def replace_block(m):
        idx = counter[0]
        counter[0] += 1
        diagram_src = m.group(1)
        mmd_file = Path(tmp_dir) / f"mermaid-{idx}.mmd"
        png_file = Path(tmp_dir) / f"mermaid-{idx}.png"
        puppeteer_cfg = Path(tmp_dir) / "puppeteer-config.json"
        mmd_file.write_text(diagram_src, encoding="utf-8")

        if not puppeteer_cfg.exists():
            puppeteer_cfg.write_text('{"args": ["--no-sandbox"]}', encoding="utf-8")

        try:
            subprocess.run(
                [
                    "mmdc",
                    "-i",
                    str(mmd_file),
                    "-o",
                    str(png_file),
                    "--backgroundColor",
                    "white",
                    "--puppeteerConfigFile",
                    str(puppeteer_cfg),
                ],
                check=True,
                capture_output=True,
            )
            attachment_name = f"mermaid-{idx}.png"
            attachments.append((attachment_name, png_file))
            return f"![{attachment_name}]({png_file})"
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            print(f"  Warning: mmdc failed for diagram {idx}: {stderr.strip()}")
            return m.group(0)
        except FileNotFoundError:
            print(
                "  Warning: mmdc not found — Mermaid diagrams will not be rendered as PNG."
            )
            return m.group(0)

    modified = pattern.sub(replace_block, md_content)
    return modified, attachments


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------

_IMG_SRC_PATTERN = re.compile(
    r'<img\s+([^>]*\s+)?src="([^"]+)"([^>]*)>',
    re.IGNORECASE,
)


def _replace_local_images_with_attachment_macros(html_content, md_file_dir):
    """Replace local image refs with Confluence attachment macros.

    Returns (modified_html, list_of_(filename, absolute_path)) for upload.
    Remote URLs and data URIs are left unchanged.
    """
    to_upload = []

    def replace_one(match):
        src = match.group(2).strip()
        if src.startswith(("http://", "https://", "data:", "//")):
            return match.group(0)
        path_part = unquote(src.lstrip("./"))
        if not path_part:
            return match.group(0)
        local_path = (md_file_dir / path_part).resolve()
        if not local_path.is_file():
            return match.group(0)
        filename = local_path.name
        to_upload.append((filename, local_path))
        return f'<ac:image><ri:attachment ri:filename="{html.escape(filename)}"/></ac:image>'

    return _IMG_SRC_PATTERN.sub(replace_one, html_content), to_upload


def _replace_mermaid_img_tags(html_content, mermaid_attachments):
    """Replace <img src="abs_png_path"> tags produced by render_mermaid_diagrams
    with Confluence <ac:image> macros.

    render_mermaid_diagrams replaces mermaid blocks with ![name](abs_path).
    After markdown conversion those become <img src="abs_path"> tags which
    cannot be resolved relative to md_file.parent. We handle them explicitly
    here using the known (name, abs_path) pairs before the generic image handler runs.
    """
    for name, abs_path in mermaid_attachments:
        escaped_name = html.escape(name)
        macro = f'<ac:image><ri:attachment ri:filename="{escaped_name}"/></ac:image>'
        # match the img tag with this exact src
        html_content = re.sub(
            r'<img\s[^>]*src="' + re.escape(str(abs_path)) + r'"[^>]*/?>',
            macro,
            html_content,
        )
    return html_content


def _content_type_for_filename(filename):
    ext = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".ico": "image/x-icon",
    }.get(ext, "application/octet-stream")


def _upload_attachments(conf, page_id, files_to_upload):
    """Upload local image files as Confluence page attachments."""
    page_id = str(page_id)
    for filename, file_path in files_to_upload:
        file_path = Path(file_path)
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_bytes()
            conf.attach_content(
                content,
                name=filename,
                content_type=_content_type_for_filename(filename),
                page_id=page_id,
            )
            print(f"  ✓ Uploaded attachment: {filename}")
        except Exception as e:
            print(f"  Warning: could not upload {filename}: {e}")


# ---------------------------------------------------------------------------
# Confluence client + page operations
# ---------------------------------------------------------------------------


def init_confluence(confluence_url, confluence_user, confluence_token):
    """Initialize and return a Confluence client."""
    return Confluence(
        url=confluence_url,
        username=confluence_user,
        password=confluence_token,
        cloud=True,
    )


def _update_confluence_page(conf, page_id, title, body_html, space_key, parent_id):
    """Update a Confluence page via direct REST PUT.

    The atlassian-python-api update_page can trigger 400 ApiValueError on
    Confluence Cloud when space is missing from the payload. We build the
    PUT payload explicitly to avoid this.
    """
    try:
        hist = conf.history(page_id)
        if hasattr(hist, "json"):
            hist = hist.json()
        version_num = hist.get("lastUpdated", {}).get("number", 1)
    except Exception:
        try:
            page = conf.get_page_by_id(page_id, expand="version")
            version_num = page.get("version", {}).get("number", 1)
        except Exception:
            version_num = 1

    data = {
        "id": page_id,
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "version": {"number": version_num + 1, "minorEdit": False},
        "body": {"storage": {"value": body_html, "representation": "storage"}},
    }
    if parent_id and str(parent_id) != str(page_id):
        data["ancestors"] = [{"type": "page", "id": parent_id}]

    conf.put(f"rest/api/content/{page_id}", data=data, params={"status": "current"})


def _find_page_any_status(conf, space_key, title):
    """Search for a page by title across all statuses (current, draft, trashed, archived).

    The standard get_page_by_title only returns 'current' pages. Confluence
    still enforces title uniqueness across drafts and trashed pages, so this
    is needed to find a conflicting ghost page before retrying a create.
    """
    for status in ("current", "draft", "trashed", "archived"):
        try:
            response = conf.get(
                "rest/api/content",
                params={
                    "type": "page",
                    "spaceKey": space_key,
                    "title": title,
                    "status": status,
                    "limit": 1,
                },
            )
            results = response.get("results", []) if isinstance(response, dict) else []
            if results:
                page = results[0]
                page.setdefault("status", status)
                return page
        except Exception:
            continue
    return None


def get_or_create_root_page(conf, space_key, root_page_title):
    """Return the root page id, creating the page if it doesn't exist."""
    print(f"Setting up root page: {root_page_title}")
    root_page = conf.get_page_by_title(space=space_key, title=root_page_title)
    if root_page:
        print(f"✓ Found root page: {root_page_title}")
        return root_page["id"]
    print(f"Creating root page: {root_page_title}")
    root_page = conf.create_page(
        space=space_key,
        title=root_page_title,
        body="<p>This is the root documentation page. Content is auto-generated from GitHub.</p>",
    )
    if not root_page:
        raise RuntimeError(f"Failed to create root page: {root_page_title}")
    print(f"✓ Created root page: {root_page_title}")
    return root_page["id"]


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
    """Get or create a Confluence page for a folder.

    Checks parent's children first, then falls back to a space-wide title
    search. On title conflict caused by a ghost draft/trashed page, removes
    the ghost and retries creation.
    """
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

    # Also search the whole space by title
    existing = conf.get_page_by_title(space=space_key, title=title)
    if existing:
        print(f"  ✓ Found folder page: {title} (id: {existing['id']})")
        folder_pages[folder_key] = existing["id"]
        return existing["id"]

    # Create folder page if not found
    print(f"  Creating folder page: {title} (under parent: {parent_id})")
    try:
        folder_page = conf.create_page(
            space=space_key,
            title=title,
            body=f"<p>This section contains documentation for {title}.</p>",
            parent_id=parent_id,
        )
        folder_pages[folder_key] = folder_page["id"]
        return folder_page["id"]
    except Exception as exc:
        if "already exists" not in str(exc).lower() and "title" not in str(exc).lower():
            raise
        # Ghost page (draft/trashed) is blocking creation — find and clean it up
        fallback = _find_page_any_status(conf, space_key, title)
        if fallback:
            fallback_status = fallback.get("status", "current")
            fallback_id = fallback["id"]
            if fallback_status in ("draft", "trashed"):
                try:
                    conf.remove_page(fallback_id)
                except Exception:
                    pass
                folder_page = conf.create_page(
                    space=space_key,
                    title=title,
                    body=f"<p>This section contains documentation for {title}.</p>",
                    parent_id=parent_id,
                )
                fallback_id = folder_page["id"]
            folder_pages[folder_key] = fallback_id
            return fallback_id
        raise


def get_nested_parent_id(
    conf,
    space_key,
    rel_path,
    docs_dir,
    root_page_id,
    folder_pages,
    confluence_prefix="",
):
    """Get parent page ID for nested folder structure."""
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
# Title derivation
# ---------------------------------------------------------------------------


def _title_for_md(md_file, rel_path, md_content):
    """Derive a Confluence page title from a markdown file and its content."""
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

    return title


# ---------------------------------------------------------------------------
# Single file publish
# ---------------------------------------------------------------------------


def publish_single_file(
    conf,
    space_key,
    md_file,
    docs_dir,
    root_page_id,
    folder_pages,
    confluence_prefix="",
    tmp_dir=None,
):
    """Publish (create or update) a single markdown file to Confluence.

    Handles the full pipeline:
      - Mermaid rendering to PNG (via mmdc) with CloudScript macro fallback
      - Frontmatter stripping and write-back of confluence_url/page_id
      - Code block conversion to Confluence macros
      - Local image upload as attachments
      - Ghost page cleanup on title conflicts
      - Direct REST PUT for page updates (avoids atlassian-python-api 400 bug)
    """
    md_file = Path(md_file).resolve()
    docs_dir = Path(docs_dir).resolve()

    try:
        rel_path = md_file.relative_to(docs_dir)
    except ValueError:
        rel_path = Path(md_file.name)

    md_content = md_file.read_text(encoding="utf-8")

    # Strip frontmatter before conversion so it doesn't appear in page content
    existing_meta, md_content = _fm_parse(md_content)

    # Render mermaid blocks to PNG; falls back to leaving block unchanged if mmdc unavailable
    if tmp_dir:
        md_content, mermaid_attachments = render_mermaid_diagrams(md_content, tmp_dir)
    else:
        mermaid_attachments = []

    # Apply CloudScript macro fallback for any mermaid blocks that were not rendered
    # (render_mermaid_diagrams leaves un-renderable blocks intact as fenced code)
    md_content = convert_mermaid_blocks(md_content)

    title = prefixed(_title_for_md(md_file, rel_path, md_content), confluence_prefix)

    # Convert Markdown → HTML
    html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    # Convert <pre><code> blocks to Confluence code macros
    html_content = convert_code_blocks_for_confluence(html_content)

    # Replace mermaid PNG <img> tags (abs paths) with ac:image macros before
    # the generic local-image handler runs (which resolves paths relative to md_file.parent)
    if mermaid_attachments:
        html_content = _replace_mermaid_img_tags(html_content, mermaid_attachments)

    # Replace remaining local image references with Confluence attachment macros
    html_content, local_files_to_upload = _replace_local_images_with_attachment_macros(
        html_content, md_file.parent
    )

    if not html_content or not html_content.strip():
        html_content = "<p></p>"

    parent_id = get_nested_parent_id(
        conf,
        space_key,
        rel_path,
        docs_dir,
        root_page_id,
        folder_pages,
        confluence_prefix,
    )

    existing = conf.get_page_by_title(space=space_key, title=title)

    if existing:
        page_id = existing["id"]
        _update_confluence_page(
            conf, page_id, title, html_content, space_key, parent_id
        )
        print(f"  ✓ Updated: {title}")
    else:
        try:
            created = conf.create_page(
                space=space_key,
                title=title,
                body=html_content,
                parent_id=parent_id,
            )
            page_id = (
                created.get("id")
                if isinstance(created, dict)
                else getattr(created, "id", None)
            )
            print(f"  ✓ Created: {title}")
        except Exception as exc:
            if (
                "already exists" not in str(exc).lower()
                and "title" not in str(exc).lower()
            ):
                raise
            # Ghost page (draft/trashed) is blocking creation
            fallback = _find_page_any_status(conf, space_key, title)
            if fallback:
                fallback_status = fallback.get("status", "current")
                fallback_id = fallback["id"]
                if fallback_status in ("draft", "trashed"):
                    try:
                        conf.remove_page(fallback_id)
                    except Exception:
                        pass
                    created = conf.create_page(
                        space=space_key,
                        title=title,
                        body=html_content,
                        parent_id=parent_id,
                    )
                    page_id = (
                        created.get("id")
                        if isinstance(created, dict)
                        else getattr(created, "id", None)
                    )
                    print(f"  ✓ Created (after ghost cleanup): {title}")
                else:
                    page_id = fallback_id
                    _update_confluence_page(
                        conf, page_id, title, html_content, space_key, parent_id
                    )
                    print(f"  ✓ Updated (fallback): {title}")
            else:
                raise

    # Upload all attachments: local images + mermaid PNGs
    all_files_to_upload = local_files_to_upload + [
        (name, path) for name, path in mermaid_attachments
    ]
    if all_files_to_upload and page_id:
        _upload_attachments(conf, page_id, all_files_to_upload)

    # Write confluence_url and page_id back into the file's frontmatter
    if page_id:
        try:
            page_info = conf.get_page_by_id(page_id, expand="")
            webui = (
                page_info.get("_links", {}).get("webui", "")
                if isinstance(page_info, dict)
                else ""
            )
            base_url = conf.url.rstrip("/")
            target_url = (
                f"{base_url}/wiki{webui}"
                if webui and not webui.startswith("http")
                else webui
            )
            if target_url:
                existing_meta["confluence_url"] = target_url
                existing_meta["page_id"] = str(page_id)
                _fm_update_file(md_file, existing_meta)
        except Exception:
            pass

    # Register this page in the folder cache if a same-named sibling directory exists,
    # so child pages nest under it rather than a separate placeholder page.
    if page_id:
        sibling_dir = md_file.parent / md_file.stem
        if sibling_dir.is_dir():
            folder_pages[str(sibling_dir)] = page_id


# ---------------------------------------------------------------------------
# Sorting / filtering helpers
# ---------------------------------------------------------------------------


def _depth_then_index_first(p):
    """Sort key: shallowest paths first, index.md before siblings."""
    return (len(p.parts), p.name != "index.md", str(p))


def _remove_redundant_index_files(md_files):
    """Remove index.md files that duplicate a sibling parent .md file.

    When foo/index.md exists alongside foo.md, the index is redundant.
    """
    resolved_paths = {p.resolve() for p in md_files}
    return [
        p
        for p in md_files
        if not (
            p.name == "index.md"
            and (p.parent.parent / f"{p.parent.name}.md").resolve() in resolved_paths
        )
    ]


# ---------------------------------------------------------------------------
# Main publish entry point
# ---------------------------------------------------------------------------


def publish_docs(
    confluence_url,
    confluence_user,
    confluence_token,
    space_key,
    docs_path,
    root_page_title,
    confluence_prefix="",
    files=None,
):
    """Publish all markdown files under docs_path to Confluence.

    If *files* is given (a list of paths), only those files are published.
    """
    conf = init_confluence(confluence_url, confluence_user, confluence_token)
    root_page_title_prefixed = prefixed(root_page_title, confluence_prefix)
    root_page_id = get_or_create_root_page(conf, space_key, root_page_title_prefixed)

    folder_pages = {}
    docs_dir = Path(docs_path)

    if files:
        md_files = [Path(f) for f in files]
    else:
        md_files = list(docs_dir.rglob("*.md"))

        def sort_key(p):
            is_index = p.name == "index.md"
            depth = len(p.parts)
            return (not is_index, depth, str(p))

        md_files.sort(key=sort_key)
        md_files = _remove_redundant_index_files(md_files)

    print(f"\nPublishing {len(md_files)} files...\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        for md_file in md_files:
            if "template" in md_file.name.lower():
                print(
                    f"Skipping template: {md_file.relative_to(docs_dir) if md_file.is_relative_to(docs_dir) else md_file.name}"
                )
                continue

            rel = (
                md_file.relative_to(docs_dir)
                if md_file.is_relative_to(docs_dir)
                else md_file
            )
            print(f"\nPublishing {rel}...")
            publish_single_file(
                conf,
                space_key,
                md_file,
                docs_dir,
                root_page_id,
                folder_pages,
                confluence_prefix,
                tmp_dir=tmp_dir,
            )

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
