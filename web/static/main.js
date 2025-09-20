const canvas = document.getElementById("battlefield");
const ctx = canvas.getContext("2d");
const productionButtons = document.querySelectorAll("button[data-unit]");
const rallyButton = document.getElementById("set-rally");
const playerListEl = document.getElementById("player-list");
const eventLogEl = document.getElementById("event-log");
const playerNameEl = document.getElementById("player-name");
const playerCreditsEl = document.getElementById("player-credits");

const MAP_WIDTH = 48;
const MAP_HEIGHT = 32;
const SCALE_X = canvas.width / MAP_WIDTH;
const SCALE_Y = canvas.height / MAP_HEIGHT;

let socket;
let localPlayerId = null;
let latestState = null;
let rallyMode = false;
let selectedUnits = new Set();

function connect() {
  const defaultName = `Commander-${Math.floor(Math.random() * 999)}`;
  const name = prompt("Enter your callsign", defaultName) || defaultName;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${window.location.host}/ws?name=${encodeURIComponent(name)}`);

  socket.addEventListener("open", () => {
    logEvent("Connected to ChronoFront server.");
  });

  socket.addEventListener("close", () => {
    logEvent("Connection closed. Refresh to reconnect.");
  });

  socket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "init") {
      localPlayerId = data.player_id;
      latestState = data.payload;
      updateUI();
    } else if (data.type === "state") {
      latestState = data.payload;
      processEvents(data.events || []);
      updateUI();
    } else if (data.type === "error") {
      alert(data.message);
    }
  });
}

function sendAction(type, payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  socket.send(JSON.stringify({ type, payload }));
}

function issueProduction(unitType) {
  sendAction("spawn_unit", { unit_type: unitType });
}

function issueMove(target) {
  if (!selectedUnits.size) {
    return;
  }
  sendAction("command_move", { unit_ids: Array.from(selectedUnits), target });
}

function issueRally(target) {
  sendAction("set_rally", { target });
}

function worldPositionFromEvent(event) {
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * MAP_WIDTH;
  const y = ((event.clientY - rect.top) / rect.height) * MAP_HEIGHT;
  return { x, y };
}

function nearestUnit(position, ownerId) {
  if (!latestState) {
    return null;
  }
  let closest = null;
  let closestDistance = Infinity;
  for (const unit of latestState.units) {
    if (ownerId && unit.owner_id !== ownerId) {
      continue;
    }
    const dx = unit.position.x - position.x;
    const dy = unit.position.y - position.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance < closestDistance && distance < 3) {
      closest = unit;
      closestDistance = distance;
    }
  }
  return closest;
}

function handleCanvasClick(event) {
  const worldPos = worldPositionFromEvent(event);
  if (rallyMode) {
    rallyMode = false;
    issueRally(worldPos);
    logEvent(`Rally point set to (${worldPos.x.toFixed(1)}, ${worldPos.y.toFixed(1)})`);
    return;
  }
  const unit = nearestUnit(worldPos, localPlayerId);
  selectedUnits.clear();
  if (unit) {
    selectedUnits.add(unit.id);
  }
}

function handleCanvasContextMenu(event) {
  event.preventDefault();
  const worldPos = worldPositionFromEvent(event);
  issueMove(worldPos);
}

function handleRallyButton() {
  rallyMode = true;
  logEvent("Click anywhere on the battlefield to set a rally point.");
}

function updateUI() {
  if (!latestState) {
    return;
  }
  render();
  updatePlayers();
  const player = latestState.players.find((p) => p.id === localPlayerId);
  if (player) {
    playerNameEl.textContent = `${player.name}`;
    playerCreditsEl.textContent = `${player.credits} credits (+${player.income_per_tick})`;
  }
}

function updatePlayers() {
  playerListEl.innerHTML = "";
  for (const player of latestState.players) {
    const li = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = player.color;
    li.appendChild(swatch);
    const text = document.createElement("span");
    text.textContent = `${player.name} — ${player.credits} cr`;
    if (!player.is_active) {
      text.textContent += " (defeated)";
      text.style.opacity = 0.6;
    }
    li.appendChild(text);
    playerListEl.appendChild(li);
  }
}

function processEvents(events) {
  for (const event of events) {
    switch (event.type) {
      case "unit_spawned":
        logEvent(`Unit deployed by ${resolvePlayerName(event.unit.owner_id)}.`);
        break;
      case "unit_destroyed":
        logEvent("A unit was destroyed.");
        break;
      case "structure_destroyed":
        logEvent("A base has fallen!");
        break;
      case "match_over":
        logEvent(`Match complete. ${resolvePlayerName(event.winner)} stands victorious.`);
        break;
      default:
        break;
    }
  }
}

function resolvePlayerName(playerId) {
  if (!latestState) {
    return "Unknown";
  }
  const player = latestState.players.find((p) => p.id === playerId);
  return player ? player.name : "Unknown";
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  renderGrid();
  renderStructures();
  renderUnits();
  renderSelection();
}

function renderGrid() {
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= MAP_WIDTH; x++) {
    ctx.beginPath();
    ctx.moveTo(x * SCALE_X, 0);
    ctx.lineTo(x * SCALE_X, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= MAP_HEIGHT; y++) {
    ctx.beginPath();
    ctx.moveTo(0, y * SCALE_Y);
    ctx.lineTo(canvas.width, y * SCALE_Y);
    ctx.stroke();
  }
}

function renderStructures() {
  if (!latestState) {
    return;
  }
  for (const structure of latestState.structures) {
    const player = latestState.players.find((p) => p.id === structure.owner_id);
    ctx.fillStyle = player ? player.color : "#888";
    const x = structure.position.x * SCALE_X;
    const y = structure.position.y * SCALE_Y;
    const size = 40;
    ctx.fillRect(x - size / 2, y - size / 2, size, size);
    ctx.strokeStyle = "rgba(0,0,0,0.6)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x - size / 2, y - size / 2, size, size);
    drawHealthBar(x, y - size / 2 - 8, structure.hp / 1500);
  }
}

function renderUnits() {
  if (!latestState) {
    return;
  }
  for (const unit of latestState.units) {
    const player = latestState.players.find((p) => p.id === unit.owner_id);
    ctx.fillStyle = player ? player.color : "#ccc";
    const x = unit.position.x * SCALE_X;
    const y = unit.position.y * SCALE_Y;
    ctx.beginPath();
    ctx.arc(x, y, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(0,0,0,0.5)";
    ctx.stroke();
    drawHealthBar(x, y - 12, unit.hp / healthForUnit(unit.unit_type));
  }
}

function renderSelection() {
  if (!latestState || !selectedUnits.size) {
    return;
  }
  ctx.strokeStyle = "#ffeaa7";
  ctx.lineWidth = 2;
  for (const unitId of selectedUnits) {
    const unit = latestState.units.find((u) => u.id === unitId);
    if (!unit) continue;
    const x = unit.position.x * SCALE_X;
    const y = unit.position.y * SCALE_Y;
    ctx.beginPath();
    ctx.arc(x, y, 12, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawHealthBar(x, y, ratio) {
  const width = 30;
  const height = 4;
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.fillRect(x - width / 2, y, width, height);
  ctx.fillStyle = ratio > 0.5 ? "#55efc4" : ratio > 0.25 ? "#ffeaa7" : "#ff7675";
  ctx.fillRect(x - width / 2, y, width * Math.max(0, Math.min(1, ratio)), height);
}

function healthForUnit(unitType) {
  switch (unitType) {
    case "tank":
      return 320;
    case "rocketeer":
      return 90;
    default:
      return 120;
  }
}

function logEvent(message) {
  const entry = document.createElement("p");
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  eventLogEl.appendChild(entry);
  while (eventLogEl.children.length > 80) {
    eventLogEl.removeChild(eventLogEl.firstChild);
  }
  eventLogEl.scrollTop = eventLogEl.scrollHeight;
}

connect();

productionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    issueProduction(button.dataset.unit);
  });
});

canvas.addEventListener("click", handleCanvasClick);
canvas.addEventListener("contextmenu", handleCanvasContextMenu);
rallyButton.addEventListener("click", handleRallyButton);

function animationLoop() {
  render();
  requestAnimationFrame(animationLoop);
}

requestAnimationFrame(animationLoop);
