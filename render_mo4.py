import io
import json
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright
import base64

# Local mirror of helldiverscompanion.com stylesheets, kept fresh by
# `python scripts/sync_hdc_styles.py` (the site's asset URLs are content-
# hashed and rot on every redeploy).
HDC_CSS_DIR = Path(__file__).resolve().parent / "hdc_css"

def get_base64_image(image_path: str) -> str:

    with open(image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')

    return f"data:image/png;base64,{b64_string}"

def get_style_links() -> str:
    if not HDC_CSS_DIR.exists() or not any(HDC_CSS_DIR.glob("*.css")):
        print("WARNING: no mirrored stylesheets found; run `python scripts/sync_hdc_styles.py`")
        return ""

    # Load CSS in the order the site itself uses (recorded by the sync
    # script); cascade order matters when rules tie on specificity. The
    # site's @font-face rules use relative url()s, which resolve against
    # each CSS file's directory, so the mirrored fonts in hdc_css/ apply.
    css_names = []
    meta_path = HDC_CSS_DIR / ".meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            css_names = [n for n in meta.get("css_order", []) if (HDC_CSS_DIR / n).exists()]
        except (json.JSONDecodeError, OSError):
            pass
    css_names += [f.name for f in sorted(HDC_CSS_DIR.glob("*.css")) if f.name not in css_names]

    return "\n".join(f'<link rel="stylesheet" href="{(HDC_CSS_DIR / name).as_uri()}">' for name in css_names)

def format_html(new_title: str, new_body: str, img_path = "render_img/SuperEarthGWR-2.png") -> str:
    b64_image_data = get_base64_image(img_path)    
    
    with open('template.html', "r", encoding="utf-8") as file:
        html_template = file.read()
        
    new_body = new_body.replace('_[', '<span class="text-hd-yellow hcml_link">').replace(']_', '</span>')
    new_body = new_body.replace('[', '<span class="text-hd-yellow">').replace(']', '</span>')
    
    return html_template.format(
        title=new_title, 
        body=new_body,
        image_data=b64_image_data,
        styles=get_style_links()
    )
    

async def render_html_to_image(html_content: str) -> io.BytesIO:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        page = await browser.new_page(viewport={"width": 800, "height": 5000}, device_scale_factor=2.0)
        
        # Navigate to a real file:// document instead of set_content: an
        # about:blank page blocks file:// stylesheets, so the mirrored CSS
        # and fonts would never apply.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as tmp:
            tmp.write(html_content)
            tmp_path = Path(tmp.name)
        
        try:
            await page.goto(tmp_path.as_uri())
            
            await page.wait_for_load_state("networkidle")
            
            # Ensure the mirrored fonts are actually loaded before the
            # screenshot, otherwise text renders in the fallback font.
            await page.evaluate("document.fonts.ready")
            
            fonts = await page.evaluate(
                "Array.from(document.fonts).filter(f => f.status !== 'unloaded')"
                ".map(f => f.family + ':' + f.status)"
            )
            if not fonts:
                print("WARNING: no fonts loaded in the render; is hdc_css/ in sync on this machine?")
            elif any(f.endswith(':error') for f in fonts):
                print(f"WARNING: font load errors in the render: {fonts}")
            
            container = page.locator("div.min-w-\\[284px\\]")
            
            image_bytes = await container.screenshot(
                omit_background=True,
                animations="disabled"
            )
        finally:
            tmp_path.unlink(missing_ok=True)
            await browser.close()
        
        image_stream = io.BytesIO(image_bytes)
        image_stream.seek(0)
        
        return image_stream
