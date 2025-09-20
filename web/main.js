import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.module.js";

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
  grid: "#0f172a",
  enemy: "#ef4444",
  neutral: "#facc15",
  selection: "#38bdf8",
};

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(new THREE.Color("#020617"));

const scene = new THREE.Scene();
scene.background = new THREE.Color("#020617");

const camera = new THREE.OrthographicCamera(-10, 10, 10, -10, -500, 500);
camera.up.set(0, 1, 0);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.65);
directionalLight.position.set(120, 180, 90);
scene.add(directionalLight);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const intersectionPoint = new THREE.Vector3();

let gridHelper = null;
const unitMeshes = new Map();
const buildingMeshes = new Map();
const resourceMeshes = new Map();
let configuredMapSize = null;

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
  const point = getMapPoint(event);
  if (!point) return;

  if (event.button === 0) {
    handleSelection(point.x, point.y, event.shiftKey);
  } else if (event.button === 2) {
    handleCommand(point.x, point.y);
  }
});

canvas.addEventListener("mousemove", (event) => {
  if (!gameState) return;
  const point = getMapPoint(event);
  if (!point) {
    tooltip.style.opacity = 0;
    lastHover = null;
    return;
  }
  const hoverInfo = pickEntity(point.x, point.y);
  const rect = canvas.getBoundingClientRect();
  tooltip.style.left = `${event.clientX - rect.left + 12}px`;
  tooltip.style.top = `${event.clientY - rect.top + 12}px`;
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
      if (
        !configuredMapSize ||
        configuredMapSize[0] !== mapSize[0] ||
        configuredMapSize[1] !== mapSize[1]
      ) {
        configureSceneForMapSize();
        configuredMapSize = [...mapSize];
      }
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
  updateSelectionsDisplay();
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
    updateSelectionsDisplay();
    return;
  }
  syncResources();
  syncBuildings();
  syncUnits();
  updateSelectionsDisplay();
}

function syncResources() {
  if (!gameState) return;
  const seen = new Set();
  for (const resource of gameState.resources) {
    let mesh = resourceMeshes.get(resource.id);
    if (!mesh) {
      mesh = createResourceMesh();
      resourceMeshes.set(resource.id, mesh);
      scene.add(mesh);
    }
    placeMeshAtMapPosition(mesh, resource.position[0], resource.position[1], 0.2);
    seen.add(resource.id);
  }
  for (const [id, mesh] of resourceMeshes) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject3D(mesh);
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
      mesh = createBuildingMesh(building);
      buildingMeshes.set(building.id, mesh);
      scene.add(mesh);
    }
    mesh.material.color.set(getPlayerColor(building.owner));
    placeMeshAtMapPosition(mesh, building.position[0], building.position[1], mesh.userData.baseHeight);
    seen.add(building.id);
  }
  for (const [id, mesh] of buildingMeshes) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject3D(mesh);
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
      mesh = createUnitMesh(unit);
      unitMeshes.set(unit.id, mesh);
      scene.add(mesh);
    }
    mesh.material.color.set(getPlayerColor(unit.owner));
    placeMeshAtMapPosition(mesh, unit.position[0], unit.position[1], mesh.userData.baseHeight);
    seen.add(unit.id);
  }
  for (const [id, mesh] of unitMeshes) {
    if (!seen.has(id)) {
      scene.remove(mesh);
      disposeObject3D(mesh);
      unitMeshes.delete(id);
    }
  }
}

function createResourceMesh() {
  const geometry = new THREE.CylinderGeometry(1.4, 2.2, 0.8, 10);
  const material = new THREE.MeshStandardMaterial({
    color: COLORS.neutral,
    emissive: new THREE.Color(COLORS.neutral).multiplyScalar(0.2),
    roughness: 0.6,
    metalness: 0.15,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = false;
  mesh.receiveShadow = true;
  mesh.userData.baseHeight = 0.4;
  return mesh;
}

function createBuildingMesh(building) {
  const footprint = 7;
  const height = 4.5;
  const geometry = new THREE.BoxGeometry(footprint, height, footprint);
  const material = new THREE.MeshStandardMaterial({
    color: getPlayerColor(building.owner),
    metalness: 0.25,
    roughness: 0.7,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData.baseHeight = height / 2;

  const edges = new THREE.EdgesGeometry(geometry);
  const edgeMaterial = new THREE.LineBasicMaterial({
    color: COLORS.selection,
    linewidth: 2,
  });
  const selectionOutline = new THREE.LineSegments(edges, edgeMaterial);
  selectionOutline.visible = false;
  mesh.add(selectionOutline);
  mesh.userData.selection = selectionOutline;
  return mesh;
}

function createUnitMesh(unit) {
  const radius = unit.type === "tank" ? 2.3 : 1.6;
  const height = unit.type === "tank" ? 1.2 : 1.0;
  const geometry = new THREE.CylinderGeometry(radius, radius, height, 16);
  const material = new THREE.MeshStandardMaterial({
    color: getPlayerColor(unit.owner),
    metalness: 0.3,
    roughness: 0.45,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData.baseHeight = height / 2;

  const ringGeometry = new THREE.RingGeometry(radius + 0.4, radius + 0.8, 32);
  const ringMaterial = new THREE.MeshBasicMaterial({
    color: COLORS.selection,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.75,
  });
  const selectionRing = new THREE.Mesh(ringGeometry, ringMaterial);
  selectionRing.rotation.x = -Math.PI / 2;
  selectionRing.position.y = -height / 2 + 0.05;
  selectionRing.visible = false;
  mesh.add(selectionRing);
  mesh.userData.selection = selectionRing;
  return mesh;
}

function placeMeshAtMapPosition(mesh, mapX, mapY, elevation = 0) {
  const worldX = mapX - mapSize[0] / 2;
  const worldZ = mapY - mapSize[1] / 2;
  mesh.position.set(worldX, elevation, worldZ);
}

function getPlayerColor(owner) {
  if (!owner) return COLORS.enemy;
  if (!gameState) return playerColor;
  const player = gameState.players[owner];
  if (!player) return COLORS.enemy;
  return player.color || COLORS.enemy;
}

function updateSelectionsDisplay() {
  unitMeshes.forEach((mesh, id) => {
    if (mesh.userData.selection) {
      mesh.userData.selection.visible = selectedUnits.has(id);
    }
  });
  buildingMeshes.forEach((mesh, id) => {
    if (mesh.userData.selection) {
      mesh.userData.selection.visible = selectedBuilding === id;
    }
  });
}

function getMapPoint(event) {
  updateRendererSize();
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.ray.intersectPlane(groundPlane, intersectionPoint);
  if (!hit) return null;
  const mapX = intersectionPoint.x + mapSize[0] / 2;
  const mapY = intersectionPoint.z + mapSize[1] / 2;
  return {
    x: clamp(mapX, 0, mapSize[0]),
    y: clamp(mapY, 0, mapSize[1]),
  };
}

function configureSceneForMapSize() {
  updateRendererSize();
  const [mapWidth, mapHeight] = mapSize;
  const aspect = canvas.clientWidth / canvas.clientHeight || 1;
  const viewSize = Math.max(mapWidth, mapHeight);
  const halfWidth = (viewSize * aspect) / 2;
  const halfHeight = viewSize / 2;
  camera.left = -halfWidth;
  camera.right = halfWidth;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.near = -500;
  camera.far = 500;

  const distance = viewSize * 1.4;
  const isoAngle = THREE.MathUtils.degToRad(35.264);
  const horizontal = Math.cos(isoAngle) * distance;
  const vertical = Math.sin(isoAngle) * distance;
  camera.position.set(horizontal, vertical, horizontal);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();

  updateGridHelper(mapWidth, mapHeight);
}

function updateGridHelper(mapWidth, mapHeight) {
  if (gridHelper) {
    scene.remove(gridHelper);
    disposeObject3D(gridHelper);
    gridHelper = null;
  }
  const size = Math.max(mapWidth, mapHeight);
  const divisions = Math.max(Math.round(size / 4), 1);
  const gridColor = new THREE.Color(COLORS.grid);
  gridHelper = new THREE.GridHelper(size, divisions, gridColor, gridColor);
  const scaleX = mapWidth / size;
  const scaleZ = mapHeight / size;
  gridHelper.scale.set(scaleX, 1, scaleZ);
  gridHelper.material.transparent = true;
  gridHelper.material.opacity = 0.35;
  scene.add(gridHelper);
}

function disposeObject3D(object) {
  object.traverse((child) => {
    if (child.isMesh || child.isLine) {
      if (child.geometry) {
        child.geometry.dispose?.();
      }
      if (Array.isArray(child.material)) {
        child.material.forEach((mat) => mat.dispose?.());
      } else if (child.material) {
        child.material.dispose?.();
      }
    }
  });
}

function updateRendererSize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) {
    return;
  }
  if (canvas.width !== width || canvas.height !== height) {
    renderer.setSize(width, height, false);
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
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

function animate() {
  updateRendererSize();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

window.addEventListener("resize", () => {
  configureSceneForMapSize();
});

configureSceneForMapSize();
configuredMapSize = [...mapSize];
animate();
