# USI - Information Retrieval, 2024, Lino and Jiun

from flask import Flask, render_template, request, jsonify
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
import re
import pyterrier as pt

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
    listings = scrape_airbnb(search_query)
    #listings.extend(scrape_airbnb2(search_query))
    #listings.extend(scrape_airbnb3(search_query))
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
    cursor.execute("SELECT rowid, title, price, location, url, image FROM listings")
    rows = cursor.fetchall()
    conn.close()

    # Prepare the dataset for PyTerrier
    docs = [{'docno': str(row[0]), 'text': f"{row[1]} {row[2]} {row[3]} {row[4]} {row[5]}"} for row in rows]
    indexer = pt.IterDictIndexer('./index')
    indexref = indexer.index(docs)

    # Initialize the PyTerrier pipeline
    pipeline = pt.BatchRetrieve(indexref, wmodel="BM25")

    # Perform the search
    results = pipeline.search(search_query)

    # Fetch the results from the database
    result_ids = [int(docno) for docno in results['docno']]
    conn = sqlite3.connect('listings.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, price, location, url, image FROM listings WHERE rowid IN ({})".format(','.join('?' * len(result_ids))), result_ids)
    listings = cursor.fetchall()
    conn.close()

    return render_template('index.html', listings=listings)

def scrape_airbnb(search_query=None, price=None, location=None):
    url = 'https://www.holidaylettings.co.uk/villas-with-pools/hom_sleeps_max.2/'
    #url = 'https://www.booking.com/searchresults.it.html?label=case-ky3JiZXv9DTZuATr9XpW0gS589026812344%3Apl%3Ata%3Ap1%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-1635741998535%3Alp9186879%3Ali%3Adec%3Adm&sid=6af81181512ff406b2c99b367aab62cc&gclid=Cj0KCQiAx9q6BhCDARIsACwUxu5eYDOdL8dvY3ou1JGoUJrL0Mj8j21HVPmV58ydBCfAHCBhklT9i5EaApPsEALw_wcB&aid=375011&nflt=sth%253D2&city=-114090'
    #url = 'https://citystay.com/en/apartments'
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
    #elements = soup.find_all('div', class_='c82435a4b8 a178069f51 a6ae3c2b40 a18aeea94d d794b7a0f7 f53e278e95 c6710787a4')  # Adjust this to match the new website structure.
    #elements = soup.find_all('a', class_='block')

    irrelevant_titles = {'privacy and cookies statement', 'Owners / Managers', 'common questions', 'terms', 'privacy policy'}
    elements = [el for el in elements if el.get_text(strip=True).lower() not in irrelevant_titles]
    elements = elements[2:] #workaround, remove Owners / Managers

    
    for element in elements:
        title = element.get_text(strip=True)
        title_tag = element.find('div', class_='f6431b446c')  # Class that seems to hold the title.
        #article = element.find('article')
        #title_tag = article.find('h2')

        title = title_tag.get_text(strip=True) if title_tag else 'No title'
        if 'owners' in title.lower():
            continue

        data_param = element.get('data-param', '')
        decoded_url = base64.b64decode(data_param).decode('utf-8') if data_param else 'No URL'
        title = element.get_text(strip=True) if element else 'No title'
        if title in seen:
            continue
        seen.add(title)
        price_tag = element.find_next('span', class_='fs-4')
        #price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
            # Price extraction
        #price_tag = element.find('div', class_='price-class-here')  # Update with correct price class.
        
        price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
        
        location_tag = element.find_next('p', class_='text-gray-700')
        #location_tag = element.find('div', class_='location-class')
        #location_text = location_tag.get_text(strip=True) if location_tag else 'No location'
        # Location extraction
        #location_tag = element.find('span', class_='aee5343fdb')  # Class likely containing the location.
        #location_tag = article.find('p', class_='text-location-s')

        location_text = location_tag.get_text(strip=True) if location_tag else 'No location'

        image_tag = element.find_next('span', class_='pc-photos-list')
        #image_tag = element.find('img', class_='image-class')
            # Image URL extraction
        #image_tag = article.find('img', class_='transition-all')
    
        #image_url = image_tag['src'] if image_tag else 'No image'
        
        if image_tag and 'data-imgs' in image_tag.attrs:
            data_imgs = image_tag['data-imgs']
            first_image = data_imgs.split('|')[0]
            image_url = 'https:' + first_image
        matches_query = search_query is None or search_query.lower() in title.lower()
        matches_price = price is None
        matches_location = location is None
        matches_guest = 2
        if matches_query and matches_price and matches_location:
            listings.append({'title': title, 'price': price_text, 'location': location_text, 'url': decoded_url, 'image': image_url})
    if search_query:
        listings.sort(key=lambda x: (search_query.lower() not in x['title'].lower(), x['title']))
    # Insert listings into the table
    for listing in listings:
        cursor.execute('SELECT COUNT(*) FROM listings WHERE url = ?', (listing['url'],))
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute('''
                INSERT INTO listings (title, price, location, url, image)
                VALUES (?, ?, ?, ?, ?)
            ''', (listing['title'], listing['price'], listing['location'], listing['url'], listing['image']))
    # Commit the transaction and close the connection
    conn.commit()
    conn.close()
    return listings

def scrape_airbnb2(search_query=None, price=None, location=None):
    
    url = 'https://www.booking.com/searchresults.it.html?label=case-ky3JiZXv9DTZuATr9XpW0gS589026812344%3Apl%3Ata%3Ap1%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-1635741998535%3Alp9186879%3Ali%3Adec%3Adm&sid=6af81181512ff406b2c99b367aab62cc&gclid=Cj0KCQiAx9q6BhCDARIsACwUxu5eYDOdL8dvY3ou1JGoUJrL0Mj8j21HVPmV58ydBCfAHCBhklT9i5EaApPsEALw_wcB&aid=375011&nflt=sth%253D2&city=-114090'
    #url = 'https://citystay.com/en/apartments'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Failed', response.status_code)
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    listings = []
    seen = set()

    elements = soup.find_all('div', class_='c82435a4b8 a178069f51 a6ae3c2b40 a18aeea94d d794b7a0f7 f53e278e95 c6710787a4')  # Adjust this to match the new website structure.
    #elements = soup.find_all('a', class_='block')

    irrelevant_titles = {'privacy and cookies statement', 'Owners / Managers', 'common questions', 'terms', 'privacy policy'}
    elements = [el for el in elements if el.get_text(strip=True).lower() not in irrelevant_titles]
    elements = elements[2:] #workaround, remove Owners / Managers

    for element in elements:
        title = element.get_text(strip=True)
        title_tag = element.find('div', class_='f6431b446c')  # Class that seems to hold the title.
        #article = element.find('article')
        #title_tag = article.find('h2')

        title = title_tag.get_text(strip=True) if title_tag else 'No title'
        if 'owners' in title.lower():
            continue

        data_param = element.get('data-param', '')
        decoded_url = base64.b64decode(data_param).decode('utf-8') if data_param else 'No URL'
        title = element.get_text(strip=True) if element else 'No title'
        if title in seen:
            continue
        seen.add(title)
        price_tag = element.find_next('span', class_='fs-4')
        #price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
            # Price extraction
        #price_tag = element.find('div', class_='price-class-here')  # Update with correct price class.
        
        price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
        
        
        location_tag = element.find('div', class_='location-class')
        location_text = location_tag.get_text(strip=True) if location_tag else 'No location'
        # Location extraction
        #location_tag = element.find('span', class_='aee5343fdb')  # Class likely containing the location.
        #location_tag = article.find('p', class_='text-location-s')

        

        
        image_tag = element.find('img', class_='image-class')
            # Image URL extraction
        #image_tag = article.find('img', class_='transition-all')
    
        image_url = image_tag['src'] if image_tag else 'No image'
        
        if image_tag and 'data-imgs' in image_tag.attrs:
            data_imgs = image_tag['data-imgs']
            first_image = data_imgs.split('|')[0]
            image_url = 'https:' + first_image
        matches_query = search_query is None or search_query.lower() in title.lower()
        matches_price = price is None
        matches_location = location is None
        matches_guest = 2
        if matches_query and matches_price and matches_location:
            listings.append({'title': title, 'price': price_text, 'location': location_text, 'url': decoded_url, 'image': image_url})
    if search_query:
        listings.sort(key=lambda x: (search_query.lower() not in x['title'].lower(), x['title']))
    return listings

def scrape_airbnb3(search_query=None, price=None, location=None):
    url = 'https://www.holidaylettings.co.uk/villas-with-pools/hom_sleeps_max.2/'
    #url = 'https://www.booking.com/searchresults.it.html?label=case-ky3JiZXv9DTZuATr9XpW0gS589026812344%3Apl%3Ata%3Ap1%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-1635741998535%3Alp9186879%3Ali%3Adec%3Adm&sid=6af81181512ff406b2c99b367aab62cc&gclid=Cj0KCQiAx9q6BhCDARIsACwUxu5eYDOdL8dvY3ou1JGoUJrL0Mj8j21HVPmV58ydBCfAHCBhklT9i5EaApPsEALw_wcB&aid=375011&nflt=sth%253D2&city=-114090'
    #url = 'https://citystay.com/en/apartments'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Failed', response.status_code)
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    listings = []
    seen = set()

    elements = soup.find_all('a', attrs={'data-param': True})
    #elements = soup.find_all('div', class_='c82435a4b8 a178069f51 a6ae3c2b40 a18aeea94d d794b7a0f7 f53e278e95 c6710787a4')  # Adjust this to match the new website structure.
    #elements = soup.find_all('a', class_='block')

    irrelevant_titles = {'privacy and cookies statement', 'Owners / Managers', 'common questions', 'terms', 'privacy policy'}
    elements = [el for el in elements if el.get_text(strip=True).lower() not in irrelevant_titles]
    elements = elements[2:] #workaround, remove Owners / Managers

    for element in elements:
        title = element.get_text(strip=True)
        title_tag = element.find('div', class_='f6431b446c')  # Class that seems to hold the title.
        #article = element.find('article')
        #title_tag = article.find('h2')

        title = title_tag.get_text(strip=True) if title_tag else 'No title'
        if 'owners' in title.lower():
            continue

        data_param = element.get('data-param', '')
        decoded_url = base64.b64decode(data_param).decode('utf-8') if data_param else 'No URL'
        title = element.get_text(strip=True) if element else 'No title'
        if title in seen:
            continue
        seen.add(title)
        price_tag = element.find_next('span', class_='fs-4')
        #price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
            # Price extraction
        #price_tag = element.find('div', class_='price-class-here')  # Update with correct price class.
        
        price_text = price_tag.get_text(strip=True) if price_tag else 'No price'
        
        location_tag = element.find_next('p', class_='text-gray-700')
        #location_tag = element.find('div', class_='location-class')
        #location_text = location_tag.get_text(strip=True) if location_tag else 'No location'
        # Location extraction
        #location_tag = element.find('span', class_='aee5343fdb')  # Class likely containing the location.
        #location_tag = article.find('p', class_='text-location-s')

        location_text = location_tag.get_text(strip=True) if location_tag else 'No location'

        image_tag = element.find_next('span', class_='pc-photos-list')
        #image_tag = element.find('img', class_='image-class')
            # Image URL extraction
        #image_tag = article.find('img', class_='transition-all')
    
        #image_url = image_tag['src'] if image_tag else 'No image'
        
        if image_tag and 'data-imgs' in image_tag.attrs:
            data_imgs = image_tag['data-imgs']
            first_image = data_imgs.split('|')[0]
            image_url = 'https:' + first_image
        matches_query = search_query is None or search_query.lower() in title.lower()
        matches_price = price is None
        matches_location = location is None
        matches_guest = 2
        if matches_query and matches_price and matches_location:
            listings.append({'title': title, 'price': price_text, 'location': location_text, 'url': decoded_url, 'image': image_url})
    if search_query:
        listings.sort(key=lambda x: (search_query.lower() not in x['title'].lower(), x['title']))
    return listings

if __name__ == '__main__':
    app.run(debug=True)