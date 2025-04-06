// 드래그가 가능하도록 설정
const tasks = document.querySelectorAll('.task');
const columns = document.querySelectorAll('.column');

// 드래그 시작 시
tasks.forEach(task => {
    task.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', task.id); // 태스크 ID를 저장
    });
});

// 열에 드래그된 태스크를 놓을 때
columns.forEach(column => {
    column.addEventListener('dragover', (e) => {
        e.preventDefault(); // 기본 동작을 방지
        column.style.backgroundColor = '#e6f7ff'; // 드래그 시 배경색 변경
    });

    column.addEventListener('dragleave', () => {
        column.style.backgroundColor = ''; // 드래그 아웃 시 배경색 복원
    });

    column.addEventListener('drop', (e) => {
        e.preventDefault();
        const taskId = e.dataTransfer.getData('text/plain');
        const task = document.getElementById(taskId);

        // 열에 태스크를 추가
        column.appendChild(task);
        column.style.backgroundColor = ''; // 배경색 복원
    });
});

// 새 태스크 추가 기능
document.getElementById('addTaskForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const taskName = document.getElementById('taskName').value;

    if (taskName) {
        const newTask = document.createElement('div');
        newTask.classList.add('task');
        newTask.setAttribute('draggable', 'true');
        newTask.textContent = taskName;
        newTask.id = 'task-' + Date.now();  // 고유 ID를 시간으로 설정

        // 새 태스크를 'To Do' 열에 추가
        document.getElementById('to-do').appendChild(newTask);

        // 태스크 드래그 이벤트 리스너 추가
        newTask.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', newTask.id);
        });

        // 입력 필드 초기화
        document.getElementById('taskName').value = '';
    }
});
