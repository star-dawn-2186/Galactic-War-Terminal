import io
from playwright.async_api import async_playwright
import base64

def get_base64_image(image_path: str) -> str:

    with open(image_path, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode('utf-8')

    return f"data:image/png;base64,{b64_string}"

def format_html(new_title: str, new_body: str, img_path = "render_img/gwr_logo_long.png") -> str:
    b64_image_data = get_base64_image(img_path)    
    
    with open('template.html', "r", encoding="utf-8") as file:
        html_template = file.read()
        
    new_body = new_body.replace('_[', '<span class="text-hd-yellow hcml_link">').replace(']_', '</span>')
    new_body = new_body.replace('[', '<span class="text-hd-yellow">').replace(']', '</span>')
    
    return html_template.format(
        title=new_title, 
        body=new_body,
        image_data=b64_image_data
    )
    

async def render_html_to_image(html_content: str) -> io.BytesIO:
    """Takes an HTML string, renders it in a headless browser, and returns image bytes."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        page = await browser.new_page(viewport={"width": 800, "height": 5000}, device_scale_factor=2.0)
        
        await page.set_content(html_content)
        
        await page.wait_for_load_state("networkidle")
        
        container = page.locator("div.min-w-\\[284px\\]")
        
        image_bytes = await container.screenshot(
            omit_background=True,
            animations="disabled"
        )
        
        await browser.close()
        
        image_stream = io.BytesIO(image_bytes)
        image_stream.seek(0)
        
        return image_stream
