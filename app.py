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
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    created_rooms = db.relationship('ChatRoom', foreign_keys='ChatRoom.created_by', backref='creator', lazy=True)

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

# 메시지 모델
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'sender_id': self.sender_id,
            'sender_username': self.sender.username,
            'receiver_id': self.receiver_id,
            'receiver_username': self.receiver.username,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': self.is_read,
            'is_deleted': self.is_deleted
        }

# 그룹 채팅방 모델
class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship('ChatRoomMember', backref='room', lazy=True)
    messages = db.relationship('GroupMessage', backref='room', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'member_count': len(self.members)
        }

# 채팅방 멤버 모델
class ChatRoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref='chat_rooms')

# 그룹 메시지 모델
class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    sender = db.relationship('User', backref='group_messages')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'sender_id': self.sender_id,
            'sender_username': self.sender.username,
            'room_id': self.room_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_deleted': self.is_deleted
        }

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

# 메시지 관련 라우트
@app.route('/messages')
@login_required
def messages():
    # 모든 사용자 목록 (현재 사용자 제외)
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('messages.html', users=users)

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    if other_user.id == current_user.id:
        return redirect(url_for('messages'))
    
    # 두 사용자 간의 메시지 가져오기
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).filter(Message.is_deleted == False).order_by(Message.timestamp).all()
    
    # 읽지 않은 메시지를 읽음으로 표시
    unread_messages = Message.query.filter_by(
        sender_id=user_id, 
        receiver_id=current_user.id, 
        is_read=False,
        is_deleted=False
    ).all()
    for msg in unread_messages:
        msg.is_read = True
    db.session.commit()
    
    return render_template('chat.html', other_user=other_user, messages=messages)

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not content or not receiver_id:
        return jsonify({'error': '메시지 내용과 수신자를 입력해주세요.'}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'error': '수신자를 찾을 수 없습니다.'}), 404
    
    message = Message(
        content=content,
        sender_id=current_user.id,
        receiver_id=receiver_id
    )
    db.session.add(message)
    db.session.commit()
    
    # SocketIO를 통해 실시간으로 메시지 전송
    message_data = message.to_dict()
    socketio.emit('new_message', message_data, room=f'user_{receiver_id}')
    
    return jsonify({'success': True, 'message': message_data})

@app.route('/api/delete_message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    if message.sender_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    message.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/unread_count')
@login_required
def unread_count():
    count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False,
        is_deleted=False
    ).count()
    return jsonify({'count': count})

@app.route('/api/unread_count/<int:sender_id>')
@login_required
def unread_count_by_sender(sender_id):
    count = Message.query.filter_by(
        sender_id=sender_id,
        receiver_id=current_user.id,
        is_read=False,
        is_deleted=False
    ).count()
    return jsonify({'count': count})

# 그룹 채팅 관련 라우트
@app.route('/chat_rooms')
@login_required
def chat_rooms():
    # 사용자가 속한 채팅방 목록
    user_rooms = ChatRoom.query.join(ChatRoomMember).filter(
        ChatRoomMember.user_id == current_user.id
    ).all()
    
    # 모든 사용자 목록 (채팅방 초대용)
    all_users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('chat_rooms.html', rooms=user_rooms, users=all_users)

@app.route('/create_chat_room', methods=['GET', 'POST'])
@login_required
def create_chat_room():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        member_ids = request.form.getlist('members')
        
        if not name:
            flash('채팅방 이름을 입력해주세요.', 'error')
            return redirect(url_for('create_chat_room'))
        
        # 채팅방 생성
        room = ChatRoom(
            name=name,
            description=description,
            created_by=current_user.id
        )
        db.session.add(room)
        db.session.flush()  # ID 생성
        
        # 생성자를 관리자로 추가
        creator_member = ChatRoomMember(
            room_id=room.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(creator_member)
        
        # 선택된 멤버들 추가
        for member_id in member_ids:
            if int(member_id) != current_user.id:
                member = ChatRoomMember(
                    room_id=room.id,
                    user_id=int(member_id)
                )
                db.session.add(member)
        
        db.session.commit()
        flash('채팅방이 생성되었습니다.', 'success')
        return redirect(url_for('group_chat', room_id=room.id))
    
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('create_chat_room.html', users=users)

@app.route('/group_chat/<int:room_id>')
@login_required
def group_chat(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    
    # 사용자가 해당 채팅방의 멤버인지 확인
    member = ChatRoomMember.query.filter_by(
        room_id=room_id, 
        user_id=current_user.id
    ).first()
    
    if not member:
        flash('이 채팅방에 접근할 권한이 없습니다.', 'error')
        return redirect(url_for('chat_rooms'))
    
    # 채팅방 메시지 가져오기
    messages = GroupMessage.query.filter_by(
        room_id=room_id,
        is_deleted=False
    ).order_by(GroupMessage.timestamp).all()
    
    # 채팅방 멤버 목록
    members = ChatRoomMember.query.filter_by(room_id=room_id).all()
    
    # 현재 사용자의 멤버 정보
    current_user_member = member
    
    # 모든 사용자 목록 (초대용)
    users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('group_chat.html', 
                         room=room, 
                         messages=messages, 
                         members=members,
                         current_user_member=current_user_member,
                         users=users)

@app.route('/api/send_group_message', methods=['POST'])
@login_required
def send_group_message():
    data = request.get_json()
    room_id = data.get('room_id')
    content = data.get('content')
    
    if not content or not room_id:
        return jsonify({'error': '메시지 내용과 채팅방을 입력해주세요.'}), 400
    
    # 사용자가 해당 채팅방의 멤버인지 확인
    member = ChatRoomMember.query.filter_by(
        room_id=room_id, 
        user_id=current_user.id
    ).first()
    
    if not member:
        return jsonify({'error': '이 채팅방에 접근할 권한이 없습니다.'}), 403
    
    message = GroupMessage(
        content=content,
        sender_id=current_user.id,
        room_id=room_id
    )
    db.session.add(message)
    db.session.commit()
    
    # SocketIO를 통해 실시간으로 메시지 전송
    message_data = message.to_dict()
    socketio.emit('new_group_message', message_data, room=f'room_{room_id}')
    
    return jsonify({'success': True, 'message': message_data})

@app.route('/api/delete_group_message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_group_message(message_id):
    message = GroupMessage.query.get_or_404(message_id)
    
    if message.sender_id != current_user.id:
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    message.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/invite_to_room/<int:room_id>', methods=['POST'])
@login_required
def invite_to_room(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    
    # 사용자가 관리자인지 확인
    member = ChatRoomMember.query.filter_by(
        room_id=room_id, 
        user_id=current_user.id,
        is_admin=True
    ).first()
    
    if not member:
        flash('관리자만 멤버를 초대할 수 있습니다.', 'error')
        return redirect(url_for('group_chat', room_id=room_id))
    
    user_ids = request.form.getlist('users')
    
    for user_id in user_ids:
        # 이미 멤버인지 확인
        existing_member = ChatRoomMember.query.filter_by(
            room_id=room_id,
            user_id=int(user_id)
        ).first()
        
        if not existing_member:
            new_member = ChatRoomMember(
                room_id=room_id,
                user_id=int(user_id)
            )
            db.session.add(new_member)
    
    db.session.commit()
    flash('멤버가 초대되었습니다.', 'success')
    return redirect(url_for('group_chat', room_id=room_id))

# SocketIO 이벤트 핸들러
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        
        # 사용자가 속한 채팅방들에도 참가
        user_rooms = ChatRoomMember.query.filter_by(user_id=current_user.id).all()
        for member in user_rooms:
            join_room(f'room_{member.room_id}')
        
        emit('status', {'msg': f'{current_user.username}님이 접속했습니다.'})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        
        # 사용자가 속한 채팅방들에서 나가기
        user_rooms = ChatRoomMember.query.filter_by(user_id=current_user.id).all()
        for member in user_rooms:
            leave_room(f'room_{member.room_id}')
        
        emit('status', {'msg': f'{current_user.username}님이 접속을 종료했습니다.'})

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id')
    if current_user.is_authenticated:
        # 사용자가 해당 채팅방의 멤버인지 확인
        member = ChatRoomMember.query.filter_by(
            room_id=room_id,
            user_id=current_user.id
        ).first()
        
        if member:
            join_room(f'room_{room_id}')
            emit('status', {'msg': f'{current_user.username}님이 채팅방에 참가했습니다.'}, room=f'room_{room_id}')

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data.get('room_id')
    if current_user.is_authenticated:
        leave_room(f'room_{room_id}')
        emit('status', {'msg': f'{current_user.username}님이 채팅방을 나갔습니다.'}, room=f'room_{room_id}')

@socketio.on('typing')
def handle_typing(data):
    room = f'user_{data["receiver_id"]}'
    emit('typing', {
        'user_id': current_user.id,
        'username': current_user.username
    }, room=room)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    room = f'user_{data["receiver_id"]}'
    emit('stop_typing', {
        'user_id': current_user.id,
        'username': current_user.username
    }, room=room)

@socketio.on('group_typing')
def handle_group_typing(data):
    room_id = data.get('room_id')
    if current_user.is_authenticated:
        # 사용자가 해당 채팅방의 멤버인지 확인
        member = ChatRoomMember.query.filter_by(
            room_id=room_id,
            user_id=current_user.id
        ).first()
        
        if member:
            emit('group_typing', {
                'user_id': current_user.id,
                'username': current_user.username
            }, room=f'room_{room_id}')

@socketio.on('group_stop_typing')
def handle_group_stop_typing(data):
    room_id = data.get('room_id')
    if current_user.is_authenticated:
        # 사용자가 해당 채팅방의 멤버인지 확인
        member = ChatRoomMember.query.filter_by(
            room_id=room_id,
            user_id=current_user.id
        ).first()
        
        if member:
            emit('group_stop_typing', {
                'user_id': current_user.id,
                'username': current_user.username
            }, room=f'room_{room_id}')

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
