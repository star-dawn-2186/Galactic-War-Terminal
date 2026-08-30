"""
Sync the Helldivers Companion stylesheet + font mirror.

helldiverscompanion.com is a SvelteKit app: every redeploy regenerates all
asset filenames with new content hashes (e.g. storeEnts.d2LdHEoe.css ->
storeEnts.BGRzhOon.css) and the old files disappear from the server, which is
why hard-linked <link> tags in template.html break after a few days.

This script discovers the CSS files the site currently ships by reading its
client app manifest, downloads them into ./hdc_css under stable, hash-free
names (preserving the site's load order in .meta.json), and downloads the
font files the CSS references via @font-face (they use hashed filenames and
live next to the CSS on the site, so they're stored under their exact names
for the relative url() references to resolve).

render_mo4.py then injects <link> tags for everything in that folder, so
template.html never needs updating.

Usage:
    python scripts/sync_hdc_styles.py            # sync mirror from the site
    python scripts/sync_hdc_styles.py --check    # only report if out of date
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://helldiverscompanion.com"
CSS_DIR = Path(__file__).resolve().parent.parent / "hdc_css"
VERSION_FILE = CSS_DIR / ".version"
META_FILE = CSS_DIR / ".meta.json"

UA_HEADERS = {"User-Agent": "Mozilla/5.0 (GWT stylesheet mirror sync)"}

FONT_EXT_RE = re.compile(r"\.(?:woff2?|ttf|otf)$", re.I)


def fetch_url(url: str, retries: int = 4) -> bytes:
    last_exc = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA_HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_exc


def fetch_text(url: str) -> str:
    return fetch_url(url).decode("utf-8", errors="replace")


def get_site_version() -> str:
    try:
        data = fetch_text(f"{SITE}/_app/version.json")
        match = re.search(r'"version"\s*:\s*"([^"]+)"', data)
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"


def discover_css_files() -> list[str]:
    """Return the site's CSS asset filenames in the site's own load order."""
    root_html = fetch_text(f"{SITE}/")

    # The root page dynamically imports the app entry bundle.
    entry_match = re.search(r'import\("\.?/?(_app/immutable/entry/app\.[^"]+\.js)"\)', root_html)
    if not entry_match:
        raise RuntimeError("Could not locate the app entry bundle in the site HTML")

    # The entry bundle contains the full client manifest, including every
    # CSS asset as a relative import like "../assets/name.HASH.css".
    entry_js = fetch_text(f"{SITE}/{entry_match.group(1)}")
    seen, ordered = set(), []
    for name in re.findall(r'(?:\.\./assets|assets)/([A-Za-z0-9._-]+\.css)', entry_js):
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    if not ordered:
        raise RuntimeError("No CSS assets found in the app entry bundle")
    return ordered


def discover_css_fonts() -> list[str]:
    """Font filenames referenced by url() in the mirrored CSS files.

    The site's CSS declares @font-face with relative URLs like
    url(./HCSinclair-Normal.B0lI8GdS.woff), which resolve against the CSS
    file's own directory - so the fonts must be stored in hdc_css under
    exactly these hashed names (percent-decoded, since browsers decode the
    url() when resolving it to a file).
    """
    refs = set()
    for css_file in CSS_DIR.glob("*.css"):
        text = css_file.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"url\(([^)]+)\)", text):
            ref = m.group(1).strip().strip("\"'")
            if not ref.startswith("data:") and FONT_EXT_RE.search(ref):
                refs.add(urllib.parse.unquote(ref.rsplit("/", 1)[-1]))
    return sorted(refs)


def stable_name(hashed_name: str) -> str:
    """Strip the SvelteKit content hash: storeEnts.BGRzhOon.css -> storeEnts.css"""
    match = re.match(r"^(.+)\.[A-Za-z0-9_-]{8}(\.(?:css|woff2?|ttf|otf))$", hashed_name)
    return f"{match.group(1)}{match.group(2)}" if match else hashed_name


def write_file_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.write_bytes(content)
    return True


def sync_css() -> list[str]:
    hashed_files = discover_css_files()
    ordered_stable = []
    for hashed in hashed_files:
        local_name = stable_name(hashed)
        ordered_stable.append(local_name)
        content = fetch_url(f"{SITE}/_app/immutable/assets/{hashed}")
        if write_file_if_changed(CSS_DIR / local_name, content):
            print(f"  updated css: {local_name}")

    # Remove CSS files the site no longer ships.
    for existing in CSS_DIR.glob("*.css"):
        if existing.name not in ordered_stable:
            existing.unlink()
            print(f"  removed css: {existing.name}")
    return ordered_stable


def sync_fonts() -> list[str]:
    font_names = discover_css_fonts()
    for name in font_names:
        content = fetch_url(f"{SITE}/_app/immutable/assets/{urllib.parse.quote(name)}")
        if write_file_if_changed(CSS_DIR / name, content):
            print(f"  updated font: {name}")

    # Remove font files no longer referenced by the mirrored CSS.
    for existing in CSS_DIR.iterdir():
        if existing.is_file() and FONT_EXT_RE.search(existing.name) and existing.name not in font_names:
            existing.unlink()
            print(f"  removed font: {existing.name}")
    return font_names


def sync() -> int:
    version = get_site_version()
    print(f"Site version: {version}")

    CSS_DIR.mkdir(exist_ok=True)

    print("Syncing stylesheets...")
    css_order = sync_css()

    print("Syncing fonts (referenced by the mirrored CSS)...")
    try:
        font_names = sync_fonts()
    except Exception as exc:
        # CSS can still be synced if the font step fails; keep the existing
        # font files in that case.
        print(f"  WARNING: font sync skipped: {exc}")
        font_names = [f.name for f in CSS_DIR.iterdir()
                      if f.is_file() and FONT_EXT_RE.search(f.name)]

    META_FILE.write_text(
        json.dumps({"version": version, "css_order": css_order, "fonts": font_names}),
        encoding="utf-8",
    )
    VERSION_FILE.write_text(version, encoding="utf-8")
    print(f"Done. Mirror synced to {CSS_DIR}")
    return 0


def check() -> int:
    """Exit non-zero if the site deployed a new version since the last sync,
    or if the local mirror is incomplete (e.g. freshly deployed code where
    the CSS files exist but the referenced fonts were never synced)."""
    version = get_site_version()
    stored = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else None
    stale = stored != version

    # Also treat a mirror missing its recorded files (CSS or fonts) as stale,
    # even if the version matches.
    incomplete = False
    if META_FILE.exists():
        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
            expected = list(meta.get("css_order", [])) + list(meta.get("fonts", []))
            if not expected or not all((CSS_DIR / name).exists() for name in expected):
                incomplete = True
        except (json.JSONDecodeError, OSError):
            incomplete = True
    else:
        incomplete = True

    if not stale and not incomplete:
        print(f"Up to date (site version {version}).")
        return 0
    if stale:
        print(f"Out of date: site version {version}, mirror synced at {stored or 'never'}.")
    if incomplete:
        print("Mirror incomplete: expected files are missing locally.")
    print("Run `python scripts/sync_hdc_styles.py` to refresh.")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mirror helldiverscompanion.com stylesheets locally")
    parser.add_argument("--check", action="store_true", help="only report whether the mirror is stale")
    args = parser.parse_args()
    try:
        sys.exit(check() if args.check else sync())
    except Exception as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        sys.exit(2)
