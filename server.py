from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello from Render!"

@app.route('/app')
def hello(name=None):
    return render_template('hello.html', name=name)