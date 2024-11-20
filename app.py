from flask import Flask
from flask import render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/")
def home():
 app.logger.info("run the landing page")   
 titles = scrape_airbnb()
 return render_template("news.html", headlines=titles)


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('index.html', person=name)

def scrape_news():
 url = "https://news.ycombinator.com"
 response = requests.get(url)
 soup = BeautifulSoup(response.content, "html.parser")
 headlines = []
 for headline in soup.find_all("span", class_="titleline"):
 	headlines.append(headline.text)	
 return headlines

def scrape_airbnb():
 app.logger.debug("enter the function")
 r=requests.get('https://en.comparis.ch/immobilien/marktplatz/lugano/moebilierte-wohnung/mieten')
 soup = BeautifulSoup(r.content, "html.parser")
 titles = []	
 for i in soup.find_all("h2"):
    titles.append(i.text)
 return titles
