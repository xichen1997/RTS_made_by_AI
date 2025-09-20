import * as THREE from "https://unpkg.com/three@0.164.1/build/three.module.js";

const canvas = document.getElementById("battlefield");
const connectBtn = document.getElementById("connect-btn");
const roomInput = document.getElementById("room-input");
const nameInput = document.getElementById("name-input");
const statusLabel = document.getElementById("status-indicator");
const resourceDisplay = document.getElementById("resource-display");
const eventLog = document.getElementById("event-log");
const tooltip = document.getElementById("tooltip");
const productionButtons = document.querySelectorAll("[data-unit]");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(window.devicePixelRatio || 1);
renderer.shadowMap.enabled = false;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x020617);

const camera = new THREE.OrthographicCamera(-50, 50, 50, -50, -200, 400);
camera.position.set(80, 80, 80);
camera.lookAt(0, 0, 0);
camera.up.set(0, 1, 0);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);

const keyLight = new THREE.DirectionalLight(0xffffff, 0.65);
keyLight.position.set(120, 160, 80);
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0x88b4ff, 0.25);
rimLight.position.set(-80, 120, -60);
scene.add(rimLight);

const groundMaterial = new THREE.MeshStandardMaterial({
  color: 0x08111f,
  roughness: 0.95,
  metalness: 0.05,
});
const ground = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), groundMaterial);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

let gridLines = null;
const gridMaterial = new THREE.LineBasicMaterial({
  color: 0x0f172a,
  transparent: true,
  opacity: 0.55,
});

const unitMeshes = new Map();
const buildingMeshes = new Map();
const resourceMeshes = new Map();

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
};

const sharedHighlightMaterial = new THREE.MeshBasicMaterial({
  color: new THREE.Color(COLORS.selection),
  transparent: true,
  opacity: 0.6,
  depthWrite: false,
});

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
  const mapPoint = getMapPoint(event);
  if (!mapPoint) {
    return;
  }

  if (event.button === 0) {
    handleSelection(mapPoint.x, mapPoint.y, event.shiftKey);
  } else if (event.button === 2) {
    handleCommand(mapPoint.x, mapPoint.y);
  }
});

canvas.addEventListener("mousemove", (event) => {
  if (!gameState) {
    tooltip.style.opacity = 0;
    lastHover = null;
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const mapPoint = getMapPoint(event);
  if (!mapPoint) {
    tooltip.style.opacity = 0;
    lastHover = null;
    return;
  }
  tooltip.style.left = `${event.clientX - rect.left + 16}px`;
  tooltip.style.top = `${event.clientY - rect.top + 16}px`;
  const hoverInfo = pickEntity(mapPoint.x, mapPoint.y);
  if (hoverInfo && hoverInfo.id !== lastHover) {
    tooltip.textContent = hoverInfo.label;
    tooltip.style.opacity = 1;
    lastHover = hoverInfo.id;
  } else if (!hoverInfo) {
    tooltip.style.opacity = 0;
    lastHover = null;
  }
});

canvas.addEventListener("mouseleave", () => {
  tooltip.style.opacity = 0;
  lastHover = null;
});

window.addEventListener("resize", () => {
  resizeRendererToDisplaySize(true);
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
      updateScene();
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
    updateSelectionHighlights();
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
  updateSelectionHighlights();
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
  const threshold = 3.2;
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
  for (const building of gameState.buildings) {
    const [bx, by] = building.position;
    const size = 6;
    if (x >= bx - size && x <= bx + size && y >= by - size && y <= by + size) {
      return {
        id: building.id,
        owner: building.owner,
        label: `${building.type.toUpperCase()} (${building.hp}/${building.max_hp})`,
        kind: "building",
      };
    }
  }
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

function updateScene() {
  resizeRendererToDisplaySize();
  updateGroundGeometry();
  syncResources();
  syncBuildings();
  syncUnits();
  updateSelectionHighlights();
}

function resizeRendererToDisplaySize(force = false) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) {
    return;
  }
  const needResize = force || canvas.width !== width || canvas.height !== height;
  if (needResize) {
    renderer.setSize(width, height, false);
    updateCameraFrustum();
  }
}

function updateCameraFrustum() {
  const width = canvas.clientWidth || canvas.width;
  const height = canvas.clientHeight || canvas.height;
  if (!width || !height) {
    return;
  }
  const aspect = width / height;
  const largest = Math.max(mapSize[0], mapSize[1]);
  const frustum = largest * 1.25;
  camera.left = (-frustum * aspect) / 2;
  camera.right = (frustum * aspect) / 2;
  camera.top = frustum / 2;
  camera.bottom = -frustum / 2;
  camera.updateProjectionMatrix();
  const distance = largest * 0.9;
  camera.position.set(distance, distance, distance);
  camera.lookAt(0, 0, 0);
}

function updateGroundGeometry() {
  const [mapWidth, mapHeight] = mapSize;
  ground.scale.set(mapWidth, mapHeight, 1);
  if (gridLines) {
    scene.remove(gridLines);
    disposeObject(gridLines);
    gridLines = null;
  }
  gridLines = createGrid(mapWidth, mapHeight, 4);
  scene.add(gridLines);
}

function createGrid(width, height, step) {
  const points = [];
  for (let x = -width / 2; x <= width / 2; x += step) {
    points.push(x, 0.02, -height / 2, x, 0.02, height / 2);
  }
  for (let z = -height / 2; z <= height / 2; z += step) {
    points.push(-width / 2, 0.02, z, width / 2, 0.02, z);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  const lines = new THREE.LineSegments(geometry, gridMaterial.clone());
  return lines;
}

function syncUnits() {
  if (!gameState) return;
  const seen = new Set();
  for (const unit of gameState.units) {
    let mesh = unitMeshes.get(unit.id);
    if (!mesh) {
      mesh = createUnitMesh(unit);
      unitMeshes.set(unit.id, mesh);
      scene.add(mesh);
    }
    updateUnitMesh(mesh, unit);
    seen.add(unit.id);
  }
  for (const [id, mesh] of unitMeshes.entries()) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject(mesh);
      unitMeshes.delete(id);
    }
  }
}

function syncBuildings() {
  if (!gameState) return;
  const seen = new Set();
  for (const building of gameState.buildings) {
    let mesh = buildingMeshes.get(building.id);
    if (!mesh) {
      mesh = createBuildingMesh(building);
      buildingMeshes.set(building.id, mesh);
      scene.add(mesh);
    }
    updateBuildingMesh(mesh, building);
    seen.add(building.id);
  }
  for (const [id, mesh] of buildingMeshes.entries()) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject(mesh);
      buildingMeshes.delete(id);
    }
  }
}

function syncResources() {
  if (!gameState) return;
  const seen = new Set();
  for (const resource of gameState.resources) {
    let mesh = resourceMeshes.get(resource.id);
    if (!mesh) {
      mesh = createResourceMesh(resource);
      resourceMeshes.set(resource.id, mesh);
      scene.add(mesh);
    }
    updateResourceMesh(mesh, resource);
    seen.add(resource.id);
  }
  for (const [id, mesh] of resourceMeshes.entries()) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject(mesh);
      resourceMeshes.delete(id);
    }
  }
}

function createUnitMesh(unit) {
  const group = new THREE.Group();
  group.userData.kind = "unit";
  group.userData.id = unit.id;

  const { geometry, height, highlightRadius } = unitGeometryForType(unit.type);
  const material = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.65,
    metalness: 0.1,
  });
  const body = new THREE.Mesh(geometry, material);
  body.position.y = height / 2;
  body.castShadow = false;
  body.receiveShadow = false;
  group.add(body);

  const highlight = createHighlight(highlightRadius);
  group.add(highlight);

  group.userData.body = body;
  group.userData.highlight = highlight;
  group.userData.highlightRadius = highlightRadius;
  return group;
}

function updateUnitMesh(mesh, unit) {
  const { body } = mesh.userData;
  const color = getPlayerColor(unit.owner);
  body.material.color.set(color);
  const { x, z } = mapToWorld(unit.position);
  mesh.position.set(x, 0, z);
  const healthRatio = Math.max(0.25, unit.hp / unit.max_hp);
  body.material.emissive.set(color).multiplyScalar(0.2 * healthRatio);
}

function createBuildingMesh(building) {
  const group = new THREE.Group();
  group.userData.kind = "building";
  group.userData.id = building.id;

  const { geometry, height, highlightRadius } = buildingGeometryForType(building.type);
  const material = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.6,
    metalness: 0.15,
  });
  const structure = new THREE.Mesh(geometry, material);
  structure.position.y = height / 2;
  group.add(structure);

  const highlight = createHighlight(highlightRadius);
  highlight.position.y = 0.1;
  group.add(highlight);

  group.userData.body = structure;
  group.userData.highlight = highlight;
  group.userData.highlightRadius = highlightRadius;
  return group;
}

function updateBuildingMesh(mesh, building) {
  const { body } = mesh.userData;
  const color = getPlayerColor(building.owner);
  body.material.color.set(color);
  const { x, z } = mapToWorld(building.position);
  mesh.position.set(x, 0, z);
  const hpRatio = Math.max(0.35, building.hp / building.max_hp);
  body.material.emissive.set(color).multiplyScalar(0.15 * hpRatio);
}

function createResourceMesh(resource) {
  const height = 1.2;
  const geometry = new THREE.CylinderGeometry(1.6, 2.2, height, 10);
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(COLORS.neutral),
    roughness: 0.9,
    metalness: 0.05,
  });
  const node = new THREE.Mesh(geometry, material);
  node.position.y = height / 2;
  node.userData.kind = "resource";
  node.userData.id = resource.id;
  return node;
}

function updateResourceMesh(mesh, resource) {
  const { x, z } = mapToWorld(resource.position);
  mesh.position.set(x, 0, z);
  const intensity = Math.max(0.3, Math.min(1, resource.remaining / 5000));
  mesh.material.emissive.set(COLORS.neutral).multiplyScalar(0.25 * intensity);
}

function createHighlight(radius) {
  const geometry = new THREE.RingGeometry(radius - 0.15, radius + 0.15, 32);
  const material = sharedHighlightMaterial.clone();
  const mesh = new THREE.Mesh(geometry, material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = 0.05;
  mesh.visible = false;
  return mesh;
}

function unitGeometryForType(type) {
  switch (type) {
    case "tank":
      return {
        geometry: new THREE.BoxGeometry(2.8, 1.1, 3.4),
        height: 1.1,
        highlightRadius: 2.1,
      };
    case "harvester":
      return {
        geometry: new THREE.BoxGeometry(2.4, 1.2, 3.2),
        height: 1.2,
        highlightRadius: 1.9,
      };
    default:
      return {
        geometry: new THREE.CylinderGeometry(0.6, 0.6, 1.7, 12),
        height: 1.7,
        highlightRadius: 1.2,
      };
  }
}

function buildingGeometryForType(type) {
  switch (type) {
    case "factory":
      return {
        geometry: new THREE.BoxGeometry(10, 4, 8),
        height: 4,
        highlightRadius: 6.5,
      };
    default:
      return {
        geometry: new THREE.BoxGeometry(8, 4.5, 8),
        height: 4.5,
        highlightRadius: 5.5,
      };
  }
}

function updateSelectionHighlights() {
  for (const [id, mesh] of unitMeshes.entries()) {
    const highlight = mesh.userData.highlight;
    if (highlight) {
      highlight.visible = selectedUnits.has(id);
    }
  }
  for (const [id, mesh] of buildingMeshes.entries()) {
    const highlight = mesh.userData.highlight;
    if (highlight) {
      highlight.visible = selectedBuilding === id;
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

function mapToWorld([mx, my]) {
  return {
    x: mx - mapSize[0] / 2,
    z: my - mapSize[1] / 2,
  };
}

function getMapPoint(event) {
  const rect = canvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  pointer.set(x, y);
  raycaster.setFromCamera(pointer, camera);
  const intersection = new THREE.Vector3();
  if (!raycaster.ray.intersectPlane(groundPlane, intersection)) {
    return null;
  }
  const mapX = intersection.x + mapSize[0] / 2;
  const mapY = intersection.z + mapSize[1] / 2;
  if (mapX < 0 || mapY < 0 || mapX > mapSize[0] || mapY > mapSize[1]) {
    return null;
  }
  return { x: mapX, y: mapY };
}

function disposeObject(object) {
  object.traverse((child) => {
    if (child.geometry) {
      child.geometry.dispose();
    }
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach((mat) => mat.dispose());
      } else {
        child.material.dispose();
      }
    }
  });
}

function animate() {
  requestAnimationFrame(animate);
  resizeRendererToDisplaySize();
  renderer.render(scene, camera);
}

animate();
