from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 사용자 모델
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    reservations = db.relationship('LabReservation', backref='user', lazy=True)
    reagent_loans = db.relationship('ReagentLoan', backref='user', lazy=True)

# 일정 모델
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start': self.date.strftime('%Y-%m-%d'),
            'end': self.date.strftime('%Y-%m-%d'),
            'description': self.description,
            'user_id': self.user_id,
            'allDay': True
        }

# 실험실 예약 모델
class LabReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_type = db.Column(db.String(20), nullable=False)  # 물리, 화학, 생명과학, 지구과학
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)  # 자습1, 자습2, 자습3
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# 시약 대여 모델
class Reagent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lab_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    loans = db.relationship('ReagentLoan', backref='reagent', lazy=True)

class ReagentLoan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reagent_id = db.Column(db.Integer, db.ForeignKey('reagent.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    quantity = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        # 최근 일정 5개 가져오기 (모든 사용자의 일정)
        recent_schedules = Schedule.query.order_by(Schedule.date.desc()).limit(5).all()
        return render_template('index.html', schedules=recent_schedules)
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/calendar')
@login_required
def calendar():
    # 모든 사용자의 일정 가져오기
    schedules = Schedule.query.order_by(Schedule.date).all()
    schedule_list = [schedule.to_dict() for schedule in schedules]
    schedule_json = json.dumps(schedule_list)
    return render_template('calendar.html', schedules=schedule_json, user_id=current_user.id)

@app.route('/add_schedule', methods=['POST'])
@login_required
def add_schedule():
    title = request.form.get('title')
    description = request.form.get('description')
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
    
    schedule = Schedule(
        title=title,
        description=description,
        date=date,
        user_id=current_user.id
    )
    db.session.add(schedule)
    db.session.commit()
    return redirect(url_for('calendar'))

@app.route('/lab_reservation', methods=['GET', 'POST'])
@login_required
def lab_reservation():
    if request.method == 'POST':
        lab_type = request.form.get('lab_type')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        time_slot = request.form.get('time_slot')
        
        # 같은 시간대에 이미 예약이 있는지 확인
        existing_reservation = LabReservation.query.filter_by(
            lab_type=lab_type,
            date=date,
            time_slot=time_slot
        ).first()
        
        if existing_reservation:
            flash('이미 예약된 시간입니다.')
            return redirect(url_for('lab_reservation'))
        
        reservation = LabReservation(
            lab_type=lab_type,
            date=date,
            time_slot=time_slot,
            user_id=current_user.id
        )
        db.session.add(reservation)
        db.session.commit()
        return redirect(url_for('lab_reservation'))
    
    # 모든 사용자의 예약 현황 가져오기
    reservations = LabReservation.query.order_by(LabReservation.date, LabReservation.time_slot).all()
    return render_template('lab_reservation.html', reservations=reservations)

@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    if schedule.user_id == current_user.id:
        db.session.delete(schedule)
        db.session.commit()
        flash('일정이 삭제되었습니다.')
    return redirect(url_for('calendar'))

@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    reservation = LabReservation.query.get_or_404(reservation_id)
    if reservation.user_id == current_user.id:
        db.session.delete(reservation)
        db.session.commit()
        flash('예약이 취소되었습니다.')
    return redirect(url_for('lab_reservation'))

@app.route('/manage_reagents', methods=['GET', 'POST'])
@login_required
def manage_reagents():
    if not current_user.is_admin:
        flash('관리자만 접근할 수 있습니다.')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            lab_type = request.form.get('lab_type')
            quantity = int(request.form.get('quantity'))
            
            reagent = Reagent(name=name, lab_type=lab_type, quantity=quantity)
            db.session.add(reagent)
            flash('시약이 추가되었습니다.')
            
        elif action == 'delete':
            reagent_id = request.form.get('reagent_id')
            reagent = Reagent.query.get_or_404(reagent_id)
            db.session.delete(reagent)
            flash('시약이 삭제되었습니다.')
            
        db.session.commit()
        return redirect(url_for('manage_reagents'))
    
    reagents = Reagent.query.all()
    return render_template('manage_reagents.html', reagents=reagents)

@app.route('/reagent_loan', methods=['GET', 'POST'])
@login_required
def reagent_loan():
    if request.method == 'POST':
        reagent_id = request.form.get('reagent_id')
        quantity = int(request.form.get('quantity'))
        loan_date = datetime.strptime(request.form.get('loan_date'), '%Y-%m-%d').date()
        
        reagent = Reagent.query.get(reagent_id)
        if reagent.quantity >= quantity:
            reagent.quantity -= quantity
            loan = ReagentLoan(
                reagent_id=reagent_id,
                user_id=current_user.id,
                loan_date=loan_date,
                quantity=quantity
            )
            db.session.add(loan)
            db.session.commit()
            return redirect(url_for('reagent_loan'))
        flash('Not enough reagents available')
    
    reagents = Reagent.query.all()
    # 모든 사용자의 대여 현황 가져오기
    loans = ReagentLoan.query.order_by(ReagentLoan.loan_date.desc()).all()
    return render_template('reagent_loan.html', reagents=reagents, loans=loans)

@app.route('/return_reagent/<int:loan_id>', methods=['POST'])
@login_required
def return_reagent(loan_id):
    loan = ReagentLoan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        flash('권한이 없습니다.')
        return redirect(url_for('reagent_loan'))
    
    loan.return_date = datetime.now().date()
    reagent = Reagent.query.get(loan.reagent_id)
    reagent.quantity += loan.quantity
    db.session.commit()
    return redirect(url_for('reagent_loan'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 관리자 계정 생성
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('gjrjs1211!'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            
        # 기본 시약 데이터 추가
        if not Reagent.query.first():
            reagents = [
                Reagent(name='염산', lab_type='화학', quantity=10),
                Reagent(name='수산화나트륨', lab_type='화학', quantity=15),
                Reagent(name='황산', lab_type='화학', quantity=8),
                Reagent(name='에탄올', lab_type='화학', quantity=20),
                Reagent(name='메틸렌 블루', lab_type='생명과학', quantity=5),
                Reagent(name='아가로스', lab_type='생명과학', quantity=3),
                Reagent(name='전자석', lab_type='물리', quantity=4),
                Reagent(name='렌즈 세트', lab_type='물리', quantity=6),
                Reagent(name='지질계', lab_type='지구과학', quantity=2),
                Reagent(name='암석 표본', lab_type='지구과학', quantity=10)
            ]
            for reagent in reagents:
                db.session.add(reagent)
            db.session.commit()
    socketio.run(app, debug=True)
