import os
import sys
import base64
import pytest
from PIL import Image

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.styles import (BANNER_PATH, LOGO_PATH, MARK_PATH, WORDMARK_PATH, TAGLINE,
                          get_banner_base64, get_logo_base64, render_brand_header)


def test_banner_file_exists_and_valid():
    """Verify that the new brand banner asset exists, is non-empty, and has expected dimensions."""
    assert os.path.exists(BANNER_PATH), f"Banner file not found at {BANNER_PATH}"
    file_size = os.path.getsize(BANNER_PATH)
    assert file_size > 10000, f"Banner file size suspiciously small: {file_size} bytes"

    # Verify PIL can open and validate dimensions
    with Image.open(BANNER_PATH) as img:
        assert img.format == "PNG"
        width, height = img.size
        assert width >= 800, f"Expected banner width >= 800, got {width}"
        assert height >= 200, f"Expected banner height >= 200, got {height}"
        # Aspect ratio should be roughly wide banner (~3.0 to ~3.8)
        aspect = width / height
        assert 2.5 <= aspect <= 4.5, f"Expected wide banner aspect ratio, got {aspect}"


def test_banner_base64_generation():
    """Verify that get_banner_base64 correctly converts banner into valid base64 string."""
    b64_str = get_banner_base64()
    assert isinstance(b64_str, str)
    assert len(b64_str) > 1000, "Base64 banner string is unexpectedly short"

    # Decode and verify header matches PNG magic bytes
    decoded = base64.b64decode(b64_str)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n", "Decoded base64 does not match PNG signature"


def test_logo_asset_integrity():
    """Verify that the brand logo file exists and generates base64."""
    assert os.path.exists(LOGO_PATH)
    logo_b64 = get_logo_base64()
    assert len(logo_b64) > 100


def test_brand_mark_and_wordmark_assets():
    """Verify the logo mark and wordmark used in the Home logo bar exist and are transparent PNGs."""
    for path in (MARK_PATH, WORDMARK_PATH):
        assert os.path.exists(path), f"Missing brand asset: {path}"
        with Image.open(path) as img:
            assert img.format == "PNG"
            assert img.mode == "RGBA", "Brand images should have a transparent background"


def test_tagline_is_one_honest_line():
    """The tagline promises free AND low-cost care (results include sliding-scale clinics)."""
    assert TAGLINE == "Free & low-cost care. Know where to go."
    assert len(TAGLINE) <= 45, "Tagline should fit on one line on a phone"


def test_brand_header_rendering(monkeypatch):
    """Verify render_brand_header produces the logo bar: mark, wordmark and tagline."""
    rendered_markdowns = []

    def mock_markdown(body, unsafe_allow_html=False):
        rendered_markdowns.append(body)

    import streamlit as st
    monkeypatch.setattr(st, "markdown", mock_markdown)

    render_brand_header()
    assert len(rendered_markdowns) == 1
    content = rendered_markdowns[0]

    assert "cz-brand" in content
    assert "Free &amp; low-cost care. Know where to go." in content
    assert content.count("data:image/png;base64,") == 2, "Expected the mark and the wordmark images"
    assert 'alt="CareAtZero"' in content


def test_brand_header_fallback_rendering(monkeypatch):
    """Verify the logo bar falls back to text when the brand images are unavailable."""
    rendered_markdowns = []

    def mock_markdown(body, unsafe_allow_html=False):
        rendered_markdowns.append(body)

    import streamlit as st
    monkeypatch.setattr(st, "markdown", mock_markdown)
    import utils.styles as styles_mod
    monkeypatch.setattr(styles_mod, "_file_base64", lambda path: "")

    render_brand_header()
    assert len(rendered_markdowns) == 1
    content = rendered_markdowns[0]

    assert "cz-brand" in content
    assert "Free &amp; low-cost care. Know where to go." in content
    assert "CareAt" in content
    assert "Zero" in content
    assert "data:image/png;base64," not in content
