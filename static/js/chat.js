// 채팅 관련 JavaScript
let otherUserId = null;
let currentUserId = null;
let typingTimer = null;

// 채팅 초기화
function initChat(otherId, currentId) {
    otherUserId = otherId;
    currentUserId = currentId;
    
    // 메시지 전송 이벤트 리스너
    const messageForm = document.getElementById('message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', handleMessageSubmit);
    }

    // 타이핑 이벤트 리스너
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('input', handleTyping);
    }

    // SocketIO 이벤트 리스너
    if (typeof socket !== 'undefined') {
        socket.on('new_message', handleNewMessage);
        socket.on('typing', handleTypingIndicator);
        socket.on('stop_typing', handleStopTypingIndicator);
    }

    // 초기 스크롤
    scrollToBottom();
}

// 메시지 전송 처리
function handleMessageSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (content) {
        sendMessage(content);
        input.value = '';
        if (typeof socket !== 'undefined') {
            socket.emit('stop_typing', { receiver_id: otherUserId });
        }
    }
}

// 타이핑 처리
function handleTyping() {
    clearTimeout(typingTimer);
    if (typeof socket !== 'undefined') {
        socket.emit('typing', { receiver_id: otherUserId });
    }
    
    typingTimer = setTimeout(function() {
        if (typeof socket !== 'undefined') {
            socket.emit('stop_typing', { receiver_id: otherUserId });
        }
    }, 1000);
}

// 새 메시지 처리
function handleNewMessage(data) {
    if (data.sender_id === otherUserId) {
        addMessage(data, false);
    }
}

// 타이핑 인디케이터 표시
function handleTypingIndicator(data) {
    if (data.user_id === otherUserId) {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }
}

// 타이핑 인디케이터 숨김
function handleStopTypingIndicator(data) {
    if (data.user_id === otherUserId) {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
}

// 메시지 전송 함수
function sendMessage(content) {
    fetch('/api/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            receiver_id: otherUserId,
            content: content
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addMessage(data.message, true);
        } else {
            alert(data.error || '메시지 전송에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('메시지 전송에 실패했습니다.');
    });
}

// 메시지 추가 함수
function addMessage(message, isOwn = false) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `mb-3 ${isOwn ? 'text-end' : ''}`;
    
    const timestamp = new Date(message.timestamp).toLocaleString('ko-KR');
    
    messageDiv.innerHTML = `
        <div class="d-inline-block">
            <div class="${isOwn ? 'bg-primary text-white' : 'bg-light'} rounded p-2" style="max-width: 70%;">
                <div class="message-content">${message.content}</div>
                <small class="${isOwn ? 'text-white-50' : 'text-muted'}">
                    ${timestamp}
                    ${isOwn ? `<button class="btn btn-sm btn-link text-white-50 p-0 ms-2 delete-message-btn" data-message-id="${message.id}">
                        <i class="fas fa-trash"></i>
                    </button>` : ''}
                </small>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// 메시지 삭제 함수
function deleteMessage(messageId) {
    if (confirm('이 메시지를 삭제하시겠습니까?')) {
        fetch(`/api/delete_message/${messageId}`, {
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
    const messagesContainer = document.getElementById('chat-messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// 전역 초기화 함수 (HTML에서 호출)
function initializeChatPage(otherUserId, currentUserId) {
    initChat(otherUserId, currentUserId);
    
    // 삭제 버튼 이벤트 리스너 추가
    document.addEventListener('click', function(e) {
        if (e.target.closest('.delete-message-btn')) {
            const messageId = e.target.closest('.delete-message-btn').dataset.messageId;
            deleteMessage(parseInt(messageId));
        }
    });
} 