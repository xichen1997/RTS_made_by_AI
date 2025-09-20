const canvas = document.getElementById("battlefield");
const ctx = canvas.getContext("2d");
const connectBtn = document.getElementById("connect-btn");
const roomInput = document.getElementById("room-input");
const nameInput = document.getElementById("name-input");
const statusLabel = document.getElementById("status-indicator");
const resourceDisplay = document.getElementById("resource-display");
const eventLog = document.getElementById("event-log");
const tooltip = document.getElementById("tooltip");
const productionButtons = document.querySelectorAll("[data-unit]");

let socket = null;
let playerId = null;
let roomId = roomInput.value;
let playerColor = "#ffffff";
let gameState = null;
let selectedUnits = new Set();
let selectedBuilding = null;
let mapSize = [96, 64];
let lastHover = null;

const COLORS = {
  grid: "#0f172a",
  enemy: "#ef4444",
  neutral: "#facc15",
  selection: "#38bdf8",
};

connectBtn.addEventListener("click", () => {
  if (socket) {
    socket.close();
  }
  roomId = roomInput.value.trim() || "alpha";
  const name = nameInput.value.trim() || `Commander-${Math.floor(Math.random() * 999)}`;
  openSocket(roomId, name);
});

productionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      pushEvent("Connect to a room before issuing production commands.");
      return;
    }
    if (!selectedBuilding) {
      pushEvent("Select your HQ or Factory to train units.");
      return;
    }
    const unitType = button.dataset.unit;
    sendCommand({
      action: "build_unit",
      building_id: selectedBuilding,
      unit_type: unitType,
    });
  });
});

canvas.addEventListener("contextmenu", (event) => event.preventDefault());
canvas.addEventListener("mousedown", (event) => {
  if (!gameState) {
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * mapSize[0];
  const y = ((event.clientY - rect.top) / rect.height) * mapSize[1];

  if (event.button === 0) {
    handleSelection(x, y, event.shiftKey);
  } else if (event.button === 2) {
    handleCommand(x, y);
  }
});

canvas.addEventListener("mousemove", (event) => {
  if (!gameState) return;
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * mapSize[0];
  const y = ((event.clientY - rect.top) / rect.height) * mapSize[1];
  const hoverInfo = pickEntity(x, y);
  if (hoverInfo && hoverInfo.id !== lastHover) {
    tooltip.textContent = hoverInfo.label;
    tooltip.style.opacity = 1;
    lastHover = hoverInfo.id;
  } else if (!hoverInfo) {
    tooltip.style.opacity = 0;
    lastHover = null;
  }
});

function openSocket(room, name) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/ws/${room}`;
  socket = new WebSocket(url);
  statusLabel.textContent = "Connecting…";

  socket.addEventListener("open", () => {
    statusLabel.textContent = "Connected";
    socket.send(JSON.stringify({ type: "join", player_name: name }));
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "welcome") {
      playerId = message.player_id;
      pushEvent(`Welcome commander ${message.player_name}.`);
    } else if (message.type === "state") {
      gameState = message.state;
      mapSize = message.state.map_size;
      const player = gameState.players[playerId];
      if (player) {
        resourceDisplay.textContent = `Credits: ${player.credits}`;
        playerColor = player.color;
      }
      const existingUnits = new Set(gameState.units.map((unit) => unit.id));
      selectedUnits.forEach((id) => {
        if (!existingUnits.has(id)) {
          selectedUnits.delete(id);
        }
      });
      if (!gameState.buildings.some((b) => b.id === selectedBuilding)) {
        selectedBuilding = null;
      }
      updateEventLog(gameState.events || []);
      draw();
    } else if (message.type === "event") {
      pushEvent(message.message);
    }
  });

  socket.addEventListener("close", () => {
    statusLabel.textContent = "Disconnected";
    pushEvent("Connection closed.");
    playerId = null;
    selectedUnits.clear();
    selectedBuilding = null;
  });
}

function sendCommand(command) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ type: "command", command }));
}

function handleSelection(x, y, additive) {
  const picked = pickEntity(x, y);
  if (!additive) {
    selectedUnits.clear();
    selectedBuilding = null;
  }
  if (!picked) {
    return;
  }
  if (picked.owner === playerId && picked.kind === "unit") {
    if (selectedUnits.has(picked.id)) {
      selectedUnits.delete(picked.id);
    } else {
      selectedUnits.add(picked.id);
    }
  } else if (picked.owner === playerId && picked.kind === "building") {
    selectedBuilding = picked.id;
  }
}

function handleCommand(x, y) {
  if (selectedUnits.size === 0) {
    return;
  }
  const target = pickEntity(x, y);
  const unitIds = Array.from(selectedUnits);
  if (target) {
    if (target.kind === "resource") {
      sendCommand({
        action: "harvest",
        unit_ids: unitIds,
        resource_id: target.id,
      });
      return;
    }
    if (target.owner && target.owner !== playerId) {
      sendCommand({
        action: "attack",
        unit_ids: unitIds,
        target_id: target.id,
      });
      return;
    }
  }
  sendCommand({
    action: "move",
    unit_ids: unitIds,
    position: { x, y },
  });
}

function pickEntity(x, y) {
  if (!gameState) return null;
  const threshold = 2.5;
  // Units
  for (const unit of gameState.units) {
    const dx = unit.position[0] - x;
    const dy = unit.position[1] - y;
    if (Math.hypot(dx, dy) < threshold) {
      return {
        id: unit.id,
        owner: unit.owner,
        label: `${unit.type.toUpperCase()} (${unit.hp}/${unit.max_hp})`,
        kind: "unit",
      };
    }
  }
  // Buildings
  for (const building of gameState.buildings) {
    const [bx, by] = building.position;
    const size = 4;
    if (x >= bx - size && x <= bx + size && y >= by - size && y <= by + size) {
      return {
        id: building.id,
        owner: building.owner,
        label: `${building.type.toUpperCase()} (${building.hp}/${building.max_hp})`,
        kind: "building",
      };
    }
  }
  // Resources
  for (const resource of gameState.resources) {
    const dx = resource.position[0] - x;
    const dy = resource.position[1] - y;
    if (Math.hypot(dx, dy) < threshold + 1.5) {
      return {
        id: resource.id,
        owner: null,
        label: `Resource Field (${resource.remaining.toFixed(0)} credits)`,
        kind: "resource",
      };
    }
  }
  return null;
}

function draw() {
  if (!gameState) {
    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    return;
  }
  const [mapWidth, mapHeight] = mapSize;
  const sx = canvas.width / mapWidth;
  const sy = canvas.height / mapHeight;

  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Grid
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let gx = 0; gx <= mapWidth; gx += 4) {
    ctx.beginPath();
    ctx.moveTo(gx * sx, 0);
    ctx.lineTo(gx * sx, canvas.height);
    ctx.stroke();
  }
  for (let gy = 0; gy <= mapHeight; gy += 4) {
    ctx.beginPath();
    ctx.moveTo(0, gy * sy);
    ctx.lineTo(canvas.width, gy * sy);
    ctx.stroke();
  }

  // Resources
  for (const resource of gameState.resources) {
    ctx.fillStyle = COLORS.neutral;
    const [rx, ry] = resource.position;
    ctx.beginPath();
    ctx.arc(rx * sx, ry * sy, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  // Buildings
  for (const building of gameState.buildings) {
    const [bx, by] = building.position;
    const color = getPlayerColor(building.owner);
    const width = 12;
    const height = 12;
    ctx.fillStyle = color;
    ctx.fillRect(bx * sx - width / 2, by * sy - height / 2, width, height);
    if (selectedBuilding === building.id) {
      ctx.strokeStyle = COLORS.selection;
      ctx.lineWidth = 3;
      ctx.strokeRect(bx * sx - width / 2 - 3, by * sy - height / 2 - 3, width + 6, height + 6);
    }
  }

  // Units
  for (const unit of gameState.units) {
    const [ux, uy] = unit.position;
    const radius = unit.type === "tank" ? 6 : 4;
    ctx.fillStyle = getPlayerColor(unit.owner);
    ctx.beginPath();
    ctx.arc(ux * sx, uy * sy, radius, 0, Math.PI * 2);
    ctx.fill();
    if (selectedUnits.has(unit.id)) {
      ctx.strokeStyle = COLORS.selection;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(ux * sx, uy * sy, radius + 3, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

function getPlayerColor(owner) {
  if (!owner) return COLORS.enemy;
  if (!gameState) return playerColor;
  const player = gameState.players[owner];
  if (!player) return COLORS.enemy;
  return player.color || COLORS.enemy;
}

function pushEvent(message) {
  const entry = document.createElement("div");
  entry.className = "entry";
  entry.textContent = message;
  eventLog.prepend(entry);
  while (eventLog.children.length > 40) {
    eventLog.removeChild(eventLog.lastChild);
  }
}

function updateEventLog(events) {
  if (!events || events.length === 0) return;
  events.forEach((message) => pushEvent(message));
}

// Kick off a render so the canvas isn't blank before joining.
draw();
