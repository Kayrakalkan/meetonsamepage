import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser
from models import FlightResult, SearchParameters


class SkyscannerScraper:
    """Scraper for Skyscanner flight search"""
    
    BASE_URL = "https://www.skyscanner.com/transport/flights"
    
    def __init__(self, headless: bool = True, manual_captcha: bool = False):
        self.headless = headless
        self.manual_captcha = manual_captcha  # If True, wait for user to solve CAPTCHA
        self.browser: Optional[Browser] = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080'
            ],
            slow_mo=50  # Add slight delay to actions (more human-like)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
    
    def _format_date_for_url(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to YYMMDD format for Skyscanner URL"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%y%m%d")
    
    def _build_url(self, origin: str, destination: str, depart_date: str, return_date: str) -> str:
        """Build Skyscanner search URL"""
        depart_formatted = self._format_date_for_url(depart_date)
        return_formatted = self._format_date_for_url(return_date)
        
        # Format: /origin/destination/departure_date/return_date/
        url = f"{self.BASE_URL}/{origin.lower()}/{destination.lower()}/{depart_formatted}/{return_formatted}/"
        return url
    
    def _generate_date_combinations(self, date_from: str, date_to: str, duration_days: int) -> List[tuple]:
        """Generate all possible departure/return date combinations"""
        combinations = []
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        
        current = start
        while current + timedelta(days=duration_days) <= end:
            departure = current.strftime("%Y-%m-%d")
            return_date = (current + timedelta(days=duration_days)).strftime("%Y-%m-%d")
            combinations.append((departure, return_date))
            current += timedelta(days=1)
        
        return combinations
    
    async def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent popup if present"""
        try:
            # Wait a bit for popup to appear
            await asyncio.sleep(2)
            
            # Try multiple possible accept buttons
            accept_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("Accept All")',
                'button:has-text("I agree")',
                'button:has-text("OK")',
                'button[id*="accept"]',
                'button[class*="accept"]',
                '[data-testid="accept-button"]'
            ]
            
            for selector in accept_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click()
                        print("    ✓ Cookie consent accepted")
                        await asyncio.sleep(1)
                        return
                except:
                    continue
        except:
            pass  # No cookie popup or already accepted

    async def _wait_for_manual_captcha(self, page: Page, timeout: int = 60):
        """Wait for user to manually solve CAPTCHA"""
        captcha_selectors = [
            '#px-captcha',
            '[id*="px-captcha"]',
            '[class*="captcha"]',
            '[class*="challenge"]',
            ':has-text("Press & Hold")',
            ':has-text("press and hold")',
        ]
        
        # Check if CAPTCHA is present
        captcha_found = False
        for selector in captcha_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    captcha_found = True
                    break
            except:
                continue
        
        if captcha_found:
            print("\n    ⚠️  CAPTCHA DETECTED!")
            print("    👆 Please solve the CAPTCHA manually in the browser window.")
            print(f"    ⏳ Waiting up to {timeout} seconds for you to solve it...\n")
            
            # Wait for CAPTCHA to disappear (user solved it)
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                # Check if any CAPTCHA elements are still visible
                still_visible = False
                for selector in captcha_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible(timeout=500):
                            still_visible = True
                            break
                    except:
                        continue
                
                if not still_visible:
                    print("    ✅ CAPTCHA solved! Continuing...")
                    await asyncio.sleep(2)  # Wait for page to load after CAPTCHA
                    return True
                
                await asyncio.sleep(1)  # Check every second
            
            print("    ⚠️ CAPTCHA timeout - proceeding anyway...")
            return False
        
        return True  # No CAPTCHA found

    async def _human_like_mouse_move(self, page: Page, target_x: float, target_y: float):
        """Move mouse to target in a human-like curved path"""
        # Get current mouse position (start from a random edge)
        start_x = random.randint(100, 500)
        start_y = random.randint(100, 500)
        
        # Move in small steps with slight randomness
        steps = random.randint(20, 35)
        for i in range(steps):
            progress = (i + 1) / steps
            # Add some curve/randomness to the path
            noise_x = random.uniform(-3, 3)
            noise_y = random.uniform(-3, 3)
            
            # Ease-out curve for more natural movement
            eased_progress = 1 - (1 - progress) ** 2
            
            current_x = start_x + (target_x - start_x) * eased_progress + noise_x
            current_y = start_y + (target_y - start_y) * eased_progress + noise_y
            
            await page.mouse.move(current_x, current_y)
            await asyncio.sleep(random.uniform(0.01, 0.03))

    async def _handle_bot_verification(self, page: Page):
        """Handle Skyscanner's press-and-hold bot verification"""
        try:
            # Look for the verification button/element
            verification_selectors = [
                '#px-captcha',
                '[id*="px-captcha"]',
                '[class*="px-captcha"]',
                'div[id="px-captcha"]',
                'button:has-text("Press & Hold")',
                'button:has-text("press and hold")',
                ':has-text("Hold to confirm")',
                '[class*="challenge"]',
                '[class*="captcha"]',
                '[class*="verification"]',
                '[id*="challenge"]',
                '[class*="human"]',
            ]
            
            for selector in verification_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=3000):
                        print("    🤖 Bot verification detected! Attempting human-like solve...")
                        
                        # Get the bounding box of the element
                        box = await element.bounding_box()
                        if box:
                            # Calculate center of the button with slight randomness
                            x = box['x'] + box['width'] / 2 + random.uniform(-5, 5)
                            y = box['y'] + box['height'] / 2 + random.uniform(-5, 5)
                            
                            # Human-like mouse movement to the button
                            print("    🖱️ Moving mouse naturally...")
                            await self._human_like_mouse_move(page, x, y)
                            
                            # Small pause before clicking (human hesitation)
                            await asyncio.sleep(random.uniform(0.3, 0.7))
                            
                            # Press and hold with random duration (humans aren't precise)
                            hold_time = random.uniform(4.0, 6.0)
                            print(f"    ⏳ Pressing and holding for {hold_time:.1f}s...")
                            
                            await page.mouse.down()
                            
                            # During hold, add tiny micro-movements (hand shake)
                            hold_start = asyncio.get_event_loop().time()
                            while asyncio.get_event_loop().time() - hold_start < hold_time:
                                # Tiny movements to simulate hand tremor
                                micro_x = x + random.uniform(-1, 1)
                                micro_y = y + random.uniform(-1, 1)
                                await page.mouse.move(micro_x, micro_y)
                                await asyncio.sleep(0.1)
                            
                            await page.mouse.up()
                            
                            print("    ✓ Released button, waiting for verification...")
                            await asyncio.sleep(3)
                            
                            # Check if we passed
                            try:
                                if not await element.is_visible(timeout=2000):
                                    print("    ✅ Bot verification passed!")
                                    return True
                            except:
                                print("    ✅ Bot verification likely passed!")
                                return True
                            
                            print("    ⚠️ Verification may still be present, trying again...")
                            # Try one more time with longer hold
                            await self._human_like_mouse_move(page, x, y)
                            await asyncio.sleep(0.5)
                            await page.mouse.down()
                            
                            hold_start = asyncio.get_event_loop().time()
                            while asyncio.get_event_loop().time() - hold_start < 8:
                                micro_x = x + random.uniform(-1, 1)
                                micro_y = y + random.uniform(-1, 1)
                                await page.mouse.move(micro_x, micro_y)
                                await asyncio.sleep(0.1)
                            
                            await page.mouse.up()
                            await asyncio.sleep(3)
                        
                        return True
                except Exception as e:
                    continue
            
            # Check for PerimeterX iframe challenge
            try:
                # Sometimes it's in an iframe
                frames = page.frames
                for frame in frames:
                    try:
                        px_element = frame.locator('#px-captcha, [id*="captcha"]').first
                        if await px_element.is_visible(timeout=1000):
                            print("    🤖 PerimeterX iframe challenge detected!")
                            box = await px_element.bounding_box()
                            if box:
                                x = box['x'] + box['width'] / 2
                                y = box['y'] + box['height'] / 2
                                await self._human_like_mouse_move(page, x, y)
                                await asyncio.sleep(0.5)
                                await page.mouse.down()
                                await asyncio.sleep(6)
                                await page.mouse.up()
                                await asyncio.sleep(3)
                                print("    ✅ PerimeterX challenge attempted!")
                                return True
                    except:
                        continue
            except:
                pass
                
            return False
            
        except Exception as e:
            print(f"    ⚠️ Error handling bot verification: {e}")
            return False
    
    async def _wait_for_results(self, page: Page, timeout: int = 45000):
        """Wait for flight results to load"""
        try:
            # Try multiple possible selectors
            selectors = [
                '[class*="FlightsResults"]',
                '[class*="ResultsSummary"]',
                '[data-testid="itinerary"]',
                'div[class*="Itinerary"]',
                '[class*="BpkTicket"]',
                'a[href*="/transport/flights/"]'
            ]
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    print(f"    ✓ Found results with selector: {selector[:30]}...")
                    break
                except:
                    continue
            
            # Additional wait for dynamic content
            await asyncio.sleep(5)
        except:
            print("⚠️ Results may not have fully loaded")
    
    async def _extract_flights(self, page: Page, origin: str, destination: str, 
                                depart_date: str, return_date: str) -> List[FlightResult]:
        """Extract flight information from the page"""
        flights = []
        
        try:
            # Wait a bit for all content to load
            await asyncio.sleep(3)
            
            import re
            
            # Get all text from page
            body_text = await page.locator('body').inner_text()
            
            # Look for price patterns in different currencies
            # Patterns: €239, £150, $200, 239 €, HUF 25000, Ft 25000, CHF 150
            price_patterns = [
                r'[€£$]\s*(\d+(?:[.,]\d+)?)',           # €239, £150, $200
                r'(\d+(?:[.,]\d+)?)\s*[€£$]',           # 239 €
                r'(?:EUR|GBP|USD|CHF)\s*(\d+(?:[.,]\d+)?)',  # EUR 239
                r'(\d+(?:[.,]\d+)?)\s*(?:EUR|GBP|USD|CHF)',  # 239 EUR
                r'(?:HUF|Ft)\s*(\d+(?:\s?\d+)*)',       # HUF 25 000 or Ft25000
                r'(\d+(?:\s?\d+)*)\s*(?:HUF|Ft)',       # 25000 Ft
            ]
            
            found_prices = set()
            
            for pattern in price_patterns:
                matches = re.findall(pattern, body_text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Clean the number
                        price_str = match.replace(' ', '').replace(',', '.')
                        price_val = float(price_str)
                        
                        # Convert HUF to EUR approximately (1 EUR ≈ 380 HUF)
                        if 'HUF' in pattern or 'Ft' in pattern:
                            if price_val > 5000:  # Likely HUF
                                price_val = price_val / 380
                        
                        # Reasonable flight price range (20 - 2000 EUR)
                        if 20 < price_val < 2000:
                            found_prices.add(round(price_val, 2))
                    except:
                        continue
            
            # Also try to find standalone numbers that look like prices
            # Look for numbers in the results area
            result_area = page.locator('[class*="Result"], [class*="Flight"], [class*="Itinerary"]')
            if await result_area.count() > 0:
                for i in range(min(await result_area.count(), 20)):
                    try:
                        card = result_area.nth(i)
                        card_text = await card.inner_text()
                        # Find 3-4 digit numbers that could be prices
                        numbers = re.findall(r'\b(\d{2,4})\b', card_text)
                        for num in numbers:
                            val = float(num)
                            if 25 < val < 1500:
                                found_prices.add(val)
                    except:
                        continue
            
            # Sort and get unique prices
            sorted_prices = sorted(found_prices)
            if sorted_prices:
                print(f"    Found {len(sorted_prices)} valid prices: {sorted_prices[:5]}...")
            else:
                # Debug: print some page text to understand structure
                sample_text = body_text[:500].replace('\n', ' ')
                print(f"    No prices found. Sample text: {sample_text[:100]}...")
            
            # Create flight results from found prices
            for price in sorted_prices[:10]:  # Top 10 cheapest
                flights.append(FlightResult(
                    departure_airport=origin.upper(),
                    arrival_airport=destination.upper(),
                    departure_date=depart_date,
                    return_date=return_date,
                    price=price,
                    currency="EUR",
                    link=page.url
                ))
                    
        except Exception as e:
            print(f"⚠️ Error extracting flights: {e}")
        
        return flights
    
    async def search_flights(self, origin: str, destination: str, 
                             date_from: str, date_to: str, 
                             duration_days: int, top_n: int = 3) -> List[FlightResult]:
        """
        Search for flights and return top N cheapest options
        
        Args:
            origin: Departure airport code (e.g., "BUD")
            destination: Arrival airport code (e.g., "ZRH")
            date_from: Start of date range (YYYY-MM-DD)
            date_to: End of date range (YYYY-MM-DD)
            duration_days: Trip duration in days
            top_n: Number of top cheapest flights to return
        
        Returns:
            List of FlightResult objects
        """
        all_flights = []
        date_combinations = self._generate_date_combinations(date_from, date_to, duration_days)
        
        print(f"🔍 Searching flights: {origin} → {destination}")
        print(f"📅 Checking {len(date_combinations)} date combinations...")
        
        # Create a new context with realistic browser settings
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-GB',
            timezone_id='Europe/London',
            geolocation={'latitude': 51.5074, 'longitude': -0.1278},
            permissions=['geolocation'],
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1
        )
        
        page = await context.new_page()
        
        # Add comprehensive stealth scripts to avoid detection
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    name: 'Chrome PDF Plugin',
                    description: 'Portable Document Format',
                    filename: 'internal-pdf-viewer'
                }))
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {get: () => ['en-GB', 'en-US', 'en']});
            
            // Mock chrome runtime
            window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Remove automation indicators
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Mock WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };
        """)
        
        try:
            for i, (depart_date, return_date) in enumerate(date_combinations):
                url = self._build_url(origin, destination, depart_date, return_date)
                print(f"  [{i+1}/{len(date_combinations)}] {depart_date} → {return_date}")
                
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Handle cookie consent on first visit
                    if i == 0:
                        await self._handle_cookie_consent(page)
                    
                    # Check for and handle bot verification
                    await asyncio.sleep(2)  # Wait for any verification to appear
                    
                    if self.manual_captcha:
                        # Manual mode: wait for user to solve CAPTCHA
                        await self._wait_for_manual_captcha(page)
                    else:
                        # Auto mode: try to solve automatically
                        await self._handle_bot_verification(page)
                    
                    # Wait for results to load
                    await self._wait_for_results(page)
                    
                    # Check again for bot verification (sometimes appears after page load)
                    page_content = await page.content()
                    if 'press' in page_content.lower() and 'hold' in page_content.lower():
                        print("    🔄 Bot verification appeared after load, handling...")
                        if self.manual_captcha:
                            await self._wait_for_manual_captcha(page)
                        else:
                            await self._handle_bot_verification(page)
                        await self._wait_for_results(page)
                    
                    # Debug: save screenshot if no results found
                    flights = await self._extract_flights(page, origin, destination, depart_date, return_date)
                    
                    if not flights:
                        screenshot_path = f"debug_{origin}_{destination}_{depart_date}.png"
                        await page.screenshot(path=screenshot_path)
                        print(f"    📸 Screenshot saved: {screenshot_path}")
                    
                    all_flights.extend(flights)
                    
                    # Random delay between requests to avoid detection
                    await asyncio.sleep(random.uniform(4, 8))
                    
                except Exception as e:
                    print(f"    ⚠️ Error on {depart_date}: {e}")
                    continue
        finally:
            await context.close()
        
        # Sort by price and return top N
        all_flights.sort(key=lambda x: x.price)
        unique_flights = self._remove_duplicates(all_flights)
        
        print(f"✅ Found {len(unique_flights)} unique flights from {origin}")
        return unique_flights[:top_n]
    
    def _remove_duplicates(self, flights: List[FlightResult]) -> List[FlightResult]:
        """Remove duplicate flights based on key attributes"""
        seen = set()
        unique = []
        
        for flight in flights:
            key = (flight.departure_date, flight.return_date, flight.price, flight.airline)
            if key not in seen:
                seen.add(key)
                unique.append(flight)
        
        return unique


async def search_multiple_origins(params: SearchParameters, headless: bool = True, manual_captcha: bool = False) -> dict:
    """
    Search flights from multiple departure airports to one destination
    
    Args:
        params: SearchParameters object with all search criteria
        headless: Run browser in headless mode
        manual_captcha: If True, wait for user to manually solve CAPTCHAs
    
    Returns:
        Dictionary with results for each departure airport
    """
    results = {}
    
    async with SkyscannerScraper(headless=headless, manual_captcha=manual_captcha) as scraper:
        for origin in params.departure_airports:
            flights = await scraper.search_flights(
                origin=origin,
                destination=params.arrival_airport,
                date_from=params.date_from,
                date_to=params.date_to,
                duration_days=params.trip_duration_days,
                top_n=3
            )
            results[origin] = [f.model_dump() for f in flights]
    
    return results


# For testing
if __name__ == "__main__":
    async def test():
        params = SearchParameters(
            departure_airports=["BUD", "CGN"],
            arrival_airport="ZRH",
            date_from="2025-12-15",
            date_to="2025-12-30",
            trip_duration_days=3
        )
        
        results = await search_multiple_origins(params, headless=False)
        print(json.dumps(results, indent=2))
    
    asyncio.run(test())
