#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright

async def inspect_coles_page():
    """Inspect Coles page to find current price selectors."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Visit homepage first
            await page.goto('https://shop.coles.com.au', timeout=15000)
            await asyncio.sleep(2)
            
            # Navigate to product page
            url = 'https://www.coles.com.au/product/coca-cola-classic-soft-drink-bottle-1.25l-123011'
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # Handle modals
            try:
                await page.keyboard.press('Escape')
                await asyncio.sleep(1)
            except Exception:
                pass
            
            # Find all elements that might contain price
            price_elements = await page.query_selector_all('*[class*="price"], *[data-testid*="price"], span:has-text("$")')
            
            print(f"Found {len(price_elements)} potential price elements on Coles:")
            for i, element in enumerate(price_elements[:10]):  # Show first 10
                try:
                    text = await element.text_content()
                    tag = await element.evaluate('el => el.tagName')
                    classes = await element.get_attribute('class')
                    testid = await element.get_attribute('data-testid')
                    if text and '$' in text:
                        print(f"  {i+1}. {tag} - classes: {classes} - testid: {testid} - text: '{text.strip()}'")
                except Exception as e:
                    print(f"  {i+1}. Error reading element: {e}")
                    
        except Exception as e:
            print(f"Coles inspection error: {e}")
        finally:
            await browser.close()

async def inspect_iga_page():
    """Inspect IGA page to find current price selectors."""
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0'
        )
        page = await context.new_page()
        
        try:
            # Navigate to product page
            url = 'https://www.igashop.com.au/product/coca-cola-classic-soft-drink-bottle-13011'
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # Find all elements that might contain price
            price_elements = await page.query_selector_all('*[class*="price"], *[data-testid*="price"], span:has-text("$")')
            
            print(f"\nFound {len(price_elements)} potential price elements on IGA:")
            for i, element in enumerate(price_elements[:10]):  # Show first 10
                try:
                    text = await element.text_content()
                    tag = await element.evaluate('el => el.tagName')
                    classes = await element.get_attribute('class')
                    testid = await element.get_attribute('data-testid')
                    if text and '$' in text:
                        print(f"  {i+1}. {tag} - classes: {classes} - testid: {testid} - text: '{text.strip()}'")
                except Exception as e:
                    print(f"  {i+1}. Error reading element: {e}")
                    
        except Exception as e:
            print(f"IGA inspection error: {e}")
        finally:
            await browser.close()

async def main():
    await inspect_coles_page()
    await inspect_iga_page()

if __name__ == "__main__":
    asyncio.run(main())
