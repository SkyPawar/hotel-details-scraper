import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import re
from urllib.parse import quote, urlencode
import random
import sys
from datetime import datetime

# Try importing Selenium (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class AdvancedHotelScraper:
    def __init__(self, delay_min=2, delay_max=5, use_selenium=True):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.load_proxies()

        # Set random user-agent
        self.random_user_agent = self.get_random_user_agent()

        # Headers to mimic real browser
        self.headers = {
            'User-Agent': self.random_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Initialize Selenium if requested
        if self.use_selenium:
            self.driver = self.setup_selenium()
            
    def get_random_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/102.0",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 Chrome/89.0.4389.82 Safari/537.36"
        ]
        return random.choice(user_agents)
            
    def load_proxies(self, proxy_source_url="https://free-proxy-list.net/"):
        """Load free proxies from public proxy list"""
        try:
            print("Loading proxy list...")
            res = requests.get(proxy_source_url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')

            proxy_list = []
            for row in soup.select("table#proxylisttable tbody tr"):
                cols = row.find_all("td")
                if cols[6].text == "yes":  # HTTPS only
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    proxy_list.append(f"http://{ip}:{port}")
            
            self.proxies = proxy_list
            print(f"Loaded {len(proxy_list)} proxies.")
        except Exception as e:
            print(f"Failed to load proxies: {e}")
            self.proxies = []

    def get_random_proxy(self):
        """Get a random proxy from the list"""
        if not hasattr(self, 'proxies') or not self.proxies:
            return None
        return random.choice(self.proxies)

        
    def setup_selenium(self):
        """Setup Selenium WebDriver with random user-agent and optional proxy"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # Set the same random user-agent as requests
            chrome_options.add_argument(f'--user-agent={self.random_user_agent}')

            # Optional: use proxy for selenium
            proxy = self.get_random_proxy()
            if proxy:
                chrome_options.add_argument(f'--proxy-server={proxy}')
                print(f"Using proxy for Selenium: {proxy}")

            # Add Chrome flags for software rendering
            chrome_options.add_argument('--enable-unsafe-webgpu')
            chrome_options.add_argument('--enable-unsafe-swiftshader')
            chrome_options.add_argument('--use-gl=swiftshader')
            chrome_options.add_argument('--ignore-gpu-blocklist')

            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Failed to setup Selenium: {e}")
            return None
    
    def random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
    
    def get_page_requests(self, url, retries=5):
        """Get page using requests with optional proxy"""
        for attempt in range(retries):
            proxy = self.get_random_proxy()
            proxies = {"http": proxy, "https": proxy} if proxy else None

            try:
                response = self.session.get(url, timeout=15, proxies=proxies)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"[Retry {attempt+1}] Failed with proxy {proxy}: {e}")
                self.random_delay()
        return None
    
    def get_page_selenium(self, url, wait_time=10):
        """Get page using Selenium"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return self.driver.page_source
        except Exception as e:
            print(f"Selenium failed for {url}: {e}")
            return None
    
    def extract_phone_number(self, text):
        """Extract phone number from text using regex"""
        if not text:
            return None
        
        # Multiple phone number patterns
        patterns = [
            r'\+?[\d\s\-\(\)]{10,20}',  # International format
            r'\(\d{3}\)\s?\d{3}-\d{4}',  # US format
            r'\d{3}-\d{3}-\d{4}',       # US format
            r'\d{10,}',                 # Simple digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()
        return None
    
    def get_hotel_details(self, hotel_url, source, name=None, city=None, country=None):
        """Get detailed hotel information from hotel page"""
        if not hotel_url:
            return {}
        
        try:
            html = self.get_page_selenium(hotel_url) if self.use_selenium else self.get_page_requests(hotel_url)
            if not html:
                return {}
            
            soup = BeautifulSoup(html, 'html.parser')
            details = {}
            
            # Extract phone number
            phone_selectors = [
                '[data-testid="phone-number"]',
                '.phone-number',
                '.hotel-phone',
                '.contact-phone'
            ]
            
            for selector in phone_selectors:
                phone_elem = soup.select_one(selector)
                if phone_elem:
                    details['phone'] = self.extract_phone_number(phone_elem.get_text())
                    break
            
            # Extract official website
            website_selectors = [
                '[data-testid="website"]',
                '.hotel-website',
                '.official-website',
                'a[href*="hotel"]'
            ]
            
            for selector in website_selectors:
                website_elem = soup.select_one(selector)
                if website_elem and 'href' in website_elem.attrs:
                    href = website_elem['href']
                    if href and not href.startswith(('http://booking.com', 'http://hotels.com', 'http://expedia.com')):
                        details['website'] = href
                        break
            
            # Look for contact info in text
            if not details.get('phone') and name and city and country:
                print(f"🔁 Fallback: Getting contact from Google for {name}")
                phone = self.get_contact_from_google_knowledge_panel(name, city, country)
                if phone:
                    details['phone'] = phone
            
            return details
            
        except Exception as e:
            print(f"Error getting hotel details: {e}")
            return {}
    
    def scrape_booking_com(self, city, country, min_rating=None):
        """Scrape Booking.com for hotels"""
        print(f"\nScraping Booking.com for hotels in {city}, {country}")
        hotels = []
        
        # Booking.com search URL
        checkin = datetime.now().strftime('%Y-%m-%d')
        checkout = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'ss': f"{city}, {country}",
            'checkin': checkin,
            'checkout': checkout,
            'group_adults': '2',
            'group_children': '0',
            'no_rooms': '1'
        }
        
        url = f"https://www.booking.com/searchresults.html?{urlencode(params)}"
        
        # Try both methods
        html = self.get_page_selenium(url) if self.use_selenium else self.get_page_requests(url)
        
        if not html:
            return hotels
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Multiple selectors for different layouts
        selectors = [
            'div[data-testid="property-card"]',
            '.sr_item',
            '[data-testid="property-card"]',
            '.sr_item_content'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                break
        
        for element in elements[:20]:  # Limit to first 20 results
            try:
                # Extract hotel name
                name_selectors = [
                    '[data-testid="title"]',
                    '.sr-hotel__name',
                    'h3 a',
                    '.fcab3ed991.a23c043802'
                ]
                
                name = None
                for name_sel in name_selectors:
                    name_elem = element.select_one(name_sel)
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        break
                
                if not name:
                    continue
                
                # Extract rating
                rating_selectors = [
                    '[data-testid="review-score"] div',
                    '.bui-review-score__badge',
                    '.review-score-badge'
                ]
                
                rating = None
                for rating_sel in rating_selectors:
                    rating_elem = element.select_one(rating_sel)
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                            break
                
                # Extract price
                price_selectors = [
                    '[data-testid="price-and-discounted-price"]',
                    '.bui-price-display__value',
                    '.prco-valign-middle-helper'
                ]
                
                price = None
                price_amount = None
                for price_sel in price_selectors:
                    price_elem = element.select_one(price_sel)
                    if price_elem:
                        price = price_elem.get_text(strip=True)
                        price_amount = self.extract_price_amount(price)
                        break
                
                # Extract URL
                url_elem = element.select_one('a[href]')
                hotel_url = url_elem['href'] if url_elem else ''
                if hotel_url and not hotel_url.startswith('http'):
                    hotel_url = 'https://www.booking.com' + hotel_url
                
                # Filter by rating if specified
                if min_rating and rating and rating < min_rating:
                    continue
                
                # Get additional details
                details = self.get_hotel_details(hotel_url, 'Booking.com', name=name, city=city, country=country)
                
                hotel = {
                    'name': name,
                    'rating': rating,
                    'price': price,
                    'price_amount': price_amount,
                    'url': hotel_url,
                    'source': 'Booking.com',
                    'city': city,
                    'country': country,
                    'phone': details.get('phone'),
                    'email': details.get('email'),
                    'website': details.get('website')
                }
                
                hotels.append(hotel)
                
            except Exception as e:
                print(f"Error parsing Booking.com result: {e}")
                continue
        
        self.random_delay()
        return hotels
    
    def scrape_google_maps_hotels(self, city, country, min_rating=None):
        query = f"hotels in {city} {country}"
        url = f"https://www.google.com/maps/search/{quote(query)}"
        print(f"Navigating to {url}")
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Results for"]'))
        )
        time.sleep(2)

        hotels = []
        listings = self.driver.find_elements(By.XPATH, '//div[contains(@class,"section-result")]')[:10]

        for listing in listings:
            try:
                name = listing.find_element(By.TAG_NAME, 'h3').text
                listing.click()
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"W4Efsd")]'))
                )
                time.sleep(1)

                # Extract contact from info panel
                contact = None
                # info_elements = self.driver.find_elements(By.CLASS_NAME, 'W4Efsd')
                phone_elements = self.driver.find_elements(By.CSS_SELECTOR, '.Io6YTe.fontBodyMedium.kR99db.fdkmkc')
                for elem in phone_elements:
                    contact = self.extract_phone_number(elem.text)
                    if contact:
                        print("Found phone:", contact)
                        break

                hotels.append({
                    'name': name,
                    'city': city,
                    'country': country,
                    'source': 'Google Maps',
                    'contact': contact
                })
                self.driver.back()
                time.sleep(1)

            except Exception as e:
                print(f"Error scraping hotel: {e}")
                continue

        self.random_delay()
        return hotels

    def get_contact_from_google_knowledge_panel(self, hotel_name, city, country):
        print(f"DEBUG: Called get_contact_from_google_knowledge_panel for {hotel_name}, {city}, {country}")
        # self.open_hotel_in_google_maps(hotel_name)
        query = f"{hotel_name}"
        url = f"https://www.google.com/maps/search/{quote(query)}"
        print(f"DEBUG: Navigating to {url}")
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(2, 4))

            html = self.driver.execute_script("return document.documentElement.innerText;")
            phone_elements = self.driver.find_elements(By.CSS_SELECTOR, '.Io6YTe.fontBodyMedium.kR99db.fdkmkc')
            for elem in phone_elements:
                print("DEBUG: Phone element text:", elem.text)
                phone = self.extract_phone_number(elem.text)
                if phone:
                    print("Found phone:", phone)
                    break

            # Look for phone patterns
            for pattern in [r"\+?1?\s?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}", r"\d{3}[\s\-]\d{3}[\s\-]\d{4}"]:
                m = re.search(pattern, html)
                if m:
                    return m.group(0)

            return None

        except Exception as e:
            print("Error in Google search:", e)
            return None

    
    
    def scrape_all_sources(self, city, country, min_rating=None):
        """Scrape all available sources"""
        all_hotels = []
        
        # List of scraping methods
        methods = [
            self.scrape_booking_com,
            self.scrape_google_maps_hotels
            # You can add more sources here
        ]
        
        for method in methods:
            try:
                hotels = method(city, country, min_rating)
                if hotels:
                    all_hotels.extend(hotels)
                    print(f"Found {len(hotels)} hotels from {method.__name__}")
            except Exception as e:
                print(f"Error with {method.__name__}: {e}")
                continue
        
        self.random_delay()
        return all_hotels
    
    def remove_duplicates(self, hotels):
        """Remove duplicate hotels based on name similarity"""
        unique_hotels = []
        seen_names = set()
        
        for hotel in hotels:
            name_lower = hotel['name'].lower().strip()
            # Simple duplicate detection
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_hotels.append(hotel)
        
        return unique_hotels
    
    def save_to_csv(self, hotels, filename):
        """Save hotels to CSV with all fields"""
        if not hotels:
            print("No hotels to save")
            return
        
        # Define the field order
        fieldnames = [
            'name', 'city', 'country', 'rating', 'price', 'price_amount',
            'phone', 'email', 'website', 'url', 'source'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for hotel in hotels:
                # Ensure all fields are present
                row = {field: hotel.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        print(f"Data saved to {filename}")
    
    def save_to_json(self, hotels, filename):
        """Save hotels to JSON"""
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(hotels, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
            
            
    def get_official_website_from_google(self, name, city, country):
        query = quote(f"{name} {city} {country} official site")
        url = f"https://www.google.com/search?q={query}"
        html = self.get_page_selenium(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Try headline result
        for a in soup.select("a[jsname='UWckNb']"):
            href = a.get("href", "")
            if href.startswith("http") and "google.com" not in href:
                return href

        # Fallback
        for a in soup.select("div.yuRUbf a[href]"):
            href = a.get("href", "")
            if href.startswith("http") and "google.com" not in href:
                return href
            
        self.random_delay()
        return None
    
    
    def get_phone_from_official_site(self, website_url):
        html = self.get_page_selenium(website_url)
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')

        # Look for contact link
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True).lower()
            if 'contact' in text:
                href = a['href']
                if href.startswith('http'):
                    contact_url = href
                elif href.startswith('/'):
                    contact_url = website_url.rstrip('/') + href
                else:
                    contact_url = website_url.rstrip('/') + '/' + href

                # Open contact page
                contact_html = self.get_page_selenium(contact_url)
                if not contact_html:
                    continue
                return self.extract_phone_number(contact_html)
        
        # Fallback: try whole page
        self.random_delay()
        return self.extract_phone_number(soup.get_text())


def main():
    print("=== Enhanced Hotel & Motel Scraper ===")
    print("This scraper extracts: Name, Rating, Price, Contact Info, Website, URL")
    print("Sources: Booking.com, Hotels.com, Expedia, Google Maps")
    
    if not SELENIUM_AVAILABLE:
        print("Note: Selenium not available. Install with: pip install selenium")
        print("For better contact info extraction, also install ChromeDriver")
    
    # Get user input
    city = input("Enter city name: ").strip()
    country = input("Enter country name: ").strip()
    
    # Rating filter
    rating_input = input("Enter minimum rating (optional): ").strip()
    min_rating = None
    if rating_input:
        try:
            min_rating = float(rating_input)
        except ValueError:
            print("Invalid rating, skipping filter")
    
    # Use Selenium option
    use_selenium = True
    if SELENIUM_AVAILABLE:
        selenium_choice = input("Use Selenium for better results? (y/n): ").strip().lower()
        use_selenium = selenium_choice == 'y'
    
    # Initialize scraper
    scraper = AdvancedHotelScraper(use_selenium=use_selenium)
    scraper.load_proxies()
    
    try:
        print(f"\nScraping hotels in {city}, {country}...")
        if min_rating:
            print(f"Minimum rating: {min_rating}")
        
        # Scrape all sources
        hotels = scraper.scrape_all_sources(city, country, min_rating)
        
        # Remove duplicates
        unique_hotels = scraper.remove_duplicates(hotels)
        
        print(f"\nFound {len(hotels)} total hotels ({len(unique_hotels)} unique)")
        
        # Display results
        if unique_hotels:
            print("\n=== RESULTS ===")
            for i, hotel in enumerate(unique_hotels, 1):
                print(f"\n{i}. {hotel['name']}")
                print(f"   Source: {hotel['source']}")
                if hotel.get('rating'):
                    print(f"   Rating: {hotel['rating']}")
                if hotel.get('price'):
                    print(f"   Price: {hotel['price']}")
                if hotel.get('phone'):
                    print(f"   Phone: {hotel['phone']}")
                if hotel.get('email'):
                    print(f"   Email: {hotel['email']}")
                if hotel.get('website'):
                    print(f"   Website: {hotel['website']}")
                if hotel.get('url'):
                    print(f"   URL: {hotel['url']}")
            
            # Save data
            save_format = input("\nSave data? (csv/json/both/no): ").strip().lower()
            
            if save_format in ['csv', 'both']:
                filename = f"hotels_{city}_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filename = filename.replace(' ', '_')
                scraper.save_to_csv(unique_hotels, filename)
            
            if save_format in ['json', 'both']:
                filename = f"hotels_{city}_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filename = filename.replace(' ', '_')
                scraper.save_to_json(unique_hotels, filename)
        
        else:
            print("No hotels found. Try different search terms or check your internet connection.")
    
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()