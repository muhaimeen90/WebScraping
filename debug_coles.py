#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright

async def debug_coles_page():
    """Debug Coles page access and content."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see what's happening
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print("Visiting Coles homepage...")
            await page.goto('https://shop.coles.com.au', timeout=15000)
            await asyncio.sleep(3)
            
            print("Navigating to product page...")
            url = 'https://www.coles.com.au/product/coca-cola-classic-soft-drink-bottle-1.25l-123011'
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)
            
            # Check page title
            title = await page.title()
            print(f"Page title: {title}")
            
            # Check if we're blocked or redirected
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            # Try to handle popups/modals
            try:
                await page.keyboard.press('Escape')
                await asyncio.sleep(2)
            except Exception:
                pass
            
            # Look for any text with $
            dollar_elements = await page.query_selector_all(':has-text("$")')
            print(f"Found {len(dollar_elements)} elements containing '$'")
            
            for i, element in enumerate(dollar_elements[:15]):
                try:
                    text = await element.text_content()
                    if text and len(text.strip()) < 50:
                        print(f"  {i+1}. '{text.strip()}'")
                except Exception:
                    continue
            
            # Try alternative approach - look for price in page content
            page_content = await page.content()
            import re
            price_matches = re.findall(r'\$\d+\.?\d*', page_content)
            unique_prices = list(set(price_matches))
            print(f"\nFound price patterns in HTML: {unique_prices}")
            
            await asyncio.sleep(5)  # Keep browser open to see
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_coles_page())
