function openModal(date) {
    document.getElementById('modal').style.display = 'block';
    document.getElementById('scheduleForm').onsubmit = function(event) {
        event.preventDefault();
        const schedule = document.getElementById('schedule').value;
        alert(date + '에 일정이 추가되었습니다: ' + schedule);
        closeModal();
    };
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}
function updateClock() {
    const now = new Date();
    const clock = document.getElementById('clock');
    clock.innerText = now.toLocaleTimeString();
}

setInterval(updateClock, 1000);
updateClock();