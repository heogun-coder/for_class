from flask import Flask

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/reservation')
def reservation():
    return render_template('reservation.html')

if __name__ == '__main__':
    app.run(debug=True)