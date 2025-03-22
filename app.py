from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 비밀 키
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 데이터베이스 생성
with app.app_context():
    db.create_all()

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('아이디 또는 비밀번호가 잘못되었습니다.')
    
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    logout_user()
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
        
        # 사용자 생성
        new_user = User(username=username, email=email)
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
    return render_template('index.html')

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

# 실험실 예약 API
@app.route('/make_reservation', methods=['POST'])
@login_required
def make_reservation():
    date = request.form.get('date')
    time = request.form.get('time')
    purpose = request.form.get('purpose')
    
    # 중복 예약 확인
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
            'created_at': reservation.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True) 