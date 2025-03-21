from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 비밀 키

# 데이터 저장을 위한 파일 경로
SCHEDULE_FILE = 'schedules.json'
RESERVATION_FILE = 'reservations.json'

# 파일이 없으면 생성
def initialize_files():
    if not os.path.exists(SCHEDULE_FILE):
            json.dump({}, f)
    
    if not os.path.exists(RESERVATION_FILE):
        with open(RESERVATION_FILE, 'w') as f:
            json.dump({}, f)

initialize_files()

# 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 달력 페이지
@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

# 일정 추가 API
@app.route('/add_schedule', methods=['POST'])
def add_schedule():
    date = request.form.get('date')
    title = request.form.get('title')
    description = request.form.get('description')
    
    # 파일에서 기존 일정 로드
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            schedules = json.load(f)
    except:
        schedules = {}
    
    # 해당 날짜에 일정 추가
    if date not in schedules:
        schedules[date] = []
    
    schedules[date].append({
        'title': title,
        'description': description,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # 일정 저장
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedules, f)
    
    return redirect(url_for('calendar'))

# 일정 조회 API
@app.route('/get_schedules/<date>')
def get_schedules(date):
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            schedules = json.load(f)
            return jsonify(schedules.get(date, []))
    except:
        return jsonify([])

# 실험실 예약 페이지
@app.route('/reservation')
def reservation():
    return render_template('reservation.html')

# 예약 가능한 시간대 가져오기
@app.route('/get_available_slots/<date>')
def get_available_slots(date):
    # 시간 슬롯 (9AM - 5PM, 1시간 단위)
    all_slots = [f"{hour}:00-{hour+1}:00" for hour in range(9, 17)]
    
    # 이미 예약된 슬롯 가져오기
    try:
        with open(RESERVATION_FILE, 'r') as f:
            reservations = json.load(f)
            reserved_slots = [r['time'] for r in reservations.get(date, [])]
            
            # 예약 가능한 슬롯 계산
            available_slots = [slot for slot in all_slots if slot not in reserved_slots]
            return jsonify(available_slots)
    except:
        return jsonify(all_slots)

# 실험실 예약 API
@app.route('/make_reservation', methods=['POST'])
def make_reservation():
    date = request.form.get('date')
    time = request.form.get('time')
    name = request.form.get('name')
    purpose = request.form.get('purpose')
    
    # 파일에서 기존 예약 로드
    try:
        with open(RESERVATION_FILE, 'r') as f:
            reservations = json.load(f)
    except:
        reservations = {}
    
    # 해당 날짜에 예약 추가
    if date not in reservations:
        reservations[date] = []
    
    # 중복 예약 확인
    for r in reservations[date]:
        if r['time'] == time:
            return jsonify({'success': False, 'message': '이미 예약된 시간입니다.'})
    
    reservations[date].append({
        'time': time,
        'name': name,
        'purpose': purpose,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # 예약 저장
    with open(RESERVATION_FILE, 'w') as f:
        json.dump(reservations, f)
    
    return jsonify({'success': True})

# 예약 조회 API
@app.route('/get_reservations/<date>')
def get_reservations(date):
    try:
        with open(RESERVATION_FILE, 'r') as f:
            reservations = json.load(f)
            return jsonify(reservations.get(date, []))
    except:
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True) 