from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def hello_word():
	return "<p>Ciao!</p>"


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('index.html', person=name)

