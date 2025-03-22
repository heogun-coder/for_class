// 전역 변수
let currentDate = new Date();
let selectedDate = null;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // 시계 업데이트
    updateClock();
    setInterval(updateClock, 1000);

    // 페이지별 초기화
    if (document.getElementById('calendar')) {
        // 달력 페이지
        renderCalendar('calendar');
        setupCalendarNavigation('calendar');
    }

    if (document.getElementById('reservationCalendar')) {
        // 예약 페이지
        renderCalendar('reservationCalendar');
        setupCalendarNavigation('reservationCalendar');
    }

    // 예약 폼 제출 이벤트
    const reservationForm = document.getElementById('reservationForm');
    if (reservationForm) {
        reservationForm.addEventListener('submit', handleReservationSubmit);
    }
});

// 시계 업데이트 함수
function updateClock() {
    const clockElement = document.getElementById('clock');
    if (clockElement) {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        clockElement.textContent = `${hours}:${minutes}:${seconds}`;
    }
}

// 달력 렌더링 함수
function renderCalendar(calendarId) {
    const calendarElement = document.getElementById(calendarId);
    if (!calendarElement) return;

    // 현재 월의 첫 날과 마지막 날
    const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
    
    // 월 표시 업데이트
    const monthNames = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];
    document.getElementById('currentMonth').textContent = `${currentDate.getFullYear()}년 ${monthNames[currentDate.getMonth()]}`;

    // 달력 초기화
    calendarElement.innerHTML = '';

    // 이전 달의 날짜 표시
    const firstDayOfWeek = firstDay.getDay(); // 0: 일요일, 1: 월요일, ...
    for (let i = 0; i < firstDayOfWeek; i++) {
        const prevDate = new Date(firstDay);
        prevDate.setDate(prevDate.getDate() - (firstDayOfWeek - i));
        
        const dayElement = document.createElement('div');
        dayElement.className = 'day other-month';
        dayElement.textContent = prevDate.getDate();
        
        // 날짜가 첫 번째 줄에 표시될 경우 메소드를 분리
        if (calendarId === 'calendar') {
            dayElement.addEventListener('click', function() {
                openViewScheduleModal(formatDate(prevDate));
            });
        } else if (calendarId === 'reservationCalendar') {
            dayElement.addEventListener('click', function() {
                showReservations(formatDate(prevDate));
            });
        }
        
        calendarElement.appendChild(dayElement);
    }

    // 현재 달의 날짜 표시
    for (let i = 1; i <= lastDay.getDate(); i++) {
        const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), i);
        
        const dayElement = document.createElement('div');
        dayElement.className = 'day';
        dayElement.textContent = i;
        
        // 오늘 날짜인지 확인
        const today = new Date();
        if (date.getFullYear() === today.getFullYear() &&
            date.getMonth() === today.getMonth() &&
            date.getDate() === today.getDate()) {
            dayElement.classList.add('today');
        }

        // 날짜 클릭 이벤트
        if (calendarId === 'calendar') {
            // 일정 관리 달력
            dayElement.addEventListener('click', function() {
                openViewScheduleModal(formatDate(date));
            });

            // 이벤트 표시 (일정이 있는 경우)
            checkEvents(formatDate(date), dayElement);
        } else if (calendarId === 'reservationCalendar') {
            // 예약 달력
            dayElement.addEventListener('click', function() {
                showReservations(formatDate(date));
            });
        }
        
        calendarElement.appendChild(dayElement);
    }

    // 다음 달의 날짜 표시 (42개 셀을 채우기 위해)
    const totalCells = 42;
    const daysFromCurrentMonth = firstDayOfWeek + lastDay.getDate();
    const remainingCells = totalCells - daysFromCurrentMonth;
    
    for (let i = 1; i <= remainingCells; i++) {
        const nextDate = new Date(lastDay);
        nextDate.setDate(nextDate.getDate() + i);
        
        const dayElement = document.createElement('div');
        dayElement.className = 'day other-month';
        dayElement.textContent = i;
        
        if (calendarId === 'calendar') {
            dayElement.addEventListener('click', function() {
                openViewScheduleModal(formatDate(nextDate));
            });
        } else if (calendarId === 'reservationCalendar') {
            dayElement.addEventListener('click', function() {
                showReservations(formatDate(nextDate));
            });
        }
        
        calendarElement.appendChild(dayElement);
    }
}

// 날짜 형식 변환 함수 (YYYY-MM-DD)
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 달력 네비게이션 설정
function setupCalendarNavigation(calendarId) {
    document.getElementById('prevMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(calendarId);
    });
    
    document.getElementById('nextMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(calendarId);
    });
}

// 일정 확인 함수
function checkEvents(date, dayElement) {
    fetch(`/get_schedules/${date}`)
        .then(response => response.json())
        .then(schedules => {
            if (schedules.length > 0) {
                const eventDot = document.createElement('div');
                eventDot.className = 'event-dot';
                dayElement.appendChild(eventDot);
            }
        })
        .catch(error => console.error('일정을 불러오는 중 오류가 발생했습니다:', error));
}

// 일정 보기 모달 열기
function openViewScheduleModal(date) {
    selectedDate = date;
    
    document.getElementById('scheduleDate').textContent = formatDisplayDate(date);
    document.getElementById('scheduleList').innerHTML = '<p>일정을 불러오는 중...</p>';
    
    // 모달 표시
    document.getElementById('scheduleViewModal').style.display = 'block';
    
    // 해당 날짜의 일정 가져오기
    fetch(`/get_schedules/${date}`)
        .then(response => response.json())
        .then(schedules => {
            const scheduleList = document.getElementById('scheduleList');
            if (schedules.length > 0) {
                let html = '';
                schedules.forEach(schedule => {
                    html += `
                        <div class="schedule-item">
                            <div class="schedule-header">
                                <h4>${schedule.title}</h4>
                                <button class="delete-btn" onclick="deleteSchedule(${schedule.id})">삭제</button>
                            </div>
                            <p>${schedule.description || '설명 없음'}</p>
                        </div>
                    `;
                });
                scheduleList.innerHTML = html;
            } else {
                scheduleList.innerHTML = '<p>일정이 없습니다.</p>';
            }
        })
        .catch(error => {
            console.error('일정을 불러오는 중 오류가 발생했습니다:', error);
            document.getElementById('scheduleList').innerHTML = '<p>일정을 불러오는 중 오류가 발생했습니다.</p>';
        });
}

// 일정 삭제 함수
function deleteSchedule(scheduleId) {
    if (!confirm('정말로 이 일정을 삭제하시겠습니까?')) {
        return;
    }
    
    fetch(`/delete_schedule/${scheduleId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('일정이 삭제되었습니다.');
            // 현재 보고 있는 날짜의 일정 다시 로드
            openViewScheduleModal(selectedDate);
        } else {
            alert(data.message || '일정 삭제 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('일정 삭제 중 오류가 발생했습니다:', error);
        alert('일정 삭제 중 오류가 발생했습니다.');
    });
}

// 일정 추가 모달 열기
function openAddModal() {
    document.getElementById('scheduleViewModal').style.display = 'none';
    document.getElementById('scheduleAddModal').style.display = 'block';
    document.getElementById('selectedDate').value = selectedDate;
}

// 일정 보기 모달 닫기
function closeViewModal() {
    document.getElementById('scheduleViewModal').style.display = 'none';
}

// 일정 추가 모달 닫기
function closeAddModal() {
    document.getElementById('scheduleAddModal').style.display = 'none';
}

// 예약 현황 표시
function showReservations(date) {
    selectedDate = date;
    document.getElementById('selectedDateDisplay').textContent = formatDisplayDate(date);
    document.getElementById('reservationsList').innerHTML = '<p>예약 정보를 불러오는 중...</p>';
    
    // 해당 날짜의 예약 정보 가져오기
    fetch(`/get_reservations/${date}`)
        .then(response => response.json())
        .then(reservations => {
            const reservationsList = document.getElementById('reservationsList');
            if (reservations.length > 0) {
                let html = '';
                reservations.forEach(reservation => {
                    // 삭제 버튼 (자신의 예약인 경우에만 표시)
                    const deleteButton = reservation.is_owner 
                        ? `<button class="delete-btn" onclick="deleteReservation(${reservation.id})">삭제</button>` 
                        : '';
                    
                    html += `
                        <div class="reservation-slot ${reservation.is_owner ? 'my-reservation' : ''}">
                            <div class="reservation-header">
                                <strong>시간: ${reservation.time}</strong>
                                ${deleteButton}
                            </div>
                            <p><strong>예약자:</strong> ${reservation.name}</p>
                            <p><strong>목적:</strong> ${reservation.purpose}</p>
                        </div>
                    `;
                });
                html += `<button onclick="openReservationModal('${date}')">새 예약 만들기</button>`;
                reservationsList.innerHTML = html;
            } else {
                reservationsList.innerHTML = `
                    <p>예약된 정보가 없습니다.</p>
                    <button onclick="openReservationModal('${date}')">예약하기</button>
                `;
            }
        })
        .catch(error => {
            console.error('예약 정보를 불러오는 중 오류가 발생했습니다:', error);
            document.getElementById('reservationsList').innerHTML = '<p>예약 정보를 불러오는 중 오류가 발생했습니다.</p>';
        });
}

// 예약 모달 열기
function openReservationModal(date) {
    document.getElementById('reservationDate').textContent = formatDisplayDate(date);
    document.getElementById('reservationSelectedDate').value = date;
    document.getElementById('reservationModal').style.display = 'block';
    
    // 사용 가능한 시간 슬롯 가져오기
    fetch(`/get_available_slots/${date}`)
        .then(response => response.json())
        .then(slots => {
            const timeSelect = document.getElementById('time');
            timeSelect.innerHTML = '<option value="">시간을 선택하세요</option>';
            
            slots.forEach(slot => {
                const option = document.createElement('option');
                option.value = slot;
                option.textContent = slot;
                timeSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('사용 가능한 시간 슬롯을 불러오는 중 오류가 발생했습니다:', error);
        });
}

// 예약 모달 닫기
function closeReservationModal() {
    document.getElementById('reservationModal').style.display = 'none';
}

// 예약 제출 처리
function handleReservationSubmit(event) {
    event.preventDefault();
    
    const date = document.getElementById('reservationSelectedDate').value;
    const time = document.getElementById('time').value;
    const purpose = document.getElementById('purpose').value;
    
    // 서버에 예약 정보 전송
    fetch('/make_reservation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `date=${date}&time=${time}&purpose=${purpose}`,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('예약이 완료되었습니다.');
            closeReservationModal();
            showReservations(date);
        } else {
            alert(data.message || '예약 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('예약 처리 중 오류가 발생했습니다:', error);
        alert('예약 처리 중 오류가 발생했습니다.');
    });
}

// 예약 삭제 함수
function deleteReservation(reservationId) {
    if (!confirm('정말로 이 예약을 취소하시겠습니까?')) {
        return;
    }
    
    fetch(`/delete_reservation/${reservationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('예약이 취소되었습니다.');
            // 현재 보고 있는 날짜의 예약 정보 다시 로드
            showReservations(selectedDate);
        } else {
            alert(data.message || '예약 취소 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('예약 취소 중 오류가 발생했습니다:', error);
        alert('예약 취소 중 오류가 발생했습니다.');
    });
}

// 날짜 표시 형식 변환 (YYYY-MM-DD -> YYYY년 MM월 DD일)
function formatDisplayDate(dateString) {
    const parts = dateString.split('-');
    return `${parts[0]}년 ${parts[1]}월 ${parts[2]}일`;
} 