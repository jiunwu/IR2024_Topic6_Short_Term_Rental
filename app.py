from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import sqlite3

app = Flask(__name__)

def create_database():
    conn = sqlite3.connect('rentals.db')
    c = conn.cursor()
    create_table_query = """
        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY,
            rental_name TEXT NOT NULL,
            price REAL NOT NULL,
            location TEXT NOT NULL,
            guest_capacity INTEGER NOT NULL
        );
        """
    c.execute(create_table_query)
    conn.commit()
    conn.close()

# Unified route using Selenium
@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "")
    listings = scrape_airbnb_selenium(search_query)
    return render_template("index.html", listings=listings)

def scrape_airbnb_selenium(search_query=None, price=None, location=None):
    # Set up Selenium WebDriver with headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (useful for headless mode)
    chrome_options.add_argument("--no-sandbox")  # Necessary for some environments
    chrome_options.add_argument("--disable-dev-shm-usage")  # Avoid issues with /dev/shm in headless mode

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://www.airbnb.co.uk/")
    
    # Allow time for the page to load
    time.sleep(5)
    
    listings = []
    seen = set()
    
    try:
        # Locate and process elements containing listing information
        elements = driver.find_elements(By.CLASS_NAME, "t1jojoys")  # Adjust this selector as per the actual Airbnb page structure
        for element in elements:
            title = element.text.strip() if element else "No title"
            
            # Skip duplicate titles
            if title in seen:
                continue
            seen.add(title)

            # Retrieve price
            try:
                price_element = element.find_element(By.XPATH, ".//following-sibling::span[contains(@class, 'price')]")
                price_text = price_element.text.strip() if price_element else "No price"
            except Exception:
                price_text = "No price"

            # Retrieve location
            try:
                location_element = element.find_element(By.XPATH, ".//following-sibling::div[contains(@class, 'location-class')]")
                location_text = location_element.text.strip() if location_element else "No location"
            except Exception:
                location_text = "No location"
            
            # Apply filters (if any)
            matches_query = (search_query is None or search_query.lower() in title.lower())
            matches_price = (price is None or price in price_text)
            matches_location = (location is None or location.lower() in location_text.lower())
            
            if matches_query and matches_price and matches_location:
                listings.append({
                    "title": title,
                    "price": price_text,
                    "location": location_text,
                })
    finally:
        # Close the browser
        driver.quit()
    
    return listings

if __name__ == "__main__":
    app.run(debug=True)
