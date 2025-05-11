from itsdangerous import URLSafeTimedSerializer
from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_mail import Message
from app.utils.mail import mail
from app.utils.helpers import logger
from bson import ObjectId
from authlib.integrations.flask_client import OAuth
import os

oauth = None
serializer = None  # ✅ 전역 변수만 선언
auth_bp = Blueprint('auth', __name__)

# 초기화 함수
def init_auth(app):
    global mongo, bcrypt, oauth, serializer
    mongo = PyMongo(app)
    bcrypt = Bcrypt(app)
    oauth = OAuth(app)
    serializer = URLSafeTimedSerializer(app.secret_key)  # ✅ 안전하게 초기화

    # Google OAuth
    oauth.register(
        name='google',
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        access_token_url='https://oauth2.googleapis.com/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'email profile'}
    )

    # Kakao OAuth
    oauth.register(
        name='kakao',
        client_id=os.environ.get("KAKAO_REST_API_KEY"),
        access_token_url='https://kauth.kakao.com/oauth/token',
        authorize_url='https://kauth.kakao.com/oauth/authorize',
        api_base_url='https://kapi.kakao.com/v2/user/me',
        client_kwargs={'scope': 'profile_nickname profile_image'}
    )

# 홈
@auth_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    return redirect(url_for("auth.login"))

# 회원가입
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        if mongo.db.users.find_one({"username": username}):
            return "이미 존재하는 사용자입니다."

        token = serializer.dumps(username, salt='email-confirm')
        verify_link = url_for('auth.verify_email', token=token, _external=True)

        msg = Message(
            subject="회원가입 이메일 인증",
            sender=os.environ.get("MAIL_USERNAME"),
            recipients=[username],
            body=f"[CollabTool] 아래 링크를 클릭해 이메일 인증을 완료해주세요:\n\n{verify_link}\n\n이 링크는 1시간 동안만 유효합니다."
        )
        mail.send(msg)

        mongo.db.users.insert_one({
            "username": username,
            "password": hashed_password,
            "auth_type": "local",
            "invitations": [],
            "is_verified": False
        })

        return "회원가입 완료! 입력하신 이메일에서 인증을 완료해주세요."

    return render_template("register.html")

# 이메일 인증
@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        username = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return "유효하지 않거나 만료된 토큰입니다."

    mongo.db.users.update_one(
        {"username": username},
        {"$set": {"is_verified": True}}
    )
    return "이메일 인증이 완료되었습니다. 이제 로그인하실 수 있습니다."

# 로그인
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_data = mongo.db.users.find_one({"username": username})

        if not user_data:
            return "존재하지 않는 사용자입니다."
        if not user_data.get("is_verified", False):
            return "이메일 인증이 완료되지 않았습니다."
        if not bcrypt.check_password_hash(user_data["password"], password):
            return "비밀번호가 틀렸습니다."

        from app.__main__ import User
        user = User(user_data)
        login_user(user)
        session["user_id"] = user.id
        return redirect(url_for("auth.dashboard"))

    return render_template("login.html")

# 로그아웃
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("user_id", None)
    return redirect(url_for("auth.login"))

# 대시보드
@auth_bp.route("/dashboard")
@login_required
def dashboard():
    user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    projects = mongo.db.projects.find({"members": ObjectId(current_user.id)}).sort("order", 1)

    project_list = []
    for project in projects:
        project["owner"] = str(project.get("owner", None))
        card_count = mongo.db.cards.count_documents({"project_id": project["_id"]})
        project["card_count"] = card_count
        project_list.append(project)

    return render_template(
        "dashboard.html",
        user={"_id": str(current_user.id), "username": current_user.username},
        projects=project_list
    )

# 소셜 로그인 시작
@auth_bp.route("/login/<provider>")
def oauth_login(provider):
    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

# 소셜 로그인 콜백
@auth_bp.route("/callback/<provider>")
def oauth_callback(provider):
    client = oauth.create_client(provider)
    token = client.authorize_access_token()

    if provider == "google":
        resp = client.get("userinfo")
    elif provider == "kakao":
        resp = client.get("https://kapi.kakao.com/v2/user/me")

    user_info = resp.json()

    if provider == "google":
        username = user_info.get("email")
    elif provider == "kakao":
        kakao_id = str(user_info.get("id"))
        kakao_account = user_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        nickname = profile.get("nickname", "KakaoUser")
        username = f"{nickname}_{kakao_id}"

    user_data = mongo.db.users.find_one({"username": username})
    if not user_data:
        mongo.db.users.insert_one({
            "username": username,
            "password": None,
            "auth_type": provider,
            "invitations": [],
            "is_verified": True
        })
        user_data = mongo.db.users.find_one({"username": username})

    from app.__main__ import User
    user = User(user_data)
    login_user(user)
    session["user_id"] = user.id

    return redirect(url_for("auth.dashboard"))
