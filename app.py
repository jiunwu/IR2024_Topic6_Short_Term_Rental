from flask import Flask
from flask import render_template
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/")
def news():
 headlines = scrape_news()
 return render_template("news.html", headlines=headlines)


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
