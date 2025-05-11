let dragged = null;
let dragClone = null;
let dragTimer = null;
let isDragging = false;
let wasDragging = false;
let startX = 0;
let startY = 0;
let scrollAnimationFrame = null;
let draggedCard = null;
let placeholder = null;

function initializeDragAndDrop() {
  const container = document.querySelector(".project-scroll-container");
  const kanbanBoard = document.querySelector(".kanban-board");

  // 마우스 휠로 가로 스크롤
  container.addEventListener("wheel", e => {
    if (!isDragging) {
      e.preventDefault();
      container.scrollLeft += e.deltaY * 0.5;
    }
  });

  kanbanBoard.addEventListener("wheel", e => {
    if (!isDragging) {
      e.preventDefault();
      kanbanBoard.scrollLeft += e.deltaY * 0.5;
    }
  });

  // 프로젝트 드래그 설정
  const cards = container.querySelectorAll(".project-card-wrapper");
  cards.forEach(card => {
    card.addEventListener("mousedown", e => {
      if (e.target.closest('.task-card')) return;
      e.preventDefault();
      e.stopPropagation();
      startX = e.clientX;
      startY = e.clientY;

      dragTimer = setTimeout(() => {
        startProjectDrag(card, e.clientX, e.clientY);
      }, 200);
    });

    card.addEventListener("mousemove", e => {
      if (isDragging && dragged) {
        e.preventDefault();
        handleProjectDrag(e.clientX, e.clientY);
      }
    });

    card.addEventListener("mouseup", () => {
      clearTimeout(dragTimer);
      if (isDragging) {
        endProjectDrag();
      }
    });

    card.addEventListener("mouseleave", () => {
      clearTimeout(dragTimer);
    });

    card.addEventListener("touchstart", e => {
      if (e.target.closest('.task-card')) return;
      e.preventDefault();
      e.stopPropagation();
      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;

      dragTimer = setTimeout(() => {
        startProjectDrag(card, touch.clientX, touch.clientY);
      }, 300);
    });

    card.addEventListener("touchmove", e => {
      if (isDragging && dragged) {
        e.preventDefault();
        const touch = e.touches[0];
        handleProjectDrag(touch.clientX, touch.clientY);
      }
    });

    card.addEventListener("touchend", () => {
      clearTimeout(dragTimer);
      if (isDragging) {
        endProjectDrag();
      }
    });
  });

  function startProjectDrag(card, x, y) {
    if (isDragging) return;
    isDragging = true;
    wasDragging = true;
    dragged = card;

    card.classList.add("dragging");
    dragClone = card.cloneNode(true);
    dragClone.classList.add("drag-clone");
    dragClone.style.width = `${card.offsetWidth}px`;
    dragClone.style.height = `${card.offsetHeight}px`;
    dragClone.style.left = `${x - card.offsetWidth / 2}px`;
    dragClone.style.top = `${y - card.offsetHeight / 2}px`;
    document.body.appendChild(dragClone);
  }

  function handleProjectDrag(x, y) {
    if (!dragClone || !dragged) return;

    dragClone.style.left = `${x - dragged.offsetWidth / 2}px`;
    dragClone.style.top = `${y - dragged.offsetHeight / 2}px`;

    const containerRect = container.getBoundingClientRect();
    const scrollSpeed = 20;
    const edgeThreshold = 50;

    if (scrollAnimationFrame) {
      cancelAnimationFrame(scrollAnimationFrame);
    }

    function scrollStep() {
      if (!isDragging) return;

      if (x < containerRect.left + edgeThreshold) {
        container.scrollLeft -= scrollSpeed;
      } else if (x > containerRect.right - edgeThreshold) {
        container.scrollLeft += scrollSpeed;
      }

      const target = document.elementFromPoint(x, y);
      const targetCard = target?.closest(".project-card-wrapper");
      if (targetCard && targetCard !== dragged && !targetCard.classList.contains("drag-clone")) {
        const cardRect = targetCard.getBoundingClientRect();
        const insertBeforeTarget = x < cardRect.left + cardRect.width / 2;

        if (insertBeforeTarget) {
          container.insertBefore(dragged, targetCard);
        } else {
          if (targetCard.nextSibling) {
            container.insertBefore(dragged, targetCard.nextSibling);
          } else {
            container.appendChild(dragged);
          }
        }
      }

      if (isDragging) {
        scrollAnimationFrame = requestAnimationFrame(scrollStep);
      }
    }

    scrollAnimationFrame = requestAnimationFrame(scrollStep);
  }

  function endProjectDrag() {
    if (!isDragging || !dragged) return;
    isDragging = false;
    dragged.classList.remove("dragging");

    if (dragClone) {
      dragClone.remove();
      dragClone = null;
    }

    saveProjectOrder();
    dragged = null;

    if (scrollAnimationFrame) {
      cancelAnimationFrame(scrollAnimationFrame);
      scrollAnimationFrame = null;
    }

    setTimeout(() => {
      wasDragging = false;
    }, 100);
  }

  function saveProjectOrder() {
    const order = Array.from(container.querySelectorAll(".project-card-wrapper"))
      .map(card => card.getAttribute("data-project-id"));
    localStorage.setItem("projectOrder", JSON.stringify(order));
  }

  // 카드 드래그 앤 드롭 설정
  const containers = document.querySelectorAll('.card-container');
  containers.forEach(container => {
    container.addEventListener('dragover', handleCardDragOver);
    container.addEventListener('dragenter', handleCardDragEnter);
    container.addEventListener('dragleave', handleCardDragLeave);
    container.addEventListener('drop', handleCardDrop);
  });

  function handleCardDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  function handleCardDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    const container = e.target.closest('.card-container');
    if (container && draggedCard) {
      container.classList.add('drag-over');

      const cards = [...container.querySelectorAll('.task-card:not(.dragging)')];
      const dropY = e.clientY;
      const closestCard = cards.reduce((closest, card) => {
        const box = card.getBoundingClientRect();
        const offset = dropY - (box.top + box.height / 2);
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: card };
        }
        return closest;
      }, { offset: Number.NEGATIVE_INFINITY }).element;

      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.removeChild(placeholder);
      }

      if (closestCard) {
        container.insertBefore(placeholder, closestCard);
      } else {
        container.appendChild(placeholder);
      }
    }
  }

  function handleCardDragLeave(e) {
    e.stopPropagation();
    const container = e.target.closest('.card-container');
    if (container) {
      container.classList.remove('drag-over');
    }
  }

  async function handleCardDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    const container = e.target.closest('.card-container');
    if (!container || !draggedCard) {
      console.error('Drop failed: container or draggedCard is null');
      if (draggedCard) {
        draggedCard.style.display = 'block';
      }
      if (placeholder) {
        placeholder.remove();
        placeholder = null;
      }
      return;
    }

    container.classList.remove('drag-over');
    const cardId = e.dataTransfer.getData('text/plain');
    const targetProjectId = container.dataset.projectId;

    if (placeholder && placeholder.parentNode === container) {
      container.replaceChild(draggedCard, placeholder);
    } else {
      container.appendChild(draggedCard);
    }

    draggedCard.style.display = 'block';
    if (placeholder) {
      placeholder.remove();
      placeholder = null;
    }

    console.log(`Dropping card ${cardId} to project ${targetProjectId}`);
    await updateCardProjectAndOrder(cardId, targetProjectId, container);
  }

  async function updateCardProjectAndOrder(cardId, targetProjectId, container) {
    const cards = [...container.querySelectorAll('.task-card')];
    const order = cards.map(card => card.dataset.cardId);
    console.log(`Updating card ${cardId} to project ${targetProjectId} with order:`, order);
  
    try {
      const sourceProjectId = draggedCard ? draggedCard.dataset.projectId : null;
      // 카드 이동 및 순서 업데이트를 서버에서 한 번에 처리
      const response = await fetch(`/projects/${targetProjectId}/cards/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cardId,
          projectId: targetProjectId,
          order
        })
      });
  
      if (!response.ok) {
        const error = await response.json();
        console.error('카드 이동/순서 업데이트 실패:', error);
        alert(error.message || '카드 이동/순서 업데이트에 실패했습니다.');
        return;
      }
  
      console.log(`Card ${cardId} successfully moved to project ${targetProjectId}`);
      loadCards(); // cards.js에서 정의된 함수 호출
    } catch (error) {
      console.error('Error updating card:', error);
      alert('카드 이동/순서 업데이트 중 오류가 발생했습니다: ' + error.message);
    }
  }
}

function handleCardDragStart(e) {
  e.stopPropagation();
  draggedCard = e.target;
  e.target.classList.add('dragging');
  e.dataTransfer.setData('text/plain', e.target.dataset.cardId);
  e.dataTransfer.effectAllowed = 'move';

  placeholder = document.createElement('div');
  placeholder.className = 'card-placeholder';
  placeholder.style.height = `${draggedCard.offsetHeight}px`;
  setTimeout(() => {
    draggedCard.style.display = 'none';
  }, 0);
}

function handleCardDragEnd(e) {
  e.stopPropagation();
  if (draggedCard) {
    draggedCard.classList.remove('dragging');
    draggedCard.style.display = 'block';
  }
  if (placeholder) {
    placeholder.remove();
    placeholder = null;
  }
  document.querySelectorAll('.card-container').forEach(container => {
    container.classList.remove('drag-over');
  });
  draggedCard = null;
}