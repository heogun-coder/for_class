function initializeCalendar(events, userId) {
    document.addEventListener('DOMContentLoaded', function() {
        var calendarEl = document.getElementById('calendar');
        
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            events: events,
            eventClick: function(info) {
                if (info.event.extendedProps.user_id === userId) {
                    if (confirm('이 일정을 삭제하시겠습니까?')) {
                        var form = document.createElement('form');
                        form.method = 'POST';
                        form.action = '/delete_schedule/' + info.event.id;
                        document.body.appendChild(form);
                        form.submit();
                    }
                }
            },
            height: 'auto',
            locale: 'ko'
        });
        
        calendar.render();
    });
} 