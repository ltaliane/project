from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/1548021')
def schet():
  return render_template('1548021.html')

@app.route('/44243855')
def schet2():
  return render_template('44243855.html')

app.run(host="0.0.0.0")