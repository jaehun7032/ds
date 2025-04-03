from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)

# 기본 설정
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

# MongoDB 설정
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/mydatabase")
try:
    mongo = PyMongo(app)
except Exception as e:
    print(f"MongoDB 연결 오류: {e}")
    raise

bcrypt = Bcrypt(app)

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Flask-Session 설정
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = mongo.cx
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
    projects = list(mongo.db.projects.find({"members": session["user_id"]}))
    for project in projects:
        project["_id"] = str(project["_id"])
    return render_template("dashboard.html", user=current_user, projects=projects)

# Create new project
@app.route("/projects/create", methods=["POST"])
@login_required
def create_project():
    data = request.json
    new_project = {
        "name": data["name"],
        "description": data.get("description", ""),
        "created_by": session["user_id"],
        "members": [session["user_id"]],
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    result = mongo.db.projects.insert_one(new_project)
    new_project["_id"] = str(result.inserted_id)
    return jsonify(new_project), 201

# Delete project
@app.route("/projects/<project_id>", methods=["DELETE"])
@login_required
def delete_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if project and project["created_by"] == session["user_id"]:
        mongo.db.projects.delete_one({"_id": ObjectId(project_id)})
        return jsonify({"message": "Project deleted"}), 200
    return jsonify({"message": "Unauthorized"}), 403

# Get project details
@app.route("/projects/<project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    if project:
        project["_id"] = str(project["_id"])
        return jsonify(project), 200
    return jsonify({"message": "Project not found"}), 404

# Invite team member
@app.route("/projects/<project_id>/invite", methods=["POST"])
@login_required
def invite_member(project_id):
    data = request.json
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
    
    if not project or project["created_by"] != session["user_id"]:
        return jsonify({"message": "Unauthorized"}), 403
        
    user_to_invite = mongo.db.users.find_one({"username": data["username"]})
    if not user_to_invite:
        return jsonify({"message": "User not found"}), 404
        
    if str(user_to_invite["_id"]) not in project["members"]:
        mongo.db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$push": {"members": str(user_to_invite["_id"])}}
        )
        return jsonify({"message": "Member invited successfully"}), 200
    return jsonify({"message": "User already a member"}), 400

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