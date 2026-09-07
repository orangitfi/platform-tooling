"""Unit tests for the Confluence publish action (v5 / ConfluenceV2 migration).

The Confluence client is fully mocked — no network or live DB is required.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

HERE = Path(__file__).parent
PUBLISH_PATH = HERE / "publish.py"


def _load_publish_module():
    """Import publish.py as a module, stubbing external deps if missing."""
    # Stub 'markdown' and 'atlassian' if not installed in the test env.
    if "markdown" not in sys.modules:
        md_stub = types.ModuleType("markdown")
        md_stub.markdown = lambda text, extensions=None: f"<html>{text}</html>"
        sys.modules["markdown"] = md_stub
    if "atlassian" not in sys.modules:
        atl_stub = types.ModuleType("atlassian")
        atl_stub.ConfluenceV2 = MagicMock(name="ConfluenceV2")
        sys.modules["atlassian"] = atl_stub

    spec = importlib.util.spec_from_file_location("publish_under_test", PUBLISH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publish = _load_publish_module()


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_prefixed_with_prefix():
    assert publish.prefixed("Page", "[Repo] ") == "[Repo] Page"


def test_prefixed_without_prefix():
    assert publish.prefixed("Page", "") == "Page"


@pytest.mark.parametrize(
    "rel, expected",
    [
        ("adr", "Adr"),
        ("poc/adr", "Poc / Adr"),
        ("00-intro", "Intro"),
        ("poc/00-intro", "Poc / Intro"),
    ],
)
def test_folder_page_title(rel, expected):
    docs = Path("/docs")
    assert publish.folder_page_title(docs, docs / rel) == expected


def test_convert_mermaid_blocks_wraps_macro():
    md = "before\n```mermaid\ngraph TD;A-->B;\n```\nafter"
    out = publish.convert_mermaid_blocks(md)
    assert "cloudscript-mermaid" in out
    assert "graph TD;A-->B;" in out
    assert "```mermaid" not in out


def test_convert_mermaid_blocks_noop_without_mermaid():
    md = "just text"
    assert publish.convert_mermaid_blocks(md) == md


# ---------------------------------------------------------------------------
# Client / space resolution
# ---------------------------------------------------------------------------


def test_make_client_drops_cloud_flag():
    with patch.object(publish, "ConfluenceV2") as CV2:
        publish.make_client("https://x.atlassian.net/wiki", "u@e", "tok")
    CV2.assert_called_once_with(
        url="https://x.atlassian.net/wiki", username="u@e", password="tok"
    )


def test_resolve_space_id_returns_string_id():
    conf = MagicMock()
    conf.get_space_by_key.return_value = {"id": 12345, "key": "OKB", "name": "KB"}
    assert publish.resolve_space_id(conf, "OKB") == "12345"
    conf.get_space_by_key.assert_called_once_with("OKB")


def test_resolve_space_id_bad_response_raises():
    conf = MagicMock()
    conf.get_space_by_key.return_value = "<html>login</html>"
    with pytest.raises(RuntimeError):
        publish.resolve_space_id(conf, "OKB")


# ---------------------------------------------------------------------------
# find_page_by_title
# ---------------------------------------------------------------------------


def test_find_page_by_title_match():
    conf = MagicMock()
    conf.get_pages.return_value = [
        {"id": "1", "title": "Other"},
        {"id": "2", "title": "Target"},
    ]
    page = publish.find_page_by_title(conf, "999", "Target")
    assert page["id"] == "2"
    conf.get_pages.assert_called_once_with(
        space_id="999", title="Target", limit=50, get_body=True
    )


def test_find_page_by_title_no_match():
    conf = MagicMock()
    conf.get_pages.return_value = [{"id": "1", "title": "Other"}]
    assert publish.find_page_by_title(conf, "999", "Missing") is None


def test_find_page_by_title_empty():
    conf = MagicMock()
    conf.get_pages.return_value = []
    assert publish.find_page_by_title(conf, "999", "X") is None


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


def test_attach_file_v2_posts_to_v1_endpoint():
    conf = MagicMock()
    m = mock_open(read_data=b"png-bytes")
    with patch("builtins.open", m):
        publish.attach_file_v2(conf, "42", "/tmp/x.png", "x.png")
    args, kwargs = conf.post.call_args
    assert args[0] == "rest/api/content/42/child/attachment"
    assert kwargs["headers"]["X-Atlassian-Token"] == "no-check"
    assert "file" in kwargs["files"]


def test_upload_attachments_success_and_failure():
    conf = MagicMock()
    calls = {"n": 0}

    def side_effect(c, page_id, path, name, content_type="image/png"):
        calls["n"] += 1
        if name == "bad.png":
            raise RuntimeError("boom")

    with patch.object(publish, "attach_file_v2", side_effect=side_effect):
        uploaded = publish.upload_attachments(
            conf,
            "42",
            [("ok.png", Path("/tmp/ok.png")), ("bad.png", Path("/tmp/bad.png"))],
        )
    assert uploaded == {"ok.png"}
    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# Image macro replacement
# ---------------------------------------------------------------------------


def test_replace_images_with_ac_macros_by_ref():
    html = '<img src="img/a.png" alt="A" />'
    out = publish.replace_images_with_ac_macros(html, {"img/a.png": "a.png"})
    assert '<ac:image ac:alt="A">' in out
    assert 'ri:filename="a.png"' in out


def test_replace_images_unmapped_left_alone():
    html = '<img src="img/z.png" alt="Z" />'
    out = publish.replace_images_with_ac_macros(html, {"other": "o.png"})
    assert out == html


# ---------------------------------------------------------------------------
# collect_local_images
# ---------------------------------------------------------------------------


def test_collect_local_images(tmp_path):
    img = tmp_path / "pic.png"
    img.write_bytes(b"x")
    md_file = tmp_path / "doc.md"
    md_file.write_text("text")
    md = "![Pic](pic.png) and ![Remote](https://e.com/r.png)"
    images = publish.collect_local_images(md, md_file)
    assert len(images) == 1
    alt, abs_path, ref = images[0]
    assert alt == "Pic" and ref == "pic.png"
    assert abs_path == img.resolve()


def test_collect_local_images_missing(tmp_path, capsys):
    md_file = tmp_path / "doc.md"
    md_file.write_text("text")
    images = publish.collect_local_images("![X](nope.png)", md_file)
    assert images == []
    assert "not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Folder page hierarchy (v2 calls)
# ---------------------------------------------------------------------------


def test_get_or_create_folder_page_found_existing():
    conf = MagicMock()
    conf.get.return_value = {"results": [{"id": "77", "title": "Adr"}]}
    folder_pages = {}
    docs = Path("/docs")
    pid = publish.get_or_create_folder_page(
        conf, "sid", docs / "adr", "root", folder_pages, docs
    )
    assert pid == "77"
    conf.post.assert_not_called()
    conf.get.assert_called_once_with("api/v2/pages/root/children", params={"limit": 100})


def test_get_or_create_folder_page_creates_with_space_id():
    conf = MagicMock()
    conf.get.return_value = {"results": []}
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.return_value = {"id": "88"}
    folder_pages = {}
    docs = Path("/docs")
    pid = publish.get_or_create_folder_page(
        conf, "sid", docs / "adr", "root", folder_pages, docs
    )
    assert pid == "88"
    _, kwargs = conf.post.call_args
    payload = kwargs["data"]
    assert payload["spaceId"] == "sid"
    assert payload["parentId"] == "root"


def test_get_or_create_folder_page_cached():
    conf = MagicMock()
    folder_pages = {str(Path("/docs/adr")): "cached"}
    pid = publish.get_or_create_folder_page(
        conf, "sid", Path("/docs/adr"), "root", folder_pages, Path("/docs")
    )
    assert pid == "cached"
    conf.get.assert_not_called()


def test_get_nested_parent_id_root_level():
    conf = MagicMock()
    assert (
        publish.get_nested_parent_id(
            conf, "sid", Path("file.md"), Path("/docs"), "root", {}
        )
        == "root"
    )


def test_get_nested_parent_id_nested():
    conf = MagicMock()
    conf.get.return_value = {"results": []}
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.side_effect = [{"id": "a"}, {"id": "b"}]
    pid = publish.get_nested_parent_id(
        conf, "sid", Path("poc/adr/file.md"), Path("/docs"), "root", {}
    )
    assert pid == "b"


# ---------------------------------------------------------------------------
# publish_docs end-to-end (mocked client + fs)
# ---------------------------------------------------------------------------


def test_publish_docs_creates_and_updates(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home\n\nWelcome")

    conf = MagicMock()
    conf.get_space_by_key.return_value = {"id": 5, "key": "OKB", "name": "KB"}
    # No existing pages anywhere.
    conf.get_pages.return_value = []
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.side_effect = [
        {"id": "root"},  # root page
        {"id": "p1"},  # index page
    ]
    conf.get_page_by_id.return_value = {
        "id": "p1",
        "status": "current",
        "version": {"number": 1},
    }

    with patch.object(publish, "ConfluenceV2", return_value=conf):
        publish.publish_docs(
            "https://x.atlassian.net/wiki",
            "u@e",
            "tok",
            "OKB",
            str(docs),
            "Documentation",
        )

    # Root + page created via explicit v2 POST with spaceId (not space key).
    for _, kwargs in conf.post.call_args_list:
        payload = kwargs["data"]
        assert "spaceId" in payload
        assert payload["body"]["representation"] == "storage"
    # Content page updated via explicit v2 PUT (update_page_content).
    assert conf.put.called
    _, ukwargs = conf.put.call_args
    upayload = ukwargs["data"]
    assert upayload["body"]["representation"] == "storage"
    assert "version" in upayload


def test_publish_docs_uses_existing_root(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "page.md").write_text("# Page\n\nBody")

    conf = MagicMock()
    conf.get_space_by_key.return_value = {"id": 5, "key": "OKB", "name": "KB"}

    def get_pages(space_id, title, limit, get_body=False):
        if title == "Documentation":
            return [{"id": "root", "title": "Documentation"}]
        return []

    conf.get_pages.side_effect = get_pages
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.return_value = {"id": "p1"}
    conf.get_page_by_id.return_value = {
        "id": "p1",
        "status": "current",
        "version": {"number": 1},
    }

    with patch.object(publish, "ConfluenceV2", return_value=conf):
        publish.publish_docs(
            "https://x.atlassian.net/wiki",
            "u@e",
            "tok",
            "OKB",
            str(docs),
            "Documentation",
        )

    # Root already existed → only the content page is created.
    assert conf.post.call_count == 1


# ---------------------------------------------------------------------------
# render_mermaid_diagrams
# ---------------------------------------------------------------------------


def test_render_mermaid_success(tmp_path):
    md = "x\n```mermaid\ngraph TD;A-->B;\n```\ny"
    with patch.object(publish.subprocess, "run") as run:
        run.return_value = MagicMock()
        out, attachments = publish.render_mermaid_diagrams(md, str(tmp_path))
    assert len(attachments) == 1
    name, path = attachments[0]
    assert name == "mermaid-0.png"
    assert f"![{name}]" in out
    run.assert_called_once()


def test_render_mermaid_mmdc_missing(tmp_path, capsys):
    md = "```mermaid\ngraph TD;A-->B;\n```"
    with patch.object(publish.subprocess, "run", side_effect=FileNotFoundError):
        out, attachments = publish.render_mermaid_diagrams(md, str(tmp_path))
    assert attachments == []
    assert "mmdc not found" in capsys.readouterr().out
    assert "```mermaid" in out  # original block preserved


def test_render_mermaid_mmdc_failed(tmp_path, capsys):
    md = "```mermaid\ngraph TD;A-->B;\n```"
    err = publish.subprocess.CalledProcessError(1, "mmdc", stderr=b"bad diagram")
    with patch.object(publish.subprocess, "run", side_effect=err):
        out, attachments = publish.render_mermaid_diagrams(md, str(tmp_path))
    assert attachments == []
    assert "mmdc failed" in capsys.readouterr().out
    assert "```mermaid" in out


def test_render_mermaid_none(tmp_path):
    md = "no diagrams here"
    out, attachments = publish.render_mermaid_diagrams(md, str(tmp_path))
    assert out == md
    assert attachments == []


# ---------------------------------------------------------------------------
# Entry point env-var validation
# ---------------------------------------------------------------------------


def test_main_missing_env_exits(monkeypatch):
    for var in [
        "CONFLUENCE_URL",
        "CONFLUENCE_USER",
        "CONFLUENCE_API_TOKEN",
        "CONFLUENCE_SPACE_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
    code = compile(PUBLISH_PATH.read_text(), str(PUBLISH_PATH), "exec")
    ns = {"__name__": "__main__"}
    with pytest.raises(SystemExit) as exc:
        exec(code, ns)
    assert exc.value.code == 1


def test_main_happy_path(monkeypatch, tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home\n\nHi")
    monkeypatch.setenv("CONFLUENCE_URL", "https://x.atlassian.net/wiki")
    monkeypatch.setenv("CONFLUENCE_USER", "u@e")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "tok")
    monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "OKB")
    monkeypatch.setenv("DOCS_PATH", str(docs))

    conf = MagicMock()
    conf.get_space_by_key.return_value = {"id": 5, "key": "OKB", "name": "KB"}
    conf.get_pages.return_value = []
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.side_effect = [{"id": "root"}, {"id": "p1"}]
    conf.get_page_by_id.return_value = {
        "id": "p1",
        "status": "current",
        "version": {"number": 1},
    }

    code = compile(PUBLISH_PATH.read_text(), str(PUBLISH_PATH), "exec")
    ns = {"__name__": "__main__"}
    with patch.object(publish, "ConfluenceV2", return_value=conf):
        # Patch the freshly-exec'd module's ConfluenceV2 by injecting into globals.
        import atlassian  # noqa: F401

        with patch("atlassian.ConfluenceV2", return_value=conf):
            exec(code, ns)  # should complete without SystemExit


def test_publish_docs_skips_templates(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "my-template.md").write_text("# T\n\nx")

    conf = MagicMock()
    conf.get_space_by_key.return_value = {"id": 5, "key": "OKB", "name": "KB"}
    conf.get_pages.return_value = []
    conf.get_endpoint.return_value = "api/v2/pages"
    conf.post.return_value = {"id": "root"}

    with patch.object(publish, "ConfluenceV2", return_value=conf):
        publish.publish_docs(
            "https://x.atlassian.net/wiki",
            "u@e",
            "tok",
            "OKB",
            str(docs),
            "Documentation",
        )

    # Only the root page is created; template file is skipped.
    assert conf.post.call_count == 1
