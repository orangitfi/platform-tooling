#!/usr/bin/env python3
"""
Export Confluence Cloud pages to local Markdown files.
Reconstructs folder hierarchy from page tree and downloads image attachments.
"""

import argparse
import html as html_module
import os
import re
import sys
from pathlib import Path

from atlassian import Confluence

# Reverse map: Confluence code macro language → markdown language identifier
CONFLUENCE_LANG_TO_MD = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "bash": "bash",
    "sql": "sql",
    "xml": "xml",
    "html": "html",
    "css": "css",
    "yaml": "yaml",
    "ruby": "ruby",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "csharp": "csharp",
    "php": "php",
    "scala": "scala",
    "groovy": "groovy",
    "powershell": "powershell",
    "r": "r",
    "perl": "perl",
    "swift": "swift",
    "kotlin": "kotlin",
    "text": "text",
    "none": "",
}


# ---------------------------------------------------------------------------
# HTML → Markdown conversion helpers
# ---------------------------------------------------------------------------


def _convert_code_macros(html_content):
    """Convert Confluence ac:structured-macro code blocks to markdown fenced code."""
    pattern = re.compile(
        r'<ac:structured-macro\s[^>]*ac:name="code"[^>]*>'
        r'(?:.*?<ac:parameter\s[^>]*ac:name="language"[^>]*>([^<]*)</ac:parameter>)?'
        r".*?<ac:plain-text-body>\s*<!\[CDATA\[(.*?)\]\]>\s*</ac:plain-text-body>"
        r".*?</ac:structured-macro>",
        re.DOTALL,
    )

    def _replace(match):
        lang = (match.group(1) or "").strip()
        code = match.group(2)
        md_lang = CONFLUENCE_LANG_TO_MD.get(lang, lang)
        return f"\n```{md_lang}\n{code}\n```\n"

    return pattern.sub(_replace, html_content)


def _convert_confluence_images(html_content, attachments_map, images_rel_dir):
    """Convert Confluence image tags to markdown image syntax.

    Handles both:
      - <ac:image><ri:attachment ri:filename="..."/></ac:image>
      - <ac:image><ri:url ri:value="..."/></ac:image>
    """
    # Attachment images
    pattern_attach = re.compile(
        r'<ac:image[^>]*>.*?<ri:attachment\s+ri:filename="([^"]+)"[^/]*/>'
        r".*?</ac:image>",
        re.DOTALL,
    )

    def _replace_attach(match):
        filename = match.group(1)
        rel_path = f"{images_rel_dir}/{filename}" if images_rel_dir else filename
        return f"![{filename}]({rel_path})"

    html_content = pattern_attach.sub(_replace_attach, html_content)

    # External URL images
    pattern_url = re.compile(
        r'<ac:image[^>]*>.*?<ri:url\s+ri:value="([^"]+)"[^/]*/>'
        r".*?</ac:image>",
        re.DOTALL,
    )

    def _replace_url(match):
        url = match.group(1)
        return f"![image]({url})"

    html_content = pattern_url.sub(_replace_url, html_content)

    return html_content


def _strip_tags(text):
    """Remove remaining HTML tags, leaving fenced code block content untouched."""
    placeholders = []
    fence_pattern = re.compile(r"(```[^\n]*\n.*?```)", re.DOTALL)

    def _protect(match):
        placeholders.append(match.group(1))
        return f"\x00CODEBLOCK{len(placeholders) - 1}\x00"

    protected = fence_pattern.sub(_protect, text)
    stripped = re.sub(r"<[^>]+>", "", protected)

    for i, block in enumerate(placeholders):
        stripped = stripped.replace(f"\x00CODEBLOCK{i}\x00", block)
    return stripped


def _convert_inline_formatting(html_content):
    """Convert inline HTML formatting to Markdown equivalents."""
    html_content = re.sub(
        r"<strong>(.*?)</strong>", r"**\1**", html_content, flags=re.DOTALL
    )
    html_content = re.sub(r"<b>(.*?)</b>", r"**\1**", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<em>(.*?)</em>", r"*\1*", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<i>(.*?)</i>", r"*\1*", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<code>(.*?)</code>", r"`\1`", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<del>(.*?)</del>", r"~~\1~~", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<s>(.*?)</s>", r"~~\1~~", html_content, flags=re.DOTALL)
    return html_content


def _convert_links(html_content):
    """Convert HTML <a> links to Markdown links."""
    pattern = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    return pattern.sub(r"[\2](\1)", html_content)


def _convert_headings(html_content):
    """Convert HTML headings to Markdown headings."""
    for level in range(1, 7):
        pattern = re.compile(rf"<h{level}[^>]*>(.*?)</h{level}>", re.DOTALL)
        html_content = pattern.sub(
            lambda m, lvl=level: f"\n{'#' * lvl} {m.group(1).strip()}\n",
            html_content,
        )
    return html_content


def _convert_lists(html_content):
    """Convert HTML lists to Markdown lists."""

    def _normalize_li_content(text):
        """Strip <p> wrappers inside <li> to avoid marker/content misalignment."""
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n", text, flags=re.DOTALL)
        text = re.sub(r"<p[^>]*>", "", text)
        text = re.sub(r"</p>", "", text)
        return text.strip()

    def _ul_replace(match):
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), re.DOTALL)
        lines = []
        for item in items:
            text = _normalize_li_content(item)
            item_lines = text.splitlines()
            non_empty = [ln for ln in item_lines if ln.strip()]
            if non_empty:
                first = non_empty[0]
                rest = ["  " + ln for ln in non_empty[1:]]
                lines.append("- " + "\n".join([first] + rest))
            else:
                lines.append("- ")
        return "\n" + "\n".join(lines) + "\n"

    def _ol_replace(match):
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), re.DOTALL)
        lines = []
        for i, item in enumerate(items, 1):
            text = _normalize_li_content(item)
            marker = f"{i}. "
            indent = " " * len(marker)
            item_lines = text.splitlines()
            non_empty = [ln for ln in item_lines if ln.strip()]
            if non_empty:
                first = non_empty[0]
                rest = [indent + ln for ln in non_empty[1:]]
                lines.append(marker + "\n".join([first] + rest))
            else:
                lines.append(marker)
        return "\n" + "\n".join(lines) + "\n"

    # Iterate a few times to handle nesting
    for _ in range(5):
        prev = html_content
        html_content = re.sub(
            r"<ul[^>]*>(.*?)</ul>", _ul_replace, html_content, flags=re.DOTALL
        )
        html_content = re.sub(
            r"<ol[^>]*>(.*?)</ol>", _ol_replace, html_content, flags=re.DOTALL
        )
        if html_content == prev:
            break

    return html_content


def _convert_tables(html_content):
    """Convert HTML tables to Markdown tables."""
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL)

    def _table_replace(match):
        table_html = match.group(1)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL)
        if not rows:
            return match.group(0)

        md_rows = []
        for row_html in rows:
            cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, re.DOTALL)
            cells = [_strip_tags(c).strip() for c in cells]
            md_rows.append("| " + " | ".join(cells) + " |")

        if len(md_rows) >= 1:
            # Add separator after first row (header)
            ncols = md_rows[0].count("|") - 1
            separator = "| " + " | ".join(["---"] * ncols) + " |"
            md_rows.insert(1, separator)

        return "\n" + "\n".join(md_rows) + "\n"

    return table_pattern.sub(_table_replace, html_content)


def _convert_paragraphs(html_content):
    """Convert <p> tags to double newlines."""
    html_content = re.sub(r"<p[^>]*>", "\n\n", html_content)
    html_content = re.sub(r"</p>", "", html_content)
    return html_content


def _convert_line_breaks(html_content):
    """Convert <br> tags to newlines."""
    return re.sub(r"<br\s*/?>", "\n", html_content)


def _convert_horizontal_rules(html_content):
    """Convert <hr> tags to Markdown horizontal rules."""
    return re.sub(r"<hr\s*/?>", "\n---\n", html_content)


def _convert_blockquotes(html_content):
    """Convert <blockquote> tags to Markdown blockquotes."""
    pattern = re.compile(r"<blockquote[^>]*>(.*?)</blockquote>", re.DOTALL)

    def _bq_replace(match):
        content = match.group(1).strip()
        lines = content.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"\n{quoted}\n"

    return pattern.sub(_bq_replace, html_content)


def _convert_confluence_info_macros(html_content):
    """Convert Confluence info/warning/note/tip macros to blockquotes."""
    pattern = re.compile(
        r'<ac:structured-macro\s[^>]*ac:name="(info|warning|note|tip)"[^>]*>'
        r".*?<ac:rich-text-body>(.*?)</ac:rich-text-body>"
        r".*?</ac:structured-macro>",
        re.DOTALL,
    )

    def _replace(match):
        macro_type = match.group(1).upper()
        body = match.group(2).strip()
        lines = body.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"\n> **{macro_type}:** \n{quoted}\n"

    return pattern.sub(_replace, html_content)


def _clean_whitespace(text):
    """Normalize excessive blank lines."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def html_to_markdown(html_content, attachments_map=None, images_rel_dir="attachments"):
    """Convert Confluence storage-format HTML to Markdown."""
    if not html_content:
        return ""

    content = html_content

    # 1. Confluence-specific macros first (before stripping tags)
    content = _convert_code_macros(content)
    content = _convert_confluence_info_macros(content)
    content = _convert_confluence_images(content, attachments_map or {}, images_rel_dir)

    # 2. Standard HTML → Markdown
    content = _convert_headings(content)
    content = _convert_tables(content)
    content = _convert_lists(content)
    content = _convert_blockquotes(content)
    content = _convert_links(content)
    content = _convert_inline_formatting(content)
    content = _convert_horizontal_rules(content)
    content = _convert_line_breaks(content)
    content = _convert_paragraphs(content)

    # 3. Strip remaining HTML tags
    content = _strip_tags(content)

    # 4. Unescape HTML entities (e.g. &lt; → <, &amp; → &)
    content = html_module.unescape(content)

    # 5. Clean up
    content = _clean_whitespace(content)

    return content


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


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


# ---------------------------------------------------------------------------
# Confluence interaction
# ---------------------------------------------------------------------------


def init_confluence(confluence_url, confluence_user, confluence_token):
    """Initialize and return a Confluence client."""
    return Confluence(
        url=confluence_url,
        username=confluence_user,
        password=confluence_token,
        cloud=True,
    )


def _sanitize_filename(title):
    """Turn a page title into a safe filesystem name."""
    name = title.strip()
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-").lower()
    return name or "untitled"


def download_attachments(conf, page_id, dest_dir):
    """Download all image attachments for a page into *dest_dir*.

    Returns a dict mapping original filename → local path.
    """
    attachments_map = {}
    try:
        result = conf.get_attachments_from_content(page_id, start=0, limit=100)
        items = result.get("results", [])
    except Exception:
        return attachments_map

    image_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".bmp",
        ".ico",
    }

    for att in items:
        filename = att.get("title", "")
        ext = Path(filename).suffix.lower()
        if ext not in image_extensions:
            continue

        download_url = att.get("_links", {}).get("download", "")
        if not download_url:
            continue

        dest_file = dest_dir / filename
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            data = conf.request(
                path=download_url,
                method="GET",
                headers={"Accept": "application/octet-stream"},
            )
            if hasattr(data, "content"):
                dest_file.write_bytes(data.content)
            else:
                dest_file.write_bytes(data)
            attachments_map[filename] = str(dest_file)
            print(f"    ✓ Downloaded attachment: {filename}")
        except Exception:
            pass

    return attachments_map


def export_page(conf, page_id, dest_dir, depth=0, max_depth=-1):
    """Export a single Confluence page and its children recursively.

    *dest_dir* is the directory where the .md file (and attachments/) will be written.
    *depth* tracks current recursion depth.
    *max_depth* limits recursion (-1 = unlimited).
    """
    indent = "  " * depth

    # Fetch page with body in storage format
    page = conf.get_page_by_id(
        page_id,
        expand="body.storage,children.page",
    )
    title = page.get("title", "Untitled")
    body_html = page.get("body", {}).get("storage", {}).get("value", "")

    print(f"{indent}Exporting: {title}")

    safe_name = _sanitize_filename(title)
    page_dir = Path(dest_dir)
    page_dir.mkdir(parents=True, exist_ok=True)

    # Download image attachments
    attachments_dir = page_dir / "attachments"
    attachments_map = download_attachments(conf, page_id, attachments_dir)

    # Convert HTML to Markdown
    md_content = html_to_markdown(
        body_html, attachments_map, images_rel_dir="attachments"
    )

    # Prepend title as H1 if not already present
    if not md_content.startswith(f"# {title}"):
        md_content = f"# {title}\n\n{md_content}"

    # Build Confluence page URL from _links
    webui = page.get("_links", {}).get("webui", "")
    base_url = conf.url.rstrip("/")
    confluence_url = (
        f"{base_url}/wiki{webui}" if webui and not webui.startswith("http") else webui
    )

    # Prepend YAML frontmatter with source URL and page ID
    meta = {
        "confluence_url": confluence_url,
        "page_id": str(page_id),
    }
    md_content = _fm_dump(meta, md_content)

    md_file = page_dir / f"{safe_name}.md"
    md_file.write_text(md_content, encoding="utf-8")
    print(f"{indent}  ✓ Written: {md_file}")

    # Recurse into children
    children = page.get("children", {}).get("page", {}).get("results", [])
    if children and (max_depth == -1 or depth < max_depth):
        child_dir = page_dir / safe_name
        for child in children:
            export_page(conf, child["id"], child_dir, depth + 1, max_depth)


def export_space(conf, space_key, dest_dir, root_page_title=None, max_depth=-1):
    """Export pages from a Confluence space.

    If *root_page_title* is given, only that page tree is exported.
    Otherwise the space's home page tree is exported.
    """
    if root_page_title:
        print(f"Looking up root page: {root_page_title}")
        root_page = conf.get_page_by_title(space=space_key, title=root_page_title)
        if not root_page:
            print(f"✗ Root page not found: {root_page_title}")
            sys.exit(1)
        root_id = root_page["id"]
    else:
        # Get space homepage
        print(f"Looking up space homepage for: {space_key}")
        space_info = conf.get_space(space_key, expand="homepage")
        root_id = space_info.get("homepage", {}).get("id")
        if not root_id:
            print(f"✗ Could not find homepage for space: {space_key}")
            sys.exit(1)

    export_page(conf, root_id, dest_dir, max_depth=max_depth)


def export_single_page(conf, page_id, dest_dir):
    """Export a single page by its ID (no recursion)."""
    export_page(conf, page_id, dest_dir, max_depth=0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser():
    """Build the argparse CLI parser."""
    parser = argparse.ArgumentParser(
        description="Export Confluence Cloud pages to local Markdown files. "
        "Downloads image attachments and reconstructs page hierarchy.",
        epilog="Connection parameters can also be set via environment variables: "
        "CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY.",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("CONFLUENCE_URL"),
        help="Confluence base URL (env: CONFLUENCE_URL)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("CONFLUENCE_USER"),
        help="Confluence username / email (env: CONFLUENCE_USER)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("CONFLUENCE_API_TOKEN"),
        help="Confluence API token (env: CONFLUENCE_API_TOKEN)",
    )
    parser.add_argument(
        "--space",
        default=os.environ.get("CONFLUENCE_SPACE_KEY"),
        help="Confluence space key (env: CONFLUENCE_SPACE_KEY)",
    )
    parser.add_argument(
        "--page-id",
        help="Export a single page by its Confluence page ID (no recursion)",
    )
    parser.add_argument(
        "--root-page-title",
        default=os.environ.get("ROOT_PAGE_TITLE"),
        help="Title of the root page to export (exports its full tree). "
        "If omitted, exports the space homepage tree.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("EXPORT_OUTPUT_DIR", "exported-docs"),
        help="Local directory to write exported files (default: exported-docs)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=-1,
        help="Maximum depth of child pages to export (-1 = unlimited, default: -1)",
    )
    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Validate required connection settings
    missing = []
    if not args.url:
        missing.append("--url / CONFLUENCE_URL")
    if not args.user:
        missing.append("--user / CONFLUENCE_USER")
    if not args.token:
        missing.append("--token / CONFLUENCE_API_TOKEN")
    if not args.page_id and not args.space:
        missing.append("--space / CONFLUENCE_SPACE_KEY (or use --page-id)")
    if missing:
        parser.error(f"Missing required settings: {', '.join(missing)}")

    conf = init_confluence(args.url, args.user, args.token)

    print(f"\nExporting to: {args.output_dir}\n")

    try:
        if args.page_id:
            export_single_page(conf, args.page_id, args.output_dir)
        else:
            export_space(
                conf,
                space_key=args.space,
                dest_dir=args.output_dir,
                root_page_title=args.root_page_title,
                max_depth=args.max_depth,
            )
    except Exception as e:
        print(
            f"\n✗ Error: {type(e).__name__}: {e.args[0] if e.args else 'unknown error'}"
        )
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n✓ Export complete!")


if __name__ == "__main__":
    main()
