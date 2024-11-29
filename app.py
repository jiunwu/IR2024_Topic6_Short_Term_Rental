from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import base64 
import sqlite3 

app = Flask(__name__)

def create_database():
    conn = sqlite3.connect('rentals.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rentals (id INTEGER PRIMARY KEY, rental TEXT)''')
    conn.commit()
    conn.close()

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("search", "")
    listings = scrape_airbnb(search_query)
    return render_template("index.html", listings=listings)

@app.route("/2", methods=["GET"])
def index_selenium():
    search_query = request.args.get("search", "")
    listings = scrape_airbnb_selenium(search_query)
    return render_template("index.html", listings=listings)


def scrape_airbnb(search_query=None, price=None, location=None):
    url = "https://www.holidaylettings.co.uk/villas-with-pools/hom_sleeps_max.2/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("Failed", response.status_code)
        return [] 

    soup = BeautifulSoup(response.content, "html.parser")

    listings = []
    seen = set()

    # search elements in the html
    elements = soup.find_all("a", attrs={"data-param": True})
    for element in elements:
        # Decode
        data_param = element.get("data-param", "")
        decoded_url = base64.b64decode(data_param).decode("utf-8") if data_param else "No URL"

        # Text in the element
        title = element.get_text(strip=True) if element else "No title"

        if title in seen:
            continue
        seen.add(title)

        # Filter (TODO: implement)
        matches_query = (search_query is None or search_query.lower() in title.lower())
        matches_price = price is None  
        matches_location = location is None 

        if matches_query and matches_price and matches_location:
            listings.append({
                "title": title,
                "url": decoded_url,
            })

    # Sort listings
    if search_query:
        listings.sort(key=lambda x: (search_query.lower() not in x['title'].lower(), x['title']))

    return listings

def scrape_airbnb_selenium(search_query=None, price=None, location=None):
   
    # Set up Selenium WebDriver (requires Chrome and ChromeDriver installed)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://www.airbnb.co.uk/")

    # time to load
    time.sleep(5)

    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source, "html.parser")

    listings = []
    seen = set()

    #  inside divs with class 't1jojoys' (adjust if necessary)
    elements = soup.find_all("div", class_="t1jojoys")
    for element in elements:
        title = element.get_text(strip=True) if element else "No title"
        
        if title in seen:
            continue
        seen.add(title)

        # filters TODO: latter implement
        price_tag = element.find_next("span", class_="price")
        price_text = price_tag.get_text(strip=True) if price_tag else "No price"
        
        location_tag = element.find_next("div", class_="location-class") 
        location_text = location_tag.get_text(strip=True) if location_tag else "No location"

        matches_query = (search_query is None or search_query.lower() in title.lower())
        matches_price = (price is None or price in price_text)
        matches_location = (location is None or location.lower() in location_text.lower())

        if matches_query and matches_price and matches_location:
            listings.append({
                "title": title,
                "price": price_text,
                "location": location_text,
            })

    return listings

if __name__ == "__main__":
    app.run(debug=True)
