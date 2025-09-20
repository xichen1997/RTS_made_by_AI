const joinButton = document.getElementById("join-button");
const nameInput = document.getElementById("player-name");
const statusSpan = document.getElementById("status");
const creditsSpan = document.getElementById("credits");
const canvas = document.getElementById("battle-canvas");
const ctx = canvas.getContext("2d");

let websocket = null;
let playerId = null;
let playerColor = "#ffffff";
let lastState = null;
let selection = null;
let animationHandle = null;

const commandButtons = document.querySelectorAll("[data-command]");

function connect() {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    return;
  }
  const name = nameInput.value.trim() || "Commander";
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socketUrl = `${protocol}://${window.location.host}/ws?name=${encodeURIComponent(
    name
  )}`;
  websocket = new WebSocket(socketUrl);
  statusSpan.textContent = "Connecting";

  websocket.addEventListener("open", () => {
    joinButton.disabled = true;
    statusSpan.textContent = "Matchmaking";
  });

  websocket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "welcome") {
      playerId = data.player.id;
      playerColor = data.player.color;
      statusSpan.textContent = "Awaiting opponent";
      return;
    }
    if (data.type === "state") {
      lastState = data.state;
      updateUi();
      if (!animationHandle) {
        animationHandle = requestAnimationFrame(renderLoop);
      }
      if (data.state.winner) {
        statusSpan.textContent =
          data.state.winner === playerId ? "Victory" : "Defeat";
      }
    }
  });

  websocket.addEventListener("close", () => {
    joinButton.disabled = false;
    statusSpan.textContent = "Disconnected";
    playerId = null;
    lastState = null;
    if (animationHandle) {
      cancelAnimationFrame(animationHandle);
      animationHandle = null;
    }
    clearCanvas();
  });

  websocket.addEventListener("error", () => {
    statusSpan.textContent = "Connection error";
  });
}

joinButton.addEventListener("click", connect);

commandButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
    const payload = { type: button.dataset.type };
    websocket.send(
      JSON.stringify({
        action: button.dataset.command,
        payload,
      })
    );
  });
});

canvas.addEventListener("click", (event) => {
  if (!lastState || !playerId) return;
  const pos = canvasToWorld(event.offsetX, event.offsetY);
  const myUnits = lastState.players[playerId]?.units ?? [];
  const hitUnit = myUnits.find((unit) => distance(unit, pos) < 1.5);
  if (hitUnit) {
    selection = hitUnit.id;
  }
});

canvas.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  if (!lastState || !playerId || selection === null) return;
  if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
  const worldPos = canvasToWorld(event.offsetX, event.offsetY);
  const enemyUnit = findEnemyAt(worldPos);
  if (enemyUnit) {
    websocket.send(
      JSON.stringify({
        action: "attack",
        payload: { unit: selection, target: enemyUnit.id },
      })
    );
  } else {
    websocket.send(
      JSON.stringify({
        action: "move",
        payload: { unit: selection, position: [worldPos.x, worldPos.y] },
      })
    );
  }
});

function updateUi() {
  if (!lastState || !playerId) return;
  const player = lastState.players[playerId];
  creditsSpan.textContent = player ? player.credits : 0;
  if (player && player.base) {
    statusSpan.textContent = "In combat";
  }
}

function renderLoop() {
  clearCanvas();
  if (lastState) {
    drawGrid();
    drawResources();
    drawPlayers();
  }
  animationHandle = requestAnimationFrame(renderLoop);
}

function clearCanvas() {
  ctx.fillStyle = "#030712";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function drawGrid() {
  const mapWidth = lastState.config.map[0];
  const mapHeight = lastState.config.map[1];
  const scale = getScale();
  ctx.strokeStyle = "rgba(148, 163, 184, 0.1)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= mapWidth; x += 5) {
    ctx.beginPath();
    ctx.moveTo(x * scale.x, 0);
    ctx.lineTo(x * scale.x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= mapHeight; y += 5) {
    ctx.beginPath();
    ctx.moveTo(0, y * scale.y);
    ctx.lineTo(canvas.width, y * scale.y);
    ctx.stroke();
  }
}

function drawResources() {
  const scale = getScale();
  ctx.fillStyle = "#facc15";
  lastState.resources.forEach((node) => {
    ctx.beginPath();
    ctx.arc(node.x * scale.x, node.y * scale.y, 6, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawPlayers() {
  const scale = getScale();
  Object.values(lastState.players).forEach((player) => {
    if (player.base) {
      ctx.fillStyle = player.color;
      ctx.fillRect(
        player.base.x * scale.x - 10,
        player.base.y * scale.y - 10,
        20,
        20
      );
    }
    player.units.forEach((unit) => {
      const radius = unit.unit_type === "harvester" ? 7 : 5;
      ctx.beginPath();
      ctx.fillStyle = player.color;
      ctx.arc(unit.x * scale.x, unit.y * scale.y, radius, 0, Math.PI * 2);
      ctx.fill();
      if (player.id === playerId && unit.id === selection) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(unit.x * scale.x, unit.y * scale.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
    });
  });
}

function getScale() {
  if (!lastState) return { x: 1, y: 1 };
  const mapWidth = lastState.config.map[0];
  const mapHeight = lastState.config.map[1];
  return {
    x: canvas.width / mapWidth,
    y: canvas.height / mapHeight,
  };
}

function canvasToWorld(x, y) {
  const scale = getScale();
  return { x: x / scale.x, y: y / scale.y };
}

function distance(unit, pos) {
  const dx = unit.x - pos.x;
  const dy = unit.y - pos.y;
  return Math.hypot(dx, dy);
}

function findEnemyAt(pos) {
  if (!lastState || !playerId) return null;
  for (const player of Object.values(lastState.players)) {
    if (player.id === playerId) continue;
    for (const unit of player.units) {
      if (distance(unit, pos) < 1.25) {
        return unit;
      }
    }
  }
  return null;
}

window.addEventListener("beforeunload", () => {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.close();
  }
});
