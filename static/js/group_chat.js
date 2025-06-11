// 그룹 채팅 관련 JavaScript
let currentRoomId = null;
let currentUserId = null;
let typingTimer = null;

// 그룹 채팅 초기화
function initGroupChat(roomId, userId) {
    currentRoomId = roomId;
    currentUserId = userId;
    
    // 메시지 전송 이벤트 리스너
    const messageForm = document.getElementById('group-message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', handleGroupMessageSubmit);
    }

    // 타이핑 이벤트 리스너
    const messageInput = document.getElementById('group-message-input');
    if (messageInput) {
        messageInput.addEventListener('input', handleGroupTyping);
    }

    // SocketIO 이벤트 리스너
    if (typeof socket !== 'undefined') {
        socket.on('new_group_message', handleNewGroupMessage);
        socket.on('group_typing', handleGroupTypingIndicator);
        socket.on('group_stop_typing', handleGroupStopTypingIndicator);
        
        // 채팅방에 참가
        socket.emit('join_room', { room_id: currentRoomId });
    }

    // 초기 스크롤
    scrollToBottom();
}

// 그룹 메시지 전송 처리
function handleGroupMessageSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('group-message-input');
    const content = input.value.trim();
    
    if (content) {
        sendGroupMessage(content);
        input.value = '';
        if (typeof socket !== 'undefined') {
            socket.emit('group_stop_typing', { room_id: currentRoomId });
        }
    }
}

// 그룹 타이핑 처리
function handleGroupTyping() {
    clearTimeout(typingTimer);
    if (typeof socket !== 'undefined') {
        socket.emit('group_typing', { room_id: currentRoomId });
    }
    
    typingTimer = setTimeout(function() {
        if (typeof socket !== 'undefined') {
            socket.emit('group_stop_typing', { room_id: currentRoomId });
        }
    }, 1000);
}

// 새 그룹 메시지 처리
function handleNewGroupMessage(data) {
    if (data.room_id === currentRoomId) {
        addGroupMessage(data, data.sender_id === currentUserId);
    }
}

// 그룹 타이핑 인디케이터 표시
function handleGroupTypingIndicator(data) {
    if (data.user_id !== currentUserId) {
        const indicator = document.getElementById('group-typing-indicator');
        if (indicator) {
            indicator.textContent = `${data.username}이(가) 입력 중...`;
            indicator.style.display = 'block';
        }
    }
}

// 그룹 타이핑 인디케이터 숨김
function handleGroupStopTypingIndicator(data) {
    if (data.user_id !== currentUserId) {
        const indicator = document.getElementById('group-typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
}

// 그룹 메시지 전송 함수
function sendGroupMessage(content) {
    fetch('/api/send_group_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            room_id: currentRoomId,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addGroupMessage(data.message, true);
        } else {
            alert(data.error || '메시지 전송에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('메시지 전송에 실패했습니다.');
    });
}

// 그룹 메시지 추가 함수
function addGroupMessage(message, isOwn = false) {
    const messagesContainer = document.getElementById('group-chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `mb-3 ${isOwn ? 'text-end' : ''}`;
    
    const timestamp = new Date(message.timestamp).toLocaleString('ko-KR');
    
    messageDiv.innerHTML = `
        <div class="d-inline-block">
            <div class="${isOwn ? 'bg-primary text-white' : 'bg-light'} rounded p-2" style="max-width: 70%;">
                <div class="message-content">
                    ${!isOwn ? `<strong>${message.sender_username}</strong><br>` : ''}
                    ${message.content}
                </div>
                <small class="${isOwn ? 'text-white-50' : 'text-muted'}">
                    ${timestamp}
                    ${isOwn ? `<button class="btn btn-sm btn-link text-white-50 p-0 ms-2 delete-group-message-btn" data-message-id="${message.id}">
                        <i class="fas fa-trash"></i>
                    </button>` : ''}
                </small>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 그룹 메시지 삭제 함수
function deleteGroupMessage(messageId) {
    if (confirm('이 메시지를 삭제하시겠습니까?')) {
        fetch(`/api/delete_group_message/${messageId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 메시지 요소 제거
                const messageElements = document.querySelectorAll('.mb-3');
                messageElements.forEach(element => {
                    if (element.querySelector(`[data-message-id="${messageId}"]`)) {
                        element.remove();
                    }
                });
            } else {
                alert(data.error || '메시지 삭제에 실패했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('메시지 삭제에 실패했습니다.');
        });
    }
}

// 스크롤을 맨 아래로
function scrollToBottom() {
    const messagesContainer = document.getElementById('group-chat-messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// 전역 초기화 함수 (HTML에서 호출)
function initializeGroupChatPage(roomId, userId) {
    initGroupChat(roomId, userId);
    
    // 그룹 메시지 삭제 버튼 이벤트 리스너 추가
    document.addEventListener('click', function(e) {
        if (e.target.closest('.delete-group-message-btn')) {
            const messageId = e.target.closest('.delete-group-message-btn').dataset.messageId;
            deleteGroupMessage(parseInt(messageId));
        }
    });
} 