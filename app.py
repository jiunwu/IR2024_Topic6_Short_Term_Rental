from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    # Retrieve search parameters from the query string
    search_query = request.args.get("search", "")
    price = request.args.get("price", "")
    location = request.args.get("location", "")

    # Call the scrape_airbnb function and pass the parameters
    listings = scrape_airbnb(search_query, price, location)

    return render_template("index.html", listings=listings)

def scrape_airbnb(search_query=None, price=None, location=None):
    url = "https://www.airbnb.co.uk/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Send a GET request with headers to simulate a real browser request
    response = requests.get(url, headers=headers)

    # Parse the response content with BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    listings = []

    # Find all relevant information about each property listing
    for listing in soup.find_all("div", class_="listing-card"):  # Update with the correct class name
        # Updated title extraction based on the provided HTML structure
        title_tag = listing.find("div", class_="t1jojoys")
        title = title_tag.text.strip() if title_tag else "No title"

        price = listing.find("span", class_="price").text.strip() if listing.find("span", class_="price") else "No price"
        location = listing.find("div", class_="location-class").text.strip() if listing.find("div", class_="location-class") else "No location"

        # If no search query is provided, include all listings
        if not search_query:
            listings.append({
                "title": title,
                "price": price,
                "location": location,
            })
            continue

        # If a search query is provided, only include listings where the search term matches the title or location
        if search_query and (search_query.lower() in title.lower() or search_query.lower() in location.lower()):
            listings.append({
                "title": title,
                "price": price,
                "location": location,
            })

    return listings

@app.route('/hello/')
def news():
 headlines = scrape_news()
 return render_template("news.html", headlines=headlines)

def scrape_news():
 url = "https://news.ycombinator.com"
 response = requests.get(url)
 soup = BeautifulSoup(response.content, "html.parser")
 headlines = []
 for headline in soup.find_all("span", class_="titleline"):
 	headlines.append(headline.text)	
 return headlines