const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const spawnButton = document.getElementById("spawnButton");
const regenerateButton = document.getElementById("regenerateButton");
const seedInput = document.getElementById("seedInput");
const debugPanel = document.getElementById("debugPanel");

let mapData = null;
let tileSize = 4;
let offsetX = 0;
let offsetY = 0;
let spawnMode = false;
let lastFrameTime = performance.now();
let lastDebugUpdate = 0;

const units = [];
let selectedUnitId = null;

class Unit {
  static nextId = 1;

  constructor(x, y) {
    this.id = Unit.nextId++;
    this.x = x;
    this.y = y;
    this.targetX = x;
    this.targetY = y;
    this.speed = 6; // tiles per second
  }

  setTarget(tileX, tileY) {
    this.targetX = tileX;
    this.targetY = tileY;
  }

  update(deltaSeconds) {
    const dx = this.targetX - this.x;
    const dy = this.targetY - this.y;
    const distance = Math.hypot(dx, dy);
    if (distance < 1e-3) {
      this.x = this.targetX;
      this.y = this.targetY;
      return;
    }

    const step = this.speed * deltaSeconds;
    if (step >= distance) {
      this.x = this.targetX;
      this.y = this.targetY;
      return;
    }

    this.x += (dx / distance) * step;
    this.y += (dy / distance) * step;
  }

  toDebug() {
    return {
      id: this.id,
      position: {
        x: Number(this.x.toFixed(2)),
        y: Number(this.y.toFixed(2)),
      },
      target: {
        x: Number(this.targetX.toFixed(2)),
        y: Number(this.targetY.toFixed(2)),
      },
      selected: this.id === selectedUnitId,
    };
  }
}

function configureCanvas(metadata) {
  const maxTileWidth = Math.floor(canvas.width / metadata.width);
  const maxTileHeight = Math.floor(canvas.height / metadata.height);
  tileSize = Math.max(2, Math.min(maxTileWidth, maxTileHeight));

  const mapWidthPx = metadata.width * tileSize;
  const mapHeightPx = metadata.height * tileSize;
  offsetX = Math.floor((canvas.width - mapWidthPx) / 2);
  offsetY = Math.floor((canvas.height - mapHeightPx) / 2);
}

function tileTopLeftToCanvas(tileX, tileY) {
  return {
    x: offsetX + tileX * tileSize,
    y: offsetY + tileY * tileSize,
  };
}

function worldToCanvas(worldX, worldY) {
  return {
    x: offsetX + worldX * tileSize,
    y: offsetY + worldY * tileSize,
  };
}

function canvasToTile(event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const canvasX = (event.clientX - rect.left) * scaleX - offsetX;
  const canvasY = (event.clientY - rect.top) * scaleY - offsetY;
  return {
    tileX: Math.floor(canvasX / tileSize),
    tileY: Math.floor(canvasY / tileSize),
    rawX: canvasX / tileSize,
    rawY: canvasY / tileSize,
  };
}

function findUnitAt(tileX, tileY) {
  const targetX = tileX + 0.5;
  const targetY = tileY + 0.5;
  return units.find(
    (unit) => Math.hypot(unit.x - targetX, unit.y - targetY) < 0.5
  );
}

function spawnUnit(tileX, tileY) {
  const unit = new Unit(tileX + 0.5, tileY + 0.5);
  units.push(unit);
  selectedUnitId = unit.id;
  updateDebugPanel(true);
}

function setSpawnMode(enabled) {
  spawnMode = enabled;
  spawnButton.classList.toggle("is-active", spawnMode);
}

function handleCanvasClick(event) {
  if (!mapData) {
    return;
  }

  const { tileX, tileY } = canvasToTile(event);
  if (
    tileX < 0 ||
    tileY < 0 ||
    tileX >= mapData.width ||
    tileY >= mapData.height
  ) {
    return;
  }

  if (spawnMode) {
    spawnUnit(tileX, tileY);
    setSpawnMode(false);
    return;
  }

  const clickedUnit = findUnitAt(tileX, tileY);
  if (clickedUnit) {
    selectedUnitId = clickedUnit.id;
    updateDebugPanel(true);
    return;
  }

  if (selectedUnitId !== null) {
    const unit = units.find((u) => u.id === selectedUnitId);
    if (unit) {
      unit.setTarget(tileX + 0.5, tileY + 0.5);
      updateDebugPanel(true);
    }
  }
}

async function fetchMap(seed) {
  const url = seed ? `/api/map?seed=${seed}` : "/api/map";
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load map: ${response.status}`);
  }
  return response.json();
}

async function regenerateMap() {
  const seedValue = seedInput.value.trim();
  const payload = {};
  if (seedValue !== "") {
    payload.seed = Number(seedValue);
  }

  const response = await fetch("/api/map/regenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorMessage = await response.text();
    throw new Error(`Failed to regenerate map: ${errorMessage}`);
  }

  return response.json();
}

function drawMap() {
  if (!mapData) {
    return;
  }

  const { tiles, colours, width, height } = mapData;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const terrain = tiles[y][x];
      ctx.fillStyle = colours[terrain] ?? "#000";
      const { x: drawX, y: drawY } = tileTopLeftToCanvas(x, y);
      ctx.fillRect(drawX, drawY, tileSize + 1, tileSize + 1);
    }
  }
}

function drawUnits() {
  for (const unit of units) {
    const { x, y } = worldToCanvas(unit.x, unit.y);
    const radius = Math.max(4, tileSize * 0.35);
    ctx.beginPath();
    ctx.fillStyle = "#facc15";
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    if (unit.id === selectedUnitId) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#f87171";
      ctx.beginPath();
      ctx.arc(x, y, radius + 3, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (Math.abs(unit.targetX - unit.x) > 0.01 || Math.abs(unit.targetY - unit.y) > 0.01) {
      const target = worldToCanvas(unit.targetX, unit.targetY);
      ctx.strokeStyle = "rgba(250, 204, 21, 0.65)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();

      ctx.fillStyle = "rgba(34, 197, 94, 0.75)";
      ctx.beginPath();
      ctx.arc(target.x, target.y, radius * 0.6, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawScene() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawMap();
  drawUnits();
}

function updateUnits(deltaSeconds) {
  for (const unit of units) {
    unit.update(deltaSeconds);
  }
}

function updateDebugPanel(force = false) {
  const now = performance.now();
  if (!force && now - lastDebugUpdate < 200) {
    return;
  }
  lastDebugUpdate = now;

  const debugData = {
    seed: mapData?.seed ?? "n/a",
    units: units.map((unit) => unit.toDebug()),
  };
  debugPanel.textContent = JSON.stringify(debugData, null, 2);
}

function loop(now) {
  const deltaSeconds = Math.min((now - lastFrameTime) / 1000, 0.1);
  lastFrameTime = now;
  updateUnits(deltaSeconds);
  drawScene();
  updateDebugPanel();
  requestAnimationFrame(loop);
}

async function initialise() {
  try {
    mapData = await fetchMap();
    configureCanvas(mapData);
    drawScene();
    requestAnimationFrame(loop);
  } catch (error) {
    console.error(error);
    debugPanel.textContent = `Failed to start game: ${error.message}`;
  }
}

spawnButton.addEventListener("click", () => {
  setSpawnMode(!spawnMode);
});

regenerateButton.addEventListener("click", async () => {
  try {
    mapData = await regenerateMap();
    configureCanvas(mapData);
    units.length = 0;
    selectedUnitId = null;
    setSpawnMode(false);
    drawScene();
    updateDebugPanel(true);
  } catch (error) {
    console.error(error);
    debugPanel.textContent = `Failed to regenerate map: ${error.message}`;
  }
});

canvas.addEventListener("click", handleCanvasClick);

initialise();
