import aiofiles
from pydantic_ai import RunContext


# async def fetch_job_content(ctx: RunContext, url: str) -> str:
#     """
#     MCP Tool: Navigates to a URL and extracts the main text content as Markdown.
#     """
#     print(f"   [Tool] 🕷️ Scraping {url}...")
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context(
#             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#         )
#         page = await context.new_page()
#         try:
#             # Wait until the network is idle to ensure JS has loaded content.
#             await page.goto(url, wait_until="networkidle", timeout=30000)
#
#             # Wait for a more specific selector that contains the main job content.
#             main_content_selector = "main"
#             await page.wait_for_selector(main_content_selector, timeout=15000)
#             content = await page.inner_html(main_content_selector)
#             print(f"   [Tool] ✅ Scraped content from {url}")
#
#             # Convert to Markdown to strip noise
#             h = html2text.HTML2Text()
#             h.ignore_links = True
#             h.ignore_images = True
#             h.body_width = 0
#             return h.handle(content)[:20000]  # Limit context
#         except Exception as e:
#             return f"Error scraping: {e}"
#         finally:
#             await browser.close()


async def read_job_content_file(ctx: RunContext, file_path: str) -> str:
    """
    MCP Tool: Navigates to a URL and extracts the main text content as Markdown.
    """
    print(f"   [Tool] 🗄️️ Reading job content from a file located at  {file_path}...")
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        try:
            return await f.read()
        except Exception as e:
            # Seems the file isn't encoded in utf-8, try reading as binary and decode
            with aiofiles.open(file_path, "rb") as fb:
                content = await fb.read()
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    return f"Error reading file: {e}"
