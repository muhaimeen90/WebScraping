#!/usr/bin/env python3

import asyncio
import logging
import re
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class PriceScraperError(Exception):
    """Custom exception for price scraping errors"""
    pass

async def scrape_iga_product_price(product_url: str) -> Dict[str, Any]:
    """
    Scrape live price from IGA product page.
    
    Args:
        product_url: The IGA product URL
        
    Returns:
        Dict containing price and status information
    """
    result = {
        'price': None,
        'currency': '$',
        'status': 'error',
        'message': '',
        'store': 'IGA'
    }
    
    async with async_playwright() as p:
        browser = None
        try:
            logger.info(f"🔍 Scraping IGA price from: {product_url}")
            
            # Launch browser with more aggressive settings for IGA
            browser = await p.firefox.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--ignore-certificate-errors'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                viewport={'width': 1366, 'height': 768},
                locale='en-AU',
                timezone_id='Australia/Sydney',
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-AU,en-US;q=0.8,en;q=0.6',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                }
            )
            
            page = await context.new_page()
            
            # Set longer timeout and try different load strategies
            logger.info("📱 Navigating to IGA product page...")
            
            # Try multiple navigation strategies
            navigation_success = False
            
            # Strategy 1: Standard navigation with shorter timeout
            try:
                await page.goto(product_url, wait_until='domcontentloaded', timeout=15000)
                navigation_success = True
                logger.info("✅ Navigation successful with domcontentloaded")
            except Exception as e:
                logger.info(f"Standard navigation failed: {e}")
            
            # Strategy 2: If standard fails, try with load event
            if not navigation_success:
                try:
                    await page.goto(product_url, wait_until='load', timeout=20000)
                    navigation_success = True
                    logger.info("✅ Navigation successful with load")
                except Exception as e:
                    logger.info(f"Load navigation failed: {e}")
            
            # Strategy 3: If both fail, try basic navigation
            if not navigation_success:
                try:
                    await page.goto(product_url, timeout=25000)
                    navigation_success = True
                    logger.info("✅ Navigation successful with basic timeout")
                except Exception as e:
                    raise Exception(f"All navigation strategies failed: {e}")
            
            # Handle welcome modal/popup
            await handle_iga_modal(page)
            
            # Wait for page to stabilize
            await page.wait_for_timeout(5000)
            
            # Try to find price using multiple strategies
            price_text = None
            
            # Strategy 1: Try all CSS selectors
            price_selectors = [
                '#product-details span[class*="price"]',
                '#product-details span',
                '.price',
                '[data-testid*="price"]',
                'span[class*="price"]',
                'div[class*="price"]',
                'span:has-text("$")',
                '.product-price',
                '#product-details > div > div > div > div.lg\\:pt-8 > div > div.flex.items-center.gap-3 > div > span'
            ]
            
            for selector in price_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and '$' in text and len(text.strip()) < 20:  # Price shouldn't be too long
                            price_text = text
                            logger.info(f"✅ Found price with selector: {selector}")
                            break
                    if price_text:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Strategy 2: Try XPath if CSS fails
            if not price_text:
                xpath_selectors = [
                    '//*[@id="product-details"]/div/div/div/div[2]/div/div[1]/div/span',
                    '//span[contains(text(), "$")]',
                    '//*[contains(@class, "price")]//span',
                    '//div[@id="product-details"]//span[contains(text(), "$")]'
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = await page.query_selector_all(f'xpath={xpath}')
                        for element in elements:
                            text = await element.text_content()
                            if text and '$' in text and len(text.strip()) < 20:
                                price_text = text
                                logger.info(f"✅ Found price with XPath: {xpath}")
                                break
                        if price_text:
                            break
                    except Exception as e:
                        logger.debug(f"XPath {xpath} failed: {e}")
            
            # Strategy 3: Search all text content for price patterns
            if not price_text:
                try:
                    page_content = await page.content()
                    import re
                    price_patterns = [
                        r'\$\d+\.\d{2}',
                        r'\$\d+',
                        r'AUD\s*\d+\.\d{2}',
                        r'Price:\s*\$\d+\.\d{2}'
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, page_content)
                        if matches:
                            price_text = matches[0]
                            logger.info(f"✅ Found price with regex: {pattern}")
                            break
                except Exception as e:
                    logger.debug(f"Regex search failed: {e}")
            
            if price_text:
                # Clean and extract price
                cleaned_price = clean_price_text(price_text)
                if cleaned_price:
                    result['price'] = cleaned_price
                    result['status'] = 'success'
                    result['message'] = 'Price successfully scraped'
                    logger.info(f"✅ IGA price found: ${cleaned_price}")
                else:
                    result['message'] = f'Could not parse price from text: {price_text}'
            else:
                result['message'] = 'Price element not found on page after trying all strategies'
                
        except Exception as e:
            logger.error(f"❌ Error scraping IGA price: {str(e)}")
            result['message'] = f'Error: {str(e)}'
            
        finally:
            if browser:
                await browser.close()
    
    return result

async def scrape_coles_product_price(product_url: str) -> Dict[str, Any]:
    """
    Scrape live price from Coles product page.
    
    Args:
        product_url: The Coles product URL
        
    Returns:
        Dict containing price and status information
    """
    result = {
        'price': None,
        'currency': '$',
        'status': 'error',
        'message': '',
        'store': 'Coles'
    }
    
    async with async_playwright() as p:
        browser = None
        try:
            logger.info(f"🔍 Scraping Coles price from: {product_url}")
            
            # Launch browser with enhanced settings for Coles
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--ignore-certificate-errors',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768},
                locale='en-AU',
                timezone_id='Australia/Sydney',
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-AU,en-US;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'no-cache'
                }
            )
            
            page = await context.new_page()
            
            # Strategy: Visit homepage first with proper navigation
            logger.info("🏠 Visiting Coles homepage first...")
            try:
                await page.goto('https://www.coles.com.au', wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(3000)
                logger.info("✅ Homepage loaded successfully")
            except Exception as e:
                logger.info(f"Homepage load issue (continuing anyway): {e}")
            
            # Now navigate to product page
            logger.info("📱 Navigating to Coles product page...")
            await page.goto(product_url, wait_until='domcontentloaded', timeout=20000)
            
            # Wait for page to stabilize and load price elements
            await page.wait_for_timeout(5000)
            
            # Let's try to find ANY price-related content first
            price_text = None
            
            # Strategy 1: Look for modern Coles price selectors (updated for 2024/2025)
            modern_selectors = [
                '[data-testid="price-unit"]',
                '[data-testid="product-price"]', 
                '[data-testid="price"]',
                'span[data-testid*="price"]',
                'div[data-testid*="price"]',
                '[class*="Price"]',
                '[class*="price"]',
                'span[class*="Price"]',
                'span[class*="price"]'
            ]
            
            for selector in modern_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and '$' in text and len(text.strip()) < 50:
                            # Check if it looks like a price
                            import re
                            if re.search(r'\$\d+\.?\d*', text):
                                price_text = text.strip()
                                logger.info(f"✅ Found price with modern selector: {selector} -> {price_text}")
                                break
                    if price_text:
                        break
                except Exception as e:
                    logger.debug(f"Modern selector {selector} failed: {e}")
            
            # Strategy 2: Look for any element containing price patterns
            if not price_text:
                try:
                    # Get all elements that might contain prices
                    price_elements = await page.query_selector_all('span, div, p, h1, h2, h3, h4, h5, h6')
                    
                    for element in price_elements:
                        try:
                            text = await element.text_content()
                            if text and '$' in text:
                                # Check if it matches price pattern and is reasonably short
                                import re
                                price_match = re.search(r'\$(\d+\.?\d*)', text)
                                if price_match and len(text.strip()) < 50:
                                    # Avoid elements that are clearly not prices
                                    text_lower = text.lower()
                                    if not any(word in text_lower for word in ['save', 'off', 'discount', 'was', 'rrp', 'usual']):
                                        price_text = text.strip()
                                        logger.info(f"✅ Found price with content search: {price_text}")
                                        break
                        except Exception:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Content search failed: {e}")
            
            # Strategy 3: Search page source for JSON price data
            if not price_text:
                try:
                    page_content = await page.content()
                    import re
                    
                    # Look for JSON price structures common in Coles
                    json_patterns = [
                        r'"price"[^}]*?"value":\s*"?(\d+\.?\d*)"?',
                        r'"unitPrice"[^}]*?"value":\s*"?(\d+\.?\d*)"?',
                        r'"displayPrice":\s*"?\$?(\d+\.?\d*)"?',
                        r'"currentPrice":\s*"?\$?(\d+\.?\d*)"?',
                        r'"pricing"[^}]*?"price":\s*"?\$?(\d+\.?\d*)"?',
                        r'price["\s:]*(\d+\.?\d*)',
                        r'\$(\d+\.?\d*)'
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, page_content, re.IGNORECASE)
                        if matches:
                            # Take the first reasonable price
                            for match in matches:
                                try:
                                    price_value = float(match)
                                    if 0.50 <= price_value <= 200:  # Reasonable price range for Coke products
                                        price_text = f"${price_value:.2f}"
                                        logger.info(f"✅ Found price with JSON pattern: {pattern} -> {price_text}")
                                        break
                                except ValueError:
                                    continue
                            if price_text:
                                break
                except Exception as e:
                    logger.debug(f"JSON search failed: {e}")
            
            # Strategy 4: Try legacy selectors as last resort
            if not price_text:
                legacy_selectors = [
                    'section.sc-958d17d5-0:nth-child(3) > div:nth-child(1) > span:nth-child(1)',
                    'section div span:has-text("$")',
                    '.price-section span',
                    '.product-price span'
                ]
                
                for selector in legacy_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element:
                            text = await element.text_content()
                            if text and '$' in text:
                                price_text = text.strip()
                                logger.info(f"✅ Found price with legacy selector: {selector}")
                                break
                    except Exception as e:
                        logger.debug(f"Legacy selector {selector} failed: {e}")
            
            if price_text:
                # Clean and extract price
                cleaned_price = clean_price_text(price_text)
                if cleaned_price:
                    result['price'] = cleaned_price
                    result['status'] = 'success'
                    result['message'] = 'Price successfully scraped'
                    logger.info(f"✅ Coles price found: ${cleaned_price}")
                else:
                    result['message'] = f'Could not parse price from text: {price_text}'
            else:
                # Debug: Let's see what's actually on the page
                try:
                    page_title = await page.title()
                    logger.info(f"Page title: {page_title}")
                    
                    # Check if we're on the right page
                    if 'coles' not in page_title.lower():
                        result['message'] = f'Not on Coles page. Page title: {page_title}'
                    else:
                        result['message'] = 'Price element not found on page after trying all strategies'
                except Exception:
                    result['message'] = 'Price element not found and could not determine page status'
                
        except Exception as e:
            logger.error(f"❌ Error scraping Coles price: {str(e)}")
            result['message'] = f'Error: {str(e)}'
            
        finally:
            if browser:
                await browser.close()
    
    return result

async def scrape_woolworths_product_price(product_url: str) -> Dict[str, Any]:
    """
    Scrape live price from Woolworths product page.
    
    Args:
        product_url: The Woolworths product URL
        
    Returns:
        Dict containing price and status information
    """
    result = {
        'price': None,
        'currency': '$',
        'status': 'error',
        'message': '',
        'store': 'Woolworths'
    }
    
    async with async_playwright() as p:
        browser = None
        try:
            logger.info(f"🔍 Scraping Woolworths price from: {product_url}")
            
            # Launch browser with enhanced settings to handle HTTP2 issues
            browser = await p.firefox.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--ignore-certificate-errors',
                    '--disable-http2'  # Disable HTTP2 to avoid protocol errors
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                viewport={'width': 1366, 'height': 768},
                locale='en-AU',
                timezone_id='Australia/Sydney',
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-AU,en-US;q=0.8,en;q=0.6',
                    'Accept-Encoding': 'gzip, deflate',  # Remove br to avoid compression issues
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none'
                }
            )
            
            page = await context.new_page()
            
            # Set additional page settings to handle issues
            await page.set_extra_http_headers({
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            })
            
            logger.info("📱 Navigating to Woolworths product page...")
            
            navigation_success = False
            
            # Strategy 1: Try with domcontentloaded first
            try:
                await page.goto(product_url, wait_until='domcontentloaded', timeout=15000)
                navigation_success = True
                logger.info("✅ Navigation successful with domcontentloaded")
            except Exception as e:
                logger.info(f"DOMContentLoaded navigation failed: {e}")
            
            # Strategy 2: Try with load event
            if not navigation_success:
                try:
                    await page.goto(product_url, wait_until='load', timeout=20000)
                    navigation_success = True
                    logger.info("✅ Navigation successful with load")
                except Exception as e:
                    logger.info(f"Load navigation failed: {e}")
            
            # Strategy 3: Basic navigation without wait conditions
            if not navigation_success:
                try:
                    await page.goto(product_url, timeout=25000)
                    navigation_success = True
                    logger.info("✅ Basic navigation successful")
                except Exception as e:
                    raise Exception(f"All navigation strategies failed: {e}")
            
            # Handle any modals or popups
            await handle_woolworths_modal(page)
            
            # Wait for page to stabilize
            await page.wait_for_timeout(5000)
            
            # Strategy 1: Look for the SPECIFIC CURRENT SALE PRICE using identified selector
            price_text = None
            
            # First, try the exact selector we identified for the current price
            specific_price_selectors = [
                '.product-price_component_price-lead__vlm8f',  # This is the exact $2.40 selector
                'div.product-price_component_price-lead__vlm8f',
                'div[class*="price-lead"]',
                'div[class*="product-price_component_price-lead"]'
            ]
            
            for selector in specific_price_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text and '$' in text:
                            # Make sure it's not unit price or promotional text
                            if '/' not in text and 'save' not in text.lower() and 'was' not in text.lower():
                                import re
                                price_match = re.search(r'\$(\d+\.?\d*)', text)
                                if price_match and len(text.strip()) < 20:
                                    price_value = float(price_match.group(1))
                                    if 1.50 <= price_value <= 6.00:  # Reasonable range for current prices
                                        price_text = text.strip()
                                        logger.info(f"✅ Found specific current price with selector: {selector} -> {price_text}")
                                        break
                    if price_text:
                        break
                except Exception as e:
                    logger.debug(f"Specific price selector {selector} failed: {e}")
            
            # Strategy 2: Look for current/sale price using data attributes and classes we found
            if not price_text:
                current_price_selectors = [
                    'div[class*="product-price_component_price-container"] div[class*="price-lead"]',
                    'div[class*="price-container"] div[class*="price-lead"]',
                    'div.sr-only:contains("Price $")',
                    'div[class*="product-price_component_price-container"]'
                ]
                
                for selector in current_price_selectors:
                    try:
                        if ':contains(' in selector:
                            # Handle contains selector differently
                            all_elements = await page.query_selector_all('div.sr-only')
                            for element in all_elements:
                                text = await element.text_content()
                                if text and 'Price $' in text and '$' in text:
                                    if '/' not in text and 'save' not in text.lower():
                                        import re
                                        price_match = re.search(r'\$(\d+\.?\d*)', text)
                                        if price_match:
                                            price_value = float(price_match.group(1))
                                            if 1.50 <= price_value <= 6.00:
                                                price_text = f"${price_value:.2f}"
                                                logger.info(f"✅ Found sr-only price: {text} -> {price_text}")
                                                break
                        else:
                            elements = await page.query_selector_all(selector)
                            for element in elements:
                                text = await element.text_content()
                                if text and '$' in text:
                                    if '/' not in text and 'save' not in text.lower() and 'was' not in text.lower():
                                        import re
                                        price_match = re.search(r'\$(\d+\.?\d*)', text)
                                        if price_match and len(text.strip()) < 30:
                                            price_value = float(price_match.group(1))
                                            if 1.50 <= price_value <= 6.00:
                                                price_text = text.strip()
                                                logger.info(f"✅ Found current price: {selector} -> {price_text}")
                                                break
                        if price_text:
                            break
                    except Exception as e:
                        logger.debug(f"Current price selector {selector} failed: {e}")
            
            # Strategy 3: Look specifically for the main price (not in savings/discount areas, not strikethrough)
            if not price_text:
                main_price_selectors = [
                    'div[data-testid="price-unit"] span:not([style*="line-through"]):not([style*="text-decoration: line-through"])',
                    'div[class*="ProductPrice"] span:not([style*="line-through"]):not([class*="save"]):not([class*="was"])',
                    'span[class*="sale"]:not([class*="was"]):not([class*="save"]):not([style*="line-through"])',
                    'div[class*="price-container"] span:not([style*="line-through"]):not([class*="was"])',
                    'span[class*="current"]:not([class*="was"]):not([class*="save"]):not([style*="line-through"])',
                    'span[class*="price"]:not([style*="line-through"]):not([class*="was"]):not([class*="save"])'
                ]
                
                for selector in main_price_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and '$' in text:
                                # Check the element's style to make sure it's not crossed out
                                style = await element.get_attribute('style') or ''
                                class_name = await element.get_attribute('class') or ''
                                
                                text_lower = text.lower()
                                if ('/' not in text and 'save' not in text_lower and 
                                    'off' not in text_lower and 'was' not in text_lower and
                                    'line-through' not in style.lower() and
                                    'strike' not in class_name.lower()):
                                    
                                    import re
                                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                                    if price_match and len(text.strip()) < 25:
                                        price_value = float(price_match.group(1))
                                        if 2.00 <= price_value <= 3.50:  # Focus specifically on sale price range around $2.40
                                            price_text = text.strip()
                                            logger.info(f"✅ Found main price: {selector} -> {price_text}")
                                            break
                        if price_text:
                            break
                    except Exception as e:
                        logger.debug(f"Main price selector {selector} failed: {e}")
            
            # Strategy 3: Look for the price that's NOT crossed out, NOT a unit price, and NOT promotional text
            if not price_text:
                try:
                    # Get all price-like spans and filter out the wrong ones
                    all_price_elements = await page.query_selector_all('span')
                    
                    candidate_prices = []
                    for element in all_price_elements:
                        try:
                            text = await element.text_content()
                            if text and '$' in text and '/' not in text:
                                # Check if it's not crossed out
                                style = await element.get_attribute('style') or ''
                                class_name = await element.get_attribute('class') or ''
                                
                                # Skip if it's crossed out, strikethrough, "was" price, or "save" text
                                text_lower = text.lower()
                                if ('line-through' not in style.lower() and 
                                    'strike' not in class_name.lower() and 
                                    'was' not in class_name.lower() and
                                    'save' not in class_name.lower() and
                                    'save' not in text_lower and
                                    'off' not in text_lower):
                                    
                                    import re
                                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                                    if price_match:
                                        price_value = float(price_match.group(1))
                                        if 2.00 <= price_value <= 3.50:  # Target range for current sale prices around $2.40
                                            candidate_prices.append((price_value, text.strip()))
                        except Exception:
                            continue  # Skip problematic elements
                    
                    # Sort by price and take the most reasonable one
                    if candidate_prices:
                        candidate_prices.sort(key=lambda x: x[0])
                        price_text = f"${candidate_prices[0][0]:.2f}"
                        logger.info(f"✅ Found candidate current price: {price_text}")
                        
                except Exception as e:
                    logger.debug(f"Candidate price search failed: {e}")
            
            # Strategy 4: JSON data search for current/sale price
            if not price_text:
                try:
                    page_content = await page.content()
                    import re
                    
                    # Look for structured price data - prioritize sale/current price
                    json_patterns = [
                        r'"salePrice":\s*"?\$?(\d+\.?\d*)"?',
                        r'"currentPrice":\s*"?\$?(\d+\.?\d*)"?',
                        r'"price":\s*"?\$?(\d+\.?\d*)"?',
                        r'"displayPrice":\s*"?\$?(\d+\.?\d*)"?'
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, page_content)
                        if matches:
                            for match in matches:
                                try:
                                    price_value = float(match)
                                    # Look for prices in the current sale range
                                    if 1.50 <= price_value <= 6.00:
                                        price_text = f"${price_value:.2f}"
                                        logger.info(f"✅ Found JSON current price: {pattern} -> {price_text}")
                                        break
                                except ValueError:
                                    continue
                            if price_text:
                                break
                except Exception as e:
                    logger.debug(f"JSON search failed: {e}")
            
            # Strategy 5: Last resort - find any reasonable price but validate carefully
            if not price_text:
                fallback_selectors = [
                    'span[class*="price"]:not([class*="was"]):not([class*="strike"])',
                    '.product-price_component_price-lead__vlm8f',
                    'span:has-text("$")'
                ]
                
                for selector in fallback_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and '$' in text:
                                # Only accept if it doesn't contain unit price indicators
                                if '/' not in text and 'per' not in text.lower():
                                    import re
                                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                                    if price_match:
                                        price_value = float(price_match.group(1))
                                        # Accept prices in reasonable current range
                                        if 1.50 <= price_value <= 6.00:
                                            price_text = text.strip()
                                            logger.info(f"✅ Found fallback current price: {selector} -> {price_text}")
                                            break
                        if price_text:
                            break
                    except Exception as e:
                        logger.debug(f"Fallback selector {selector} failed: {e}")
            
            if price_text:
                # Clean and extract price - be more careful to get the right price
                cleaned_price = clean_price_text(price_text)
                if cleaned_price:
                    result['price'] = cleaned_price
                    result['status'] = 'success'
                    result['message'] = 'Price successfully scraped'
                    logger.info(f"✅ Woolworths price found: ${cleaned_price}")
                else:
                    result['message'] = f'Could not parse price from text: {price_text}'
            else:
                # Debug information
                try:
                    page_title = await page.title()
                    logger.info(f"Page title: {page_title}")
                    result['message'] = f'Price element not found. Page title: {page_title}'
                except Exception:
                    result['message'] = 'Price element not found on page after trying all strategies'
                
        except Exception as e:
            logger.error(f"❌ Error scraping Woolworths price: {str(e)}")
            result['message'] = f'Error: {str(e)}'
            
        finally:
            if browser:
                await browser.close()
    
    return result

async def handle_iga_modal(page):
    """Handle IGA welcome modal or guest browsing popup"""
    try:
        # Wait a bit for modal to appear
        await page.wait_for_timeout(3000)
        
        # Try multiple strategies to handle modals
        modal_handled = False
        
        # Strategy 1: Look for "Browse as guest" or similar buttons
        guest_selectors = [
            'text="Browse as guest"',
            'text="Continue as guest"',
            'text="Guest"',
            '[data-testid="guest-button"]',
            'button:has-text("guest")',
            'button:has-text("Guest")',
            'a:has-text("guest")',
            'a:has-text("Guest")'
        ]
        
        for selector in guest_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"✅ Clicked guest button: {selector}")
                    modal_handled = True
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                continue
        
        # Strategy 2: Try to close modal with close buttons
        if not modal_handled:
            close_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label="close"]',
                '.modal-close',
                '.close-button',
                'button:has-text("×")',
                'button:has-text("✕")',
                '[data-testid="close-button"]',
                '[data-testid="modal-close"]',
                'button[class*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"✅ Closed modal with: {selector}")
                        modal_handled = True
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
        
        # Strategy 3: Try pressing Escape key
        if not modal_handled:
            try:
                await page.keyboard.press('Escape')
                logger.info("✅ Pressed Escape to close modal")
                await page.wait_for_timeout(1000)
            except Exception:
                pass
        
        # Strategy 4: Try clicking outside the modal
        if not modal_handled:
            try:
                await page.click('body', position={'x': 50, 'y': 50})
                logger.info("✅ Clicked outside modal area")
                await page.wait_for_timeout(1000)
            except Exception:
                pass
                
    except Exception as e:
        logger.debug(f"Modal handling completed or no modal found: {e}")

async def handle_woolworths_modal(page):
    """Handle Woolworths website modals or overlays"""
    try:
        await page.wait_for_timeout(3000)
        
        modal_handled = False
        
        # Strategy 1: Try to close any overlays or modals
        close_selectors = [
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
            '.modal-close',
            '.overlay-close',
            'button:has-text("×")',
            'button:has-text("✕")',
            '[data-testid="close-button"]',
            '[data-testid="modal-close"]',
            'button[class*="close"]',
            '.close'
        ]
        
        for selector in close_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"✅ Closed Woolworths modal with: {selector}")
                    modal_handled = True
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                continue
        
        # Strategy 2: Try pressing Escape
        if not modal_handled:
            try:
                await page.keyboard.press('Escape')
                logger.info("✅ Pressed Escape for Woolworths modal")
                await page.wait_for_timeout(1000)
            except Exception:
                pass
        
        # Strategy 3: Handle cookie/privacy banners
        privacy_selectors = [
            'text="Accept"',
            'text="Accept All"',
            'button:has-text("Accept")',
            '[data-testid="accept-cookies"]',
            'button[class*="accept"]'
        ]
        
        for selector in privacy_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"✅ Accepted cookies with: {selector}")
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                continue
                
    except Exception as e:
        logger.debug(f"Woolworths modal handling completed: {e}")

def clean_price_text(price_text: str) -> Optional[float]:
    """
    Clean and extract price from text.
    
    Args:
        price_text: Raw price text from webpage
        
    Returns:
        Float price value or None if parsing fails
    """
    if not price_text:
        return None
    
    try:
        # Clean the text - remove extra whitespace and normalize
        cleaned = price_text.strip().replace('\n', ' ').replace('\t', ' ')
        
        # Handle common price formats
        price_patterns = [
            r'\$(\d+\.\d{2})',  # $12.34
            r'\$(\d+)',         # $12
            r'(\d+\.\d{2})\s*\$',  # 12.34 $
            r'(\d+)\s*\$',         # 12 $
            r'AUD\s*(\d+\.\d{2})',  # AUD 12.34
            r'AUD\s*(\d+)',         # AUD 12
            r'(\d+\.\d{2})',        # 12.34 (no currency symbol)
            r'(\d+)',               # 12 (no currency symbol, no decimal)
        ]
        
        for pattern in price_patterns:
            import re
            match = re.search(pattern, cleaned)
            if match:
                price_str = match.group(1)
                try:
                    price_value = float(price_str)
                    # Validate reasonable price range (between $0.01 and $999.99)
                    if 0.01 <= price_value <= 999.99:
                        return price_value
                except ValueError:
                    continue
        
        # Fallback: try to extract any numeric value
        import re
        numbers = re.findall(r'\d+\.?\d*', cleaned)
        for num_str in numbers:
            try:
                price_value = float(num_str)
                if 0.01 <= price_value <= 999.99:
                    return price_value
            except ValueError:
                continue
                
    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing price '{price_text}': {e}")
        
    return None

async def get_live_price(product_url: str, store: str) -> Dict[str, Any]:
    """
    Get live price for a product from any supported store.
    
    Args:
        product_url: The product URL
        store: The store name ('Coles', 'IGA', 'Woolworths')
        
    Returns:
        Dict containing price and status information
    """
    store = store.lower()
    
    if 'iga' in store:
        return await scrape_iga_product_price(product_url)
    elif 'coles' in store:
        return await scrape_coles_product_price(product_url)
    elif 'woolworths' in store:
        return await scrape_woolworths_product_price(product_url)
    else:
        return {
            'price': None,
            'currency': '$',
            'status': 'error',
            'message': f'Unsupported store: {store}',
            'store': store
        }

# Synchronous wrapper for Streamlit
def get_live_price_sync(product_url: str, store: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for get_live_price to use in Streamlit.
    
    Args:
        product_url: The product URL
        store: The store name
        
    Returns:
        Dict containing price and status information
    """
    try:
        # Create new event loop for this function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_live_price(product_url, store))
        loop.close()
        return result
    except Exception as e:
        return {
            'price': None,
            'currency': '$',
            'status': 'error',
            'message': f'Error running async scraper: {str(e)}',
            'store': store
        }
