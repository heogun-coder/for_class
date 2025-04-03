from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 비밀 키
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# AWS Cognito 설정
oauth = OAuth(app)
oauth.register(
    name="cognito",
    server_metadata_url="https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EBA96hq4a/.well-known/openid-configuration",
    client_id="1dompom8s0t0sf89h1h5ctbgp",
    client_kwargs={"scope": "phone openid email profile"},
    client_secret="<client secret>",  # 실제 프로덕션에서는 환경 변수 등 안전한 방법으로 관리
)

# 데이터베이스 초기화
db = SQLAlchemy(app)

# 로그인 매니저 초기화
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'

# 사용자 모델
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)  # Cognito 사용자는 NULL 가능
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_admin = db.Column(db.Boolean, default=False)  # 관리자 여부
    auth_type = db.Column(db.String(20), default='local')  # 'local' 또는 'cognito'
    cognito_sub = db.Column(db.String(100), unique=True, nullable=True)  # Cognito 사용자 ID
    
    # 일정 및 예약과의 관계 설정
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    reservations = db.relationship('Reservation', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 일정 모델
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# 예약 모델
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('date', 'time', name='_date_time_uc'),)

# 할 일 모델
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# 데이터베이스 생성
with app.app_context():
    db.create_all()
    
    # admin 계정 생성 (처음 실행 시에만)
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('gjrjs1211!')
        db.session.add(admin)
        db.session.commit()
        
        # 초기 할 일 데이터 추가
        tasks = [
            Task(title="레포트 작성 마감", due_date="2025-06-10"),
            Task(title="중간고사 대비 스터디", due_date="2025-06-15"),
            Task(title="실험 데이터 분석", due_date="2025-06-20"),
            Task(title="논문 초안 제출", due_date="2025-06-25"),
            Task(title="팀 프로젝트 발표", due_date="2025-06-30")
        ]
        
        for task in tasks:
            db.session.add(task)
        
        db.session.commit()

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Cognito 인증으로부터 리다이렉트된 경우
    if 'cognito_login' in session and 'user' in session:
        cognito_user = session.get('user')
        
        # 이메일로 사용자 찾기
        user = User.query.filter_by(email=cognito_user.get('email')).first()
        
        # 사용자가 없으면 새로 생성
        if not user:
            user = User(
                username=cognito_user.get('preferred_username', cognito_user.get('email')),
                email=cognito_user.get('email'),
                auth_type='cognito',
                cognito_sub=cognito_user.get('sub')
            )
            db.session.add(user)
            db.session.commit()
        elif user.auth_type != 'cognito':
            # 기존 로컬 사용자를 Cognito 연결
            user.auth_type = 'cognito'
            user.cognito_sub = cognito_user.get('sub')
            db.session.commit()
            
        login_user(user)
        # 세션 정리
        session.pop('cognito_login', None)
        
        next_page = session.pop('next_url', None)
        return redirect(next_page or url_for('index'))
    
    # 일반 로그인 처리
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.auth_type == 'local' and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('아이디 또는 비밀번호가 잘못되었습니다.')
    
    return render_template('login.html')

# 로컬 개발용 Cognito 테스트 로그인 (실제 배포 시 제거)
@app.route('/test-cognito-login')
def test_cognito_login():
    # 테스트 Cognito 사용자 정보 생성
    test_user_info = {
        'sub': 'test-cognito-user-id',
        'email': 'test-cognito@example.com',
        'preferred_username': 'cognito_user'
    }
    
    # 세션에 저장
    session['cognito_login'] = True
    session['user'] = test_user_info
    
    # 로그인 프로세스로 리디렉션
    return redirect(url_for('login'))

# Cognito 로그인
@app.route('/login/cognito')
def cognito_login():
    # 인증 후 리다이렉트될 URL
    redirect_uri = url_for('cognito_callback', _external=True)
    session['next_url'] = request.args.get('next', url_for('index'))
    
    return oauth.cognito.authorize_redirect(redirect_uri)

# Cognito 콜백
@app.route('/login/cognito/callback')
def cognito_callback():
    token = oauth.cognito.authorize_access_token()
    user_info = oauth.cognito.parse_id_token(token)
    session['user'] = user_info
    session['cognito_login'] = True
    
    return redirect(url_for('login'))

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    # Cognito 사용자인 경우 Cognito 로그아웃 URL 생성
    logout_url = None
    if current_user.auth_type == 'cognito':
        logout_url = oauth.cognito.client_id+'&logout_uri='+url_for('login', _external=True)
        logout_url = 'https://lab-management.auth.us-east-2.amazoncognito.com/logout?client_id='+logout_url
    
    logout_user()
    session.clear()
    
    if logout_url:
        return redirect(logout_url)
    return redirect(url_for('login'))

# 회원가입 페이지
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 입력 검증
        if not username or not email or not password or not confirm_password:
            flash('모든 필드를 입력해주세요.')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
            return render_template('register.html')
        
        # 중복 확인
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('이미 사용 중인 아이디입니다.')
            return render_template('register.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('이미 사용 중인 이메일입니다.')
            return render_template('register.html')
        
        # 사용자 생성 (로컬 인증)
        new_user = User(username=username, email=email, auth_type='local')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# 메인 페이지
@app.route('/')
@login_required
def index():
    # 마감일이 가까운 할 일 5개 가져오기
    upcoming_tasks = Task.query.order_by(Task.due_date).limit(5).all()
    return render_template('index.html', upcoming_tasks=upcoming_tasks)

# 달력 페이지
@app.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')

# 일정 추가 API
@app.route('/add_schedule', methods=['POST'])
@login_required
def add_schedule():
    date = request.form.get('date')
    title = request.form.get('title')
    description = request.form.get('description')
    
    new_schedule = Schedule(
        date=date,
        title=title,
        description=description,
        user_id=current_user.id
    )
    
    db.session.add(new_schedule)
    db.session.commit()
    
    return redirect(url_for('calendar'))

# 일정 조회 API
@app.route('/get_schedules/<date>')
@login_required
def get_schedules(date):
    schedules = Schedule.query.filter_by(date=date, user_id=current_user.id).all()
    
    result = []
    for schedule in schedules:
        result.append({
            'id': schedule.id,
            'title': schedule.title,
            'description': schedule.description,
            'created_at': schedule.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(result)

# 일정 삭제 API
@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    
    # 관리자이거나 자신의 일정만 삭제할 수 있도록 확인
    if not current_user.is_admin and schedule.user_id != current_user.id:
        return jsonify({'success': False, 'message': '삭제 권한이 없습니다.'}), 403
    
    date = schedule.date  # 삭제 후 리디렉션을 위해 날짜 저장
    
    db.session.delete(schedule)
    db.session.commit()
    
    return jsonify({'success': True})

# 실험실 예약 페이지
@app.route('/reservation')
@login_required
def reservation():
    return render_template('reservation.html')

# 예약 가능한 시간대 가져오기
@app.route('/get_available_slots/<date>')
@login_required
def get_available_slots(date):
    # 시간 슬롯 (9AM - 5PM, 1시간 단위)
    all_slots = [f"{hour}:00-{hour+1}:00" for hour in range(9, 17)]
    
    # 이미 예약된 슬롯 가져오기
    reserved_slots = [reservation.time for reservation in Reservation.query.filter_by(date=date).all()]
    
    # 예약 가능한 슬롯 계산
    available_slots = [slot for slot in all_slots if slot not in reserved_slots]
    
    return jsonify(available_slots)

# 예약 생성 API
@app.route('/add_reservation', methods=['POST'])
@login_required
def add_reservation():
    date = request.form.get('date')
    time = request.form.get('time')
    purpose = request.form.get('purpose')
    
    # 입력값 검증
    if not date or not time or not purpose:
        return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'})
    
    # 예약 중복 검사
    existing_reservation = Reservation.query.filter_by(date=date, time=time).first()
    if existing_reservation:
        return jsonify({'success': False, 'message': '이미 예약된 시간입니다.'})
    
    # 새 예약 생성
    new_reservation = Reservation(
        date=date,
        time=time,
        purpose=purpose,
        user_id=current_user.id
    )
    
    db.session.add(new_reservation)
    db.session.commit()
    
    return jsonify({'success': True})

# 예약 조회 API
@app.route('/get_reservations/<date>')
@login_required
def get_reservations(date):
    reservations = Reservation.query.filter_by(date=date).all()
    
    result = []
    for reservation in reservations:
        user = User.query.get(reservation.user_id)
        result.append({
            'id': reservation.id,
            'time': reservation.time,
            'name': user.username,
            'purpose': reservation.purpose,
            'created_at': reservation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_owner': reservation.user_id == current_user.id  # 자신의 예약인지 확인
        })
    
    return jsonify(result)

# 예약 삭제 API
@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def delete_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 관리자이거나 자신의 예약만 삭제할 수 있도록 확인
    if not current_user.is_admin and reservation.user_id != current_user.id:
        return jsonify({'success': False, 'message': '삭제 권한이 없습니다.'}), 403
    
    db.session.delete(reservation)
    db.session.commit()
    
    return jsonify({'success': True})

# 할 일 목록 API
@app.route('/get_tasks')
@login_required
def get_tasks():
    tasks = Task.query.order_by(Task.due_date).all()
    
    result = []
    for task in tasks:
        result.append({
            'id': task.id,
            'title': task.title,
            'due_date': task.due_date,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(result)

# 할 일 추가 API (관리자만)
@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '관리자만 추가할 수 있습니다.'}), 403
    
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    
    new_task = Task(
        title=title,
        due_date=due_date
    )
    
    db.session.add(new_task)
    db.session.commit()
    
    return jsonify({'success': True})

# 할 일 삭제 API (관리자만)
@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '관리자만 삭제할 수 있습니다.'}), 403
    
    task = Task.query.get_or_404(task_id)
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'success': True})

# 관리자 페이지 - 사용자 관리
@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('관리자만 접근할 수 있습니다.')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# 사용자 권한 변경 API (관리자만)
@app.route('/admin/users/change_role/<int:user_id>', methods=['POST'])
@login_required
def change_user_role(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '관리자만 접근할 수 있습니다.'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # 자기 자신은 변경 불가
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '자신의 권한은 변경할 수 없습니다.'}), 403
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 
