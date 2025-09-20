import * as THREE from "https://unpkg.com/three@0.156.0/build/three.module.js";

const canvas = document.getElementById("battlefield");
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
  enemy: "#ef4444",
  neutral: "#facc15",
  selection: "#38bdf8",
  terrain: "#0b1120",
  gridMain: "#334155",
  gridSub: "#1e293b",
};

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(canvas.clientWidth || canvas.width, canvas.clientHeight || canvas.height, false);

const scene = new THREE.Scene();
scene.background = new THREE.Color("#020617");

let camera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 1000);
camera.up.set(0, 1, 0);
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(25, 50, 25);
scene.add(dirLight);

const terrainGroup = new THREE.Group();
const resourceGroup = new THREE.Group();
const buildingGroup = new THREE.Group();
const unitGroup = new THREE.Group();
const selectionGroup = new THREE.Group();
scene.add(terrainGroup, resourceGroup, buildingGroup, unitGroup, selectionGroup);

let groundMesh = null;
let gridHelper = null;
let environmentKey = "";

const unitMeshes = new Map();
const buildingMeshes = new Map();
const resourceMeshes = new Map();
const selectionMeshes = new Map();

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const intersectionPoint = new THREE.Vector3();

setupEnvironment();
updateCameraProjection(canvas.clientWidth || canvas.width, canvas.clientHeight || canvas.height);
animate();

function setupEnvironment() {
  const key = `${mapSize[0]}x${mapSize[1]}`;
  if (environmentKey === key) {
    return;
  }
  environmentKey = key;
  if (groundMesh) {
    terrainGroup.remove(groundMesh);
    groundMesh.geometry.dispose();
    groundMesh.material.dispose();
  }
  if (gridHelper) {
    terrainGroup.remove(gridHelper);
  }
  const [mapWidth, mapHeight] = mapSize;
  const planeGeometry = new THREE.PlaneGeometry(
    mapWidth,
    mapHeight,
    Math.max(1, Math.floor(mapWidth / 4)),
    Math.max(1, Math.floor(mapHeight / 4))
  );
  const planeMaterial = new THREE.MeshPhongMaterial({ color: COLORS.terrain, shininess: 12 });
  groundMesh = new THREE.Mesh(planeGeometry, planeMaterial);
  groundMesh.rotation.x = -Math.PI / 2;
  terrainGroup.add(groundMesh);

  const gridSize = Math.max(mapWidth, mapHeight);
  const divisions = Math.max(1, Math.floor(gridSize / 4));
  gridHelper = new THREE.GridHelper(gridSize, divisions, COLORS.gridMain, COLORS.gridSub);
  gridHelper.position.y = 0.05;
  const gridMaterials = Array.isArray(gridHelper.material)
    ? gridHelper.material
    : [gridHelper.material];
  gridMaterials.forEach((material) => {
    material.opacity = 0.3;
    material.transparent = true;
  });
  terrainGroup.add(gridHelper);
}

function updateCameraProjection(width, height) {
  if (!camera) {
    camera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 1000);
  }
  const safeWidth = width || canvas.width || 960;
  const safeHeight = height || canvas.height || 640;
  const aspect = safeWidth / safeHeight;
  const [mapWidth, mapHeight] = mapSize;
  const frustumSize = Math.max(mapWidth, mapHeight) * 1.4;

  camera.left = (-frustumSize * aspect) / 2;
  camera.right = (frustumSize * aspect) / 2;
  camera.top = frustumSize / 2;
  camera.bottom = -frustumSize / 2;
  camera.near = 0.1;
  camera.far = 1000;
  const distance = Math.max(mapWidth, mapHeight) * 1.2;
  camera.position.set(distance, distance, distance);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
}

function resizeRenderer() {
  const width = canvas.clientWidth || canvas.width;
  const height = canvas.clientHeight || canvas.height;
  if (!width || !height) {
    return;
  }
  const needResize = canvas.width !== width || canvas.height !== height;
  if (needResize) {
    renderer.setSize(width, height, false);
  }
  updateCameraProjection(width, height);
}

function animate() {
  requestAnimationFrame(animate);
  resizeRenderer();
  renderer.render(scene, camera);
}

function mapToWorld(x, y) {
  const [mapWidth, mapHeight] = mapSize;
  return {
    x: x - mapWidth / 2,
    z: y - mapHeight / 2,
  };
}

function getMapCoordinates(event) {
  const rect = canvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;
  if (!width || !height) {
    return null;
  }
  pointer.x = ((event.clientX - rect.left) / width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.ray.intersectPlane(groundPlane, intersectionPoint);
  if (!hit) {
    return null;
  }
  const [mapWidth, mapHeight] = mapSize;
  const mapX = intersectionPoint.x + mapWidth / 2;
  const mapY = intersectionPoint.z + mapHeight / 2;
  return { x: mapX, y: mapY };
}

function clearDynamicMeshes() {
  for (const mesh of unitMeshes.values()) {
    unitGroup.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  for (const mesh of buildingMeshes.values()) {
    buildingGroup.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  for (const mesh of resourceMeshes.values()) {
    resourceGroup.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  for (const mesh of selectionMeshes.values()) {
    selectionGroup.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
  }
  unitMeshes.clear();
  buildingMeshes.clear();
  resourceMeshes.clear();
  selectionMeshes.clear();
}

function syncResources() {
  if (!gameState) return;
  const seen = new Set();
  for (const resource of gameState.resources) {
    let mesh = resourceMeshes.get(resource.id);
    if (!mesh) {
      const geometry = new THREE.CylinderGeometry(1.5, 1.5, 1.2, 20);
      const material = new THREE.MeshPhongMaterial({ color: COLORS.neutral });
      mesh = new THREE.Mesh(geometry, material);
      resourceGroup.add(mesh);
      resourceMeshes.set(resource.id, mesh);
    }
    const world = mapToWorld(resource.position[0], resource.position[1]);
    mesh.position.set(world.x, 0.6, world.z);
    mesh.userData = { id: resource.id, kind: "resource" };
    seen.add(resource.id);
  }
  for (const [id, mesh] of resourceMeshes.entries()) {
    if (!seen.has(id)) {
      resourceGroup.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      resourceMeshes.delete(id);
    }
  }
}

function syncBuildings() {
  if (!gameState) return;
  const seen = new Set();
  for (const building of gameState.buildings) {
    let mesh = buildingMeshes.get(building.id);
    if (!mesh) {
      const geometry = new THREE.BoxGeometry(4, 3, 4);
      const material = new THREE.MeshPhongMaterial({ color: getPlayerColor(building.owner) });
      mesh = new THREE.Mesh(geometry, material);
      buildingGroup.add(mesh);
      buildingMeshes.set(building.id, mesh);
      mesh.userData = { id: building.id, kind: "building", selectionRadius: 2.8 };
    }
    mesh.material.color.set(getPlayerColor(building.owner));
    const world = mapToWorld(building.position[0], building.position[1]);
    mesh.position.set(world.x, 1.5, world.z);
    seen.add(building.id);
  }
  for (const [id, mesh] of buildingMeshes.entries()) {
    if (!seen.has(id)) {
      buildingGroup.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      buildingMeshes.delete(id);
    }
  }
}

function syncUnits() {
  if (!gameState) return;
  const seen = new Set();
  for (const unit of gameState.units) {
    let mesh = unitMeshes.get(unit.id);
    if (!mesh) {
      const radius = unit.type === "tank" ? 1.4 : 1;
      const geometry = new THREE.CylinderGeometry(radius, radius, 1.2, 24);
      const material = new THREE.MeshPhongMaterial({ color: getPlayerColor(unit.owner) });
      mesh = new THREE.Mesh(geometry, material);
      mesh.rotation.x = 0;
      unitGroup.add(mesh);
      unitMeshes.set(unit.id, mesh);
      mesh.userData = { id: unit.id, kind: "unit", selectionRadius: radius * 1.2 };
    }
    mesh.material.color.set(getPlayerColor(unit.owner));
    const world = mapToWorld(unit.position[0], unit.position[1]);
    mesh.position.set(world.x, 0.6, world.z);
    seen.add(unit.id);
  }
  for (const [id, mesh] of unitMeshes.entries()) {
    if (!seen.has(id)) {
      unitGroup.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      unitMeshes.delete(id);
    }
  }
}

function syncSelections() {
  const desired = new Set();
  selectedUnits.forEach((id) => desired.add(id));
  if (selectedBuilding) {
    desired.add(selectedBuilding);
  }

  for (const id of desired) {
    let targetMesh = unitMeshes.get(id) || buildingMeshes.get(id);
    if (!targetMesh) {
      continue;
    }
    let ring = selectionMeshes.get(id);
    const baseRadius = targetMesh.userData?.selectionRadius || 1.4;
    if (!ring) {
      const geometry = new THREE.RingGeometry(baseRadius * 0.9, baseRadius * 1.1, 32);
      const material = new THREE.MeshBasicMaterial({
        color: COLORS.selection,
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
      });
      ring = new THREE.Mesh(geometry, material);
      ring.rotation.x = -Math.PI / 2;
      selectionGroup.add(ring);
      selectionMeshes.set(id, ring);
    }
    ring.position.set(targetMesh.position.x, 0.05, targetMesh.position.z);
  }

  for (const [id, ring] of selectionMeshes.entries()) {
    if (!desired.has(id)) {
      selectionGroup.remove(ring);
      ring.geometry.dispose();
      ring.material.dispose();
      selectionMeshes.delete(id);
    }
  }
}

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
  const coords = getMapCoordinates(event);
  if (!coords) {
    return;
  }
  const { x, y } = coords;

  if (event.button === 0) {
    handleSelection(x, y, event.shiftKey);
  } else if (event.button === 2) {
    handleCommand(x, y);
  }
});

canvas.addEventListener("mousemove", (event) => {
  if (!gameState) return;
  const coords = getMapCoordinates(event);
  if (!coords) {
    tooltip.style.opacity = 0;
    lastHover = null;
    return;
  }
  const hoverInfo = pickEntity(coords.x, coords.y);
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
    gameState = null;
    tooltip.style.opacity = 0;
    lastHover = null;
    clearDynamicMeshes();
    draw();
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
    draw();
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
  draw();
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
    clearDynamicMeshes();
    return;
  }
  setupEnvironment();
  syncResources();
  syncBuildings();
  syncUnits();
  syncSelections();
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
