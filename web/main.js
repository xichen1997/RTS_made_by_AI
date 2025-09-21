const canvas = document.getElementById("battlefield");
const ctx = canvas.getContext("2d");
const connectBtn = document.getElementById("connect-btn");
const roomInput = document.getElementById("room-input");
const nameInput = document.getElementById("name-input");
const statusLabel = document.getElementById("status-indicator");
const resourceDisplay = document.getElementById("resource-display");
const eventLog = document.getElementById("event-log");
const tooltip = document.getElementById("tooltip");
const productionButtonsContainer = document.getElementById("production-buttons");
const productionHint = document.getElementById("production-hint");

let socket = null;
let playerId = null;
let roomId = roomInput.value;
let playerColor = "#ffffff";
let gameState = null;
let selectedUnits = new Set();
let selectedBuilding = null; // { id: string, type: string } | null
let mapSize = [160, 120];
let lastHover = null;
let deviceRatio = 1;
let scaleX = 1;
let scaleY = 1;

const units = new Map();
const buildings = new Map();
const resources = new Map();

const selectionColor = "#38bdf8";

const COLORS = {
  enemy: "#ef4444",
  neutral: "#facc15",
};

const BASE_PRODUCTION_HINT = productionHint ? productionHint.textContent : "";

const PRODUCTION_LABELS = {
  engineer: "Mobilize Engineer",
  ore_miner: "Deploy Ore Miner",
  conscript: "Train Conscript",
  gi: "Deploy GI",
  rocketeer: "Launch Rocketeer",
  grizzly_tank: "Build Grizzly Tank",
  ifv: "Assemble IFV",
  mirage_tank: "Deploy Mirage Tank",
  prism_tank: "Construct Prism Tank",
};

initializeCanvas();
resizeRendererToDisplaySize();
animate();
renderProductionButtons(null);

connectBtn.addEventListener("click", () => {
  if (socket) {
    socket.close();
  }
  roomId = roomInput.value.trim() || "alpha";
  const name = nameInput.value.trim() || `Commander-${Math.floor(Math.random() * 999)}`;
  openSocket(roomId, name);
});

canvas.addEventListener("contextmenu", (event) => event.preventDefault());

canvas.addEventListener("mousedown", (event) => {
  if (!gameState) {
    return;
  }
  const picked = pickEntityAtEvent(event);
  if (event.button === 0) {
    handleSelection(picked, event.shiftKey);
  } else if (event.button === 2) {
    const groundPoint = getGroundPoint(event);
    handleCommand(picked, groundPoint);
  }
});

canvas.addEventListener("mousemove", (event) => {
  if (!gameState) return;
  const hovered = pickEntityAtEvent(event);
  if (hovered && hovered.id !== lastHover) {
    tooltip.textContent = hovered.label;
    tooltip.style.opacity = 1;
    lastHover = hovered.id;
  } else if (!hovered) {
    tooltip.style.opacity = 0;
    lastHover = null;
  }
});

canvas.addEventListener("mouseleave", () => {
  tooltip.style.opacity = 0;
  lastHover = null;
});

window.addEventListener("resize", () => {
  resizeRendererToDisplaySize();
});

function animate() {
  requestAnimationFrame(animate);
  drawScene();
}

function initializeCanvas() {
  if (!ctx) {
    throw new Error("Unable to acquire 2D rendering context for battlefield canvas.");
  }
  ctx.imageSmoothingEnabled = true;
}

function resizeRendererToDisplaySize() {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(Math.floor(rect.width), 1);
  const height = Math.max(Math.floor(rect.height), 1);
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
  }
  deviceRatio = ratio;
  ctx.setTransform(deviceRatio, 0, 0, deviceRatio, 0, 0);
  scaleX = width / mapSize[0];
  scaleY = height / mapSize[1];
}

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
      const incomingSize = message.state.map_size;
      if (incomingSize[0] !== mapSize[0] || incomingSize[1] !== mapSize[1]) {
        mapSize = incomingSize;
        resizeRendererToDisplaySize();
      } else {
        mapSize = incomingSize;
      }
      gameState = message.state;
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
      if (selectedBuilding) {
        const matching = gameState.buildings.find(
          (building) => building.id === selectedBuilding.id,
        );
        if (!matching) {
          selectedBuilding = null;
          renderProductionButtons(null);
        } else {
          selectedBuilding.type = matching.type;
          renderProductionButtons(selectedBuilding);
        }
      }
      updateEventLog(gameState.events || []);
      syncScene();
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
    renderProductionButtons(null);
  });
}

function sendCommand(command) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ type: "command", command }));
}

function handleSelection(picked, additive) {
  if (!additive) {
    selectedUnits.clear();
    selectedBuilding = null;
  }
  if (!picked) {
    renderProductionButtons(selectedBuilding);
    return;
  }
  if (picked.owner === playerId && picked.kind === "unit") {
    if (selectedUnits.has(picked.id)) {
      selectedUnits.delete(picked.id);
    } else {
      selectedUnits.add(picked.id);
    }
  } else if (picked.owner === playerId && picked.kind === "building") {
    if (selectedBuilding && selectedBuilding.id === picked.id && additive) {
      selectedBuilding = null;
    } else {
      selectedBuilding = { id: picked.id, type: picked.type };
    }
  } else if (!additive) {
    selectedUnits.clear();
    selectedBuilding = null;
  }
  renderProductionButtons(selectedBuilding);
}

function handleCommand(target, groundPoint) {
  if (selectedUnits.size === 0) {
    return;
  }
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
  if (groundPoint) {
    sendCommand({
      action: "move",
      unit_ids: unitIds,
      position: { x: groundPoint.x, y: groundPoint.y },
    });
  }
}

function renderProductionButtons(selection) {
  if (!productionButtonsContainer || !productionHint) return;
  productionButtonsContainer.innerHTML = "";
  if (!selection) {
    productionHint.textContent = BASE_PRODUCTION_HINT;
    return;
  }
  if (!gameState) {
    productionHint.textContent = "Connect to a room before queuing production.";
    return;
  }
  const buildingData = gameState.buildings.find((building) => building.id === selection.id);
  if (!buildingData) {
    productionHint.textContent = BASE_PRODUCTION_HINT;
    return;
  }
  const buildableUnits = buildingData.buildable_units || [];
  if (buildableUnits.length === 0) {
    productionHint.textContent = `${formatLabel(buildingData.type)} cannot produce units.`;
    return;
  }
  productionHint.textContent = `Queue units at ${formatLabel(buildingData.type)}.`;
  for (const unitType of buildableUnits) {
    const label = PRODUCTION_LABELS[unitType] || `Train ${formatLabel(unitType)}`;
    const button = document.createElement("button");
    button.textContent = label;
    button.addEventListener("click", () => {
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        pushEvent("Connect to a room before issuing production commands.");
        return;
      }
      if (!selectedBuilding) {
        pushEvent("Select a production structure before queuing units.");
        return;
      }
      sendCommand({
        action: "build_unit",
        building_id: selectedBuilding.id,
        unit_type: unitType,
      });
    });
    productionButtonsContainer.appendChild(button);
  }
  if (buildingData.queue && buildingData.queue.length > 0) {
    const queueIndicator = document.createElement("div");
    queueIndicator.className = "queue-indicator";
    queueIndicator.textContent = `In queue: ${buildingData.queue
      .map((queued) => formatLabel(queued))
      .join(", ")}`;
    productionButtonsContainer.appendChild(queueIndicator);
  }
}

function pickEntityAtEvent(event) {
  const point = screenToWorld(event.clientX, event.clientY);
  if (!point) {
    return null;
  }
  return pickEntityAtPoint(point);
}

function getGroundPoint(event) {
  return screenToWorld(event.clientX, event.clientY);
}

function screenToWorld(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    return null;
  }
  const ratioX = (clientX - rect.left) / rect.width;
  const ratioY = (clientY - rect.top) / rect.height;
  return {
    x: clamp(ratioX * mapSize[0], 0, mapSize[0]),
    y: clamp(ratioY * mapSize[1], 0, mapSize[1]),
  };
}

function pickEntityAtPoint(point) {
  let candidate = null;
  let bestScore = Infinity;

  for (const building of buildings.values()) {
    const score = distanceToBuilding(point, building);
    if (score < bestScore) {
      bestScore = score;
      candidate = {
        id: building.id,
        owner: building.owner,
        kind: "building",
        type: building.type,
        label: `${formatLabel(building.type)} (${building.hp}/${building.maxHp})`,
      };
    }
  }

  for (const unit of units.values()) {
    const score = distanceToUnit(point, unit);
    if (score < bestScore) {
      bestScore = score;
      candidate = {
        id: unit.id,
        owner: unit.owner,
        kind: "unit",
        type: unit.type,
        label: `${formatLabel(unit.type)} (${unit.hp}/${unit.maxHp})`,
      };
    }
  }

  for (const resource of resources.values()) {
    const score = distanceToResource(point, resource);
    if (score < bestScore) {
      bestScore = score;
      candidate = {
        id: resource.id,
        owner: null,
        kind: "resource",
        type: "resource",
        label: `Resource Field (${resource.remaining.toFixed(0)} credits)`,
      };
    }
  }

  if (bestScore === Infinity || bestScore > 0.8) {
    return null;
  }
  return candidate;
}

function distanceToUnit(point, unit) {
  const dx = point.x - unit.x;
  const dy = point.y - unit.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const radius = unit.radius;
  return Math.max(0, dist - radius);
}

function distanceToBuilding(point, building) {
  const halfW = building.width / 2;
  const halfD = building.depth / 2;
  const dx = Math.abs(point.x - building.x) - halfW;
  const dy = Math.abs(point.y - building.y) - halfD;
  const clampedX = Math.max(dx, 0);
  const clampedY = Math.max(dy, 0);
  const outsideDist = Math.sqrt(clampedX * clampedX + clampedY * clampedY);
  const insideDist = Math.max(dx, dy);
  return dx <= 0 && dy <= 0 ? Math.max(insideDist, 0) : outsideDist;
}

function distanceToResource(point, resource) {
  const dx = point.x - resource.x;
  const dy = point.y - resource.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const radius = resource.radius ?? 3.0;
  return Math.max(0, dist - radius);
}

function syncScene() {
  if (!gameState) return;

  const seenUnits = new Set();
  for (const unit of gameState.units) {
    const [ux, uy] = unit.position;
    const dimensions = getUnitDimensions(unit.type);
    units.set(unit.id, {
      id: unit.id,
      owner: unit.owner,
      type: unit.type,
      x: ux,
      y: uy,
      hp: unit.hp,
      maxHp: unit.max_hp,
      radius: dimensions.radius,
    });
    seenUnits.add(unit.id);
  }
  for (const id of Array.from(units.keys())) {
    if (!seenUnits.has(id)) {
      units.delete(id);
    }
  }

  const seenBuildings = new Set();
  for (const building of gameState.buildings) {
    const [bx, by] = building.position;
    const dims = getBuildingDimensions(building.type);
    buildings.set(building.id, {
      id: building.id,
      owner: building.owner,
      type: building.type,
      x: bx,
      y: by,
      hp: building.hp,
      maxHp: building.max_hp,
      width: dims.width,
      depth: dims.depth,
      queue: building.queue || [],
    });
    seenBuildings.add(building.id);
  }
  for (const id of Array.from(buildings.keys())) {
    if (!seenBuildings.has(id)) {
      buildings.delete(id);
    }
  }

  const seenResources = new Set();
  for (const resource of gameState.resources) {
    const [rx, ry] = resource.position;
    resources.set(resource.id, {
      id: resource.id,
      x: rx,
      y: ry,
      remaining: resource.remaining,
      radius: 3.0,
    });
    seenResources.add(resource.id);
  }
  for (const id of Array.from(resources.keys())) {
    if (!seenResources.has(id)) {
      resources.delete(id);
    }
  }
}

function drawScene() {
  if (!ctx) return;
  resizeRendererToDisplaySize();
  const width = canvas.width / deviceRatio;
  const height = canvas.height / deviceRatio;

  ctx.save();
  ctx.setTransform(deviceRatio, 0, 0, deviceRatio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  drawBackground(width, height);
  drawGrid(width, height);
  drawResources();
  drawBuildings();
  drawUnits();
  ctx.restore();
}

function drawBackground(width, height) {
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, width, height);
}

function drawGrid(width, height) {
  ctx.strokeStyle = "rgba(15, 23, 42, 0.35)";
  ctx.lineWidth = 1;
  const stepX = Math.max(mapSize[0] / 16, 5);
  const stepY = Math.max(mapSize[1] / 12, 5);
  ctx.beginPath();
  for (let x = stepX; x < mapSize[0]; x += stepX) {
    const sx = x * scaleX;
    ctx.moveTo(sx, 0);
    ctx.lineTo(sx, height);
  }
  for (let y = stepY; y < mapSize[1]; y += stepY) {
    const sy = y * scaleY;
    ctx.moveTo(0, sy);
    ctx.lineTo(width, sy);
  }
  ctx.stroke();
}

function drawResources() {
  for (const resource of resources.values()) {
    const { x, y } = worldToScreen(resource.x, resource.y);
    const radius = resource.radius * ((scaleX + scaleY) / 2);
    ctx.beginPath();
    ctx.fillStyle = COLORS.neutral;
    ctx.globalAlpha = 0.8;
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }
}

function drawBuildings() {
  for (const building of buildings.values()) {
    const halfW = (building.width / 2) * scaleX;
    const halfD = (building.depth / 2) * scaleY;
    const { x, y } = worldToScreen(building.x, building.y);
    ctx.fillStyle = getPlayerColor(building.owner);
    ctx.globalAlpha = 0.9;
    ctx.fillRect(x - halfW, y - halfD, halfW * 2, halfD * 2);
    ctx.globalAlpha = 1;

    ctx.strokeStyle = "rgba(0,0,0,0.35)";
    ctx.strokeRect(x - halfW, y - halfD, halfW * 2, halfD * 2);

    if (selectedBuilding && selectedBuilding.id === building.id) {
      ctx.strokeStyle = selectionColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(x - halfW - 2, y - halfD - 2, halfW * 2 + 4, halfD * 2 + 4);
    }

    drawHealthBar(x - halfW, y - halfD - 6, halfW * 2, building.hp, building.maxHp);
  }
}

function drawUnits() {
  for (const unit of units.values()) {
    const { x, y } = worldToScreen(unit.x, unit.y);
    const radius = unit.radius * ((scaleX + scaleY) / 2);
    ctx.beginPath();
    ctx.fillStyle = getPlayerColor(unit.owner);
    ctx.globalAlpha = 0.95;
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    if (selectedUnits.has(unit.id)) {
      ctx.beginPath();
      ctx.strokeStyle = selectionColor;
      ctx.lineWidth = 2;
      ctx.arc(x, y, radius + 3, 0, Math.PI * 2);
      ctx.stroke();
    }

    drawHealthBar(x - radius, y + radius + 4, radius * 2, unit.hp, unit.maxHp);
  }
}

function drawHealthBar(x, y, width, hp, maxHp) {
  const height = 4;
  ctx.fillStyle = "rgba(15,23,42,0.8)";
  ctx.fillRect(x, y, width, height);
  const ratio = maxHp > 0 ? clamp(hp / maxHp, 0, 1) : 0;
  ctx.fillStyle = ratio > 0.5 ? "#22c55e" : ratio > 0.25 ? "#fbbf24" : "#ef4444";
  ctx.fillRect(x, y, width * ratio, height);
}

function worldToScreen(x, y) {
  return {
    x: x * scaleX,
    y: y * scaleY,
  };
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function getPlayerColor(owner) {
  if (!owner) return COLORS.enemy;
  if (!gameState) return playerColor;
  const player = gameState.players[owner];
  if (!player) return COLORS.enemy;
  return player.color || COLORS.enemy;
}

function formatLabel(identifier) {
  if (!identifier) return "";
  return identifier
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getUnitDimensions(type) {
  switch (type) {
    case "ore_miner":
      return { radius: 3.2, height: 3.0 };
    case "grizzly_tank":
    case "mirage_tank":
      return { radius: 3.0, height: 2.6 };
    case "prism_tank":
      return { radius: 3.2, height: 2.8 };
    case "ifv":
      return { radius: 2.4, height: 2.2 };
    case "gi":
      return { radius: 1.3, height: 2.0 };
    case "rocketeer":
      return { radius: 1.2, height: 2.2 };
    case "conscript":
    case "engineer":
      return { radius: 1.1, height: 1.8 };
    default:
      return { radius: 1.6, height: 1.8 };
  }
}

function getBuildingDimensions(type) {
  switch (type) {
    case "construction_yard":
      return { width: 12, depth: 12 };
    case "war_factory":
      return { width: 14, depth: 10 };
    case "barracks":
      return { width: 9, depth: 9 };
    case "ore_refinery":
      return { width: 10, depth: 10 };
    case "power_plant":
      return { width: 8, depth: 8 };
    case "airforce_command":
      return { width: 11, depth: 11 };
    case "prism_tower":
      return { width: 4, depth: 4 };
    default:
      return { width: 8, depth: 8 };
  }
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
