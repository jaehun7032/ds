from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "secret_key"

# MongoDB 설정
app.config["MONGO_URI"] = "mongodb://localhost:27017/mydatabase"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)

#flask_login 설정
app.config["SECRET_KET"] = "secret_key"
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

#flask_session 설정
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = mongo.cx  # cx는 MongoDB 클라이언트 연결 객체
app.config["SESSION_MONGODB_DB"] = "user_db"
app.config["SESSION_MONGODB_COLLECTION"] = "sessions"
Session(app)

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

#회원가입
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        mongo.db.users.insert_one({"username": username, "password": hashed_password})
        return redirect(url_for("login"))

    return render_template("register.html")

#로그인
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = mongo.db.users.find_one({"username": username})

        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(str(user["_id"])))
            session["user_id"] = str(user["_id"])  # Flask-Session에 저장
            return redirect(url_for("dashboard"))
        else:
            return "로그인 실패! 아이디 또는 비밀번호를 확인하세요."

    return render_template("login.html")

#로그아웃
@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("user_id", None)  # Flask-Session에서도 삭제
    return redirect(url_for("login"))


#로그인 이후 메인화면
@app.route("/dashboard")
@login_required
def dashboard():
    tasks = list(mongo.db.tasks.find())  # 모든 할 일 가져오기
    for task in tasks:
        task["_id"] = str(task["_id"])  # ObjectId를 문자열로 변환
    return render_template("dashboard.html", user=current_user, tasks=tasks)

@app.route("/add", methods=["POST"])
def add_task():
    data = request.json
    new_task = {
        "title": data["title"],
        "status": data["status"], 
        "category": data["category"], 
        "assignee": data["assignee"]
    }
    mongo.db.tasks.insert_one(new_task)
    return jsonify({"message": "Task added"}), 201

@app.route("/update/<task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.json
    mongo.db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": data["status"]}})
    return jsonify({"message": "Task updated"}), 200

@app.route("/delete/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    mongo.db.tasks.delete_one({"_id": ObjectId(task_id)})
    return jsonify({"message": "Task deleted"}), 200

if __name__ == "__main__":
    app.run(debug=True)