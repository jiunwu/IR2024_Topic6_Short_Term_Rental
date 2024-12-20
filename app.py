import sqlite3
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
import pyterrier as pt
import os

app = Flask(__name__)

# Initialize PyTerrier
if not pt.started():
    pt.init()

def get_listings():
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, location, url, image FROM listings")
    listings = cursor.fetchall()
    conn.close()
    return listings

@app.route('/', methods=['GET'])
def index():
    search_query = request.args.get('search', '')
    #fetch_source1(search_query)
    fetch_source2(search_query)
    fetch_source3(search_query)
    
    listings = get_listings()
    listings = [{'title': title, 'price': price, 'location': location, 'url': url, 'image': image} for title, price, location, url, image in listings]

    return render_template('index.html', listings=listings)

@app.route('/api/listings')
def api_listings():
    listings = get_listings()
    listings = [{'title': title, 'price': price, 'location': location, 'url': url, 'image': image} for title, price, location, url, image in listings]
    return jsonify(listings)

@app.route('/search', methods=['GET', 'POST'])
def search():
    search_query = request.form.get('search', '')
    
    # Load dataset from SQLite
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rowid, title, price, location, url, image
        FROM listings
        WHERE title NOT LIKE '%Careers%'
          AND title NOT LIKE '%Terms and Conditions%'
          AND price IS NOT NULL
          AND price != ''
          AND location IS NOT NULL
          AND location != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    # Prepare the dataset for PyTerrier
    docs = [{'docno': str(row[0]), 'text': f"{row[1]} {row[2]} {row[3]} {row[4]} {row[5]}"} for row in rows]
    index_path = './index'
    
    try:
        indexref = pt.IndexFactory.of(index_path + "/data.properties")
    except Exception as e:
        indexer = pt.IterDictIndexer(index_path)
        indexref = indexer.index(docs)
    
    print(f"Indexed documents: {docs}")  # Debug: Print the indexed documents

    # Initialize the PyTerrier pipeline
    pipeline = pt.BatchRetrieve(indexref, wmodel="BM25")

    # Perform the search
    results = pipeline.search(search_query)
    print(f"Search results: {results}")  # Debug: Print the search results

    # Fetch the results from the database
    result_ids = [int(docno) for docno in results['docno']]
    print(f"Result IDs: {result_ids}")  # Debug: Print the result IDs
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, location, url, image FROM listings WHERE rowid IN ({})".format(','.join('?' * len(result_ids))), result_ids)
    listings = cursor.fetchall()
    conn.close()

    print(f"Listings: {listings}")  # Debug: Print the listings

    return render_template('index.html', listings=listings)

def fetch_source1(search_query=None, price=None, location=None):
    url = 'https://www.holidaylettings.co.uk/villas-with-pools/hom_sleeps_max.2/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Failed', response.status_code)
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    listings = []
    seen = set()

    # Connect to SQLite3 database (or create it if it doesn't exist)
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            location TEXT,
            url TEXT,
            image TEXT
        )
    ''')

    elements = soup.find_all('a', attrs={'data-param': True})

    # Overwrite the location values
    locations = ["United Kingdom", "France", "Spain"]
    location_index = 0

    for element in elements:
        title = element.get_text(strip=True)
        url = element['href']
        if url in seen:
            continue
        seen.add(url)

        # Example of extracting other details (price, image, etc.)
        price = "N/A"  # Replace with actual extraction logic
        image = "N/A"  # Replace with actual extraction logic

        # Overwrite the location value
        location = locations[location_index % len(locations)]
        location_index += 1

        listing = {
            'title': title,
            'price': price,
            'location': location,
            'url': url,
            'image': image
        }
        listings.append(listing)

        # Insert listing into the database
        cursor.execute('''
            INSERT INTO listings (title, price, location, url, image)
            VALUES (?, ?, ?, ?, ?)
        ''', (listing['title'], listing['price'], listing['location'], listing['url'], listing['image']))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

def fetch_source2(search_query=None, price=None, location=None):
    url = 'https://www.cozycozy.com/gb/england-short-term-rentals'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Failed', response.status_code)
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    listings = []
    seen = set()

    # Connect to SQLite3 database (or create it if it doesn't exist)
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            location TEXT,
            url TEXT,
            image TEXT
        )
    ''')

    elements = soup.find_all('article', class_='ng-star-inserted')

    # Overwrite the location values
    locations = ["United Kingdom", "France", "Spain"]
    location_index = 0

    for element in elements:
        title_element = element.find('h3', class_='title')
        price_element = element.find('strong')
        image_element = element.find('img', class_='photo')

        if not title_element or not price_element:
            continue

        title = title_element.get_text(strip=True)
        price = price_element.get_text(strip=True)
        image = image_element['src'] if image_element else "N/A"
        url = f"https://www.fakeurl.com/{location_index}"  # Generate fake URL
        if url in seen:
            continue
        seen.add(url)

        # Overwrite the location value
        location = locations[location_index % len(locations)]
        location_index += 1

        listing = {
            'title': title,
            'price': price,
            'location': location,
            'url': url,
            'image': image
        }
        listings.append(listing)

        # Insert listing into the database
        cursor.execute('''
            INSERT INTO listings (title, price, location, url, image)
            VALUES (?, ?, ?, ?, ?)
        ''', (listing['title'], listing['price'], listing['location'], listing['url'], listing['image']))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

def fetch_source3(search_query=None, price=None, location=None):
    url = 'https://www.countryhousecompany.co.uk/lettings/properties-available/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Failed', response.status_code)
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    listings = []
    seen = set()

    # Connect to SQLite3 database (or create it if it doesn't exist)
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            location TEXT,
            url TEXT,
            image TEXT
        )
    ''')

    elements = soup.find_all('a', class_='flex flex-col min-h-full overflow-hidden bg-white rounded-lg shadow-lg hvr-float')

    # Overwrite the location values
    locations = ["United Kingdom", "UK", "Britain"]
    location_index = 0

    for element in elements:
        title_element = element.find('h4', class_='mb-4 font-sans text-xl font-semibold leading-tight text-blueGray-700')
        price_element = element.find('p', class_='mb-4 font-sans text-lg font-normal leading-tight text-blueGray-600')
        image_element = element.find('img', class_='absolute object-cover w-full h-full')
        url = element['href']

        if not title_element or not price_element:
            continue

        title = title_element.get_text(strip=True)
        price = price_element.get_text(strip=True)
        image = image_element['src'] if image_element else "N/A"
        if url in seen:
            continue
        seen.add(url)

        # Overwrite the location value
        location = locations[location_index % len(locations)]
        location_index += 1

        listing = {
            'title': title,
            'price': price,
            'location': location,
            'url': url,
            'image': image
        }
        listings.append(listing)

        # Insert listing into the database
        cursor.execute('''
            INSERT INTO listings (title, price, location, url, image)
            VALUES (?, ?, ?, ?, ?)
        ''', (listing['title'], listing['price'], listing['location'], listing['url'], listing['image']))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)