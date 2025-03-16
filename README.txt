가상환경 설정법
1. 가상환경 생성
python -m venv venv

2. 가상환경 활성화
venv\Scripts\activate
활성화시 터미널 앞에 (venv)가 표시됨
비활성화 하려면 터미널에 deactivate 입력

터미널 스크립트 실행 차단 시
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
입력하여 권한 부여

3.가상환경에 패키지 설치
pip install flask pymongo flask-bcrypt flask-session
pip install flask-pymongo

또는

pip install -r requirements.txt

한 일
1. Flask 서버 실행 테스트
2. MongoDB와 연결 설정 (로컬)
3. 가상환경 패키지목록 requirements.txt 생성

4. 회원가입, 로그인 기능 구현
5. 대쉬보드 드래그 앤 드롭기능 구현
6. 사이드 바 열고 닫기 기능 구현

다음 할 일 : 프로젝트 생성, 삭제 기능 만들기