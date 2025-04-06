#from flask import Flask

#app = Flask(__name__)


#@app.route('/')
#def hello_world():  # put application's code here
    #return 'Hello World!'


#if __name__ == '__main__':
    #app.run()

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')  # 'index.html'을 렌더링

if __name__ == '__main__':
    app.run(debug=True)

