// 메시지 목록 관련 JavaScript

// 각 사용자별 읽지 않은 메시지 수 업데이트
function updateUserUnreadCounts() {
    // 모든 사용자 배지 요소를 찾아서 업데이트
    const badges = document.querySelectorAll('[id^="unread-"]');
    badges.forEach(function(badge) {
        const userId = badge.id.replace('unread-', '');
        fetch(`/api/unread_count/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.className = 'badge bg-danger rounded-pill';
                } else {
                    badge.textContent = '0';
                    badge.className = 'badge bg-secondary rounded-pill';
                }
            })
            .catch(error => {
                console.error('Error fetching unread count:', error);
            });
    });
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    updateUserUnreadCounts();
    
    // SocketIO 이벤트 리스너
    if (typeof socket !== 'undefined') {
        socket.on('new_message', function(data) {
            updateUserUnreadCounts();
        });
    }
}); 