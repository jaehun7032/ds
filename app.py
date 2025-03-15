from flask import Flask
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from flask_session import Session

app = Flask(__name__)
app.secret_key = "secret_key"

# MongoDB 연결(로컬)
app.config["MONGO_URI"] = "mongodb://localhost:27017/mydatabase"
mongo = PyMongo(app)

bcrypt = Bcrypt(app)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def home():
    return "서버 실행중"

if __name__ == "__main__":
    print("Flask 서버를 시작합니다")
    app.run(debug=True)