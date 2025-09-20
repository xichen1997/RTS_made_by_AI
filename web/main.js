import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.161.0/build/three.module.js";

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
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x020617);

const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 4000);
scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const sun = new THREE.DirectionalLight(0xffffff, 0.6);
sun.position.set(100, 200, 100);
scene.add(sun);

const pointer = new THREE.Vector2();
const raycaster = new THREE.Raycaster();

let socket = null;
let playerId = null;
let roomId = roomInput.value;
let playerColor = "#ffffff";
let gameState = null;
let selectedUnits = new Set();
let selectedBuilding = null;
let mapSize = [96, 64];
let lastHover = null;

let ground = null;
let gridHelper = null;
const unitMeshes = new Map();
const buildingMeshes = new Map();
const resourceMeshes = new Map();

const selectionColor = new THREE.Color("#38bdf8");

const COLORS = {
  enemy: "#ef4444",
  neutral: "#facc15",
};

function formatLabel(value) {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

initializeMapGeometry();
resizeRendererToDisplaySize();
configureCamera();
animate();

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
  configureCamera();
});

function animate() {
  requestAnimationFrame(animate);
  resizeRendererToDisplaySize();
  updateSelectionHighlights();
  renderer.render(scene, camera);
}

function resizeRendererToDisplaySize() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const pixelRatio = Math.min(window.devicePixelRatio, 2);
  const displayWidth = Math.floor(width * pixelRatio);
  const displayHeight = Math.floor(height * pixelRatio);
  if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
    renderer.setPixelRatio(pixelRatio);
    renderer.setSize(width, height, false);
    configureCamera();
  }
}

function initializeMapGeometry() {
  if (ground) {
    scene.remove(ground);
    ground.geometry.dispose();
    ground.material.dispose();
  }
  if (gridHelper) {
    scene.remove(gridHelper);
    gridHelper.geometry.dispose?.();
    gridHelper.material.dispose?.();
  }

  const [mapWidth, mapHeight] = mapSize;

  const planeGeometry = new THREE.PlaneGeometry(
    mapWidth,
    mapHeight,
    Math.max(Math.floor(mapWidth / 4), 1),
    Math.max(Math.floor(mapHeight / 4), 1),
  );
  const planeMaterial = new THREE.MeshStandardMaterial({
    color: 0x0f172a,
    side: THREE.DoubleSide,
    roughness: 1,
    metalness: 0,
  });
  ground = new THREE.Mesh(planeGeometry, planeMaterial);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(mapWidth / 2, 0, mapHeight / 2);
  scene.add(ground);

  const maxSize = Math.max(mapWidth, mapHeight);
  gridHelper = new THREE.GridHelper(maxSize, Math.max(Math.floor(maxSize / 4), 1), 0x0f172a, 0x0f172a);
  gridHelper.material.opacity = 0.25;
  gridHelper.material.transparent = true;
  gridHelper.scale.set(mapWidth / maxSize, 1, mapHeight / maxSize);
  gridHelper.position.set(mapWidth / 2, 0.02, mapHeight / 2);
  scene.add(gridHelper);
}

function configureCamera() {
  const [mapWidth, mapHeight] = mapSize;
  const aspect = canvas.clientWidth / canvas.clientHeight || 1;
  const viewSize = Math.max(mapWidth, mapHeight) * 0.75;

  camera.left = -viewSize * aspect;
  camera.right = viewSize * aspect;
  camera.top = viewSize;
  camera.bottom = -viewSize;
  camera.near = 0.1;
  camera.far = 4000;

  const centerX = mapWidth / 2;
  const centerZ = mapHeight / 2;
  const distance = Math.max(mapWidth, mapHeight) * 1.25;
  const theta = Math.PI / 4;
  const phi = THREE.MathUtils.degToRad(35);
  const x = centerX + distance * Math.cos(phi) * Math.sin(theta);
  const y = distance * Math.sin(phi);
  const z = centerZ + distance * Math.cos(phi) * Math.cos(theta);

  camera.position.set(x, y, z);
  camera.up.set(0, 1, 0);
  camera.lookAt(centerX, 0, centerZ);
  camera.updateProjectionMatrix();
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
        initializeMapGeometry();
        configureCamera();
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
      if (!gameState.buildings.some((b) => b.id === selectedBuilding)) {
        selectedBuilding = null;
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

function pickEntityAtEvent(event) {
  const pickables = [
    ...unitMeshes.values(),
    ...buildingMeshes.values(),
    ...resourceMeshes.values(),
  ];
  if (pickables.length === 0) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersections = raycaster.intersectObjects(pickables, false);
  if (intersections.length === 0) {
    return null;
  }
  const data = intersections[0].object.userData;
  return data ? { ...data } : null;
}

function getGroundPoint(event) {
  if (!ground) return null;
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersection = raycaster.intersectObject(ground, false)[0];
  if (!intersection) {
    return null;
  }
  return {
    x: THREE.MathUtils.clamp(intersection.point.x, 0, mapSize[0]),
    y: THREE.MathUtils.clamp(intersection.point.z, 0, mapSize[1]),
  };
}

function syncScene() {
  if (!gameState) return;
  updateUnits();
  updateBuildings();
  updateResources();
}

function updateUnits() {
  const seen = new Set();
  for (const unit of gameState.units) {
    seen.add(unit.id);
    let mesh = unitMeshes.get(unit.id);
    if (!mesh) {
      mesh = createUnitMesh(unit);
      unitMeshes.set(unit.id, mesh);
      scene.add(mesh);
    }
    updateUnitMesh(mesh, unit);
  }
  for (const [id, mesh] of unitMeshes.entries()) {
    if (!seen.has(id)) {
      disposeMesh(mesh);
      unitMeshes.delete(id);
    }
  }
}

function updateBuildings() {
  const seen = new Set();
  for (const building of gameState.buildings) {
    seen.add(building.id);
    let mesh = buildingMeshes.get(building.id);
    if (!mesh) {
      mesh = createBuildingMesh(building);
      buildingMeshes.set(building.id, mesh);
      scene.add(mesh);
    }
    updateBuildingMesh(mesh, building);
  }
  for (const [id, mesh] of buildingMeshes.entries()) {
    if (!seen.has(id)) {
      disposeMesh(mesh);
      buildingMeshes.delete(id);
    }
  }
}

function updateResources() {
  const seen = new Set();
  for (const resource of gameState.resources) {
    seen.add(resource.id);
    let mesh = resourceMeshes.get(resource.id);
    if (!mesh) {
      mesh = createResourceMesh(resource);
      resourceMeshes.set(resource.id, mesh);
      scene.add(mesh);
    }
    updateResourceMesh(mesh, resource);
  }
  for (const [id, mesh] of resourceMeshes.entries()) {
    if (!seen.has(id)) {
      disposeMesh(mesh);
      resourceMeshes.delete(id);
    }
  }
}

function createUnitMesh(unit) {
  const { radius, height, segments } = getUnitDimensions(unit.type);
  const geometry = new THREE.CylinderGeometry(radius, radius, height, segments);
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(getPlayerColor(unit.owner)),
    roughness: 0.4,
    metalness: 0.2,
    emissive: new THREE.Color(0x000000),
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData = { id: unit.id, owner: unit.owner, kind: "unit", label: "" };
  return mesh;
}

function updateUnitMesh(mesh, unit) {
  const { height } = getUnitDimensions(unit.type);
  const [ux, uy] = unit.position;
  mesh.position.set(ux, height / 2, uy);
  mesh.material.color.set(getPlayerColor(unit.owner));
  mesh.userData.owner = unit.owner;
  mesh.userData.label = `${formatLabel(unit.type)} (${unit.hp}/${unit.max_hp})`;
}

function createBuildingMesh(building) {
  const geometry = new THREE.BoxGeometry(8, 6, 8);
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(getPlayerColor(building.owner)),
    roughness: 0.6,
    metalness: 0.1,
    emissive: new THREE.Color(0x000000),
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData = { id: building.id, owner: building.owner, kind: "building", label: "" };
  return mesh;
}

function updateBuildingMesh(mesh, building) {
  const [bx, by] = building.position;
  mesh.position.set(bx, 3, by);
  mesh.material.color.set(getPlayerColor(building.owner));
  mesh.userData.owner = building.owner;
  mesh.userData.label = `${formatLabel(
    building.type
  )} (${building.hp}/${building.max_hp})`;
}

function createResourceMesh(resource) {
  const geometry = new THREE.CylinderGeometry(2.2, 3, 1.5, 8);
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(COLORS.neutral),
    roughness: 0.9,
    metalness: 0,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData = { id: resource.id, owner: null, kind: "resource", label: "" };
  return mesh;
}

function updateResourceMesh(mesh, resource) {
  const [rx, ry] = resource.position;
  mesh.position.set(rx, 0.75, ry);
  mesh.userData.label = `Resource Field (${resource.remaining.toFixed(0)} credits)`;
}

function disposeMesh(mesh) {
  scene.remove(mesh);
  mesh.geometry.dispose();
  if (Array.isArray(mesh.material)) {
    mesh.material.forEach((material) => material.dispose());
  } else {
    mesh.material.dispose();
  }
}

function updateSelectionHighlights() {
  for (const [id, mesh] of unitMeshes.entries()) {
    const isSelected = selectedUnits.has(id);
    mesh.material.emissive.set(isSelected ? selectionColor : 0x000000);
  }
  for (const [id, mesh] of buildingMeshes.entries()) {
    const isSelected = selectedBuilding === id;
    mesh.material.emissive.set(isSelected ? selectionColor : 0x000000);
  }
}

function getPlayerColor(owner) {
  if (!owner) return COLORS.enemy;
  if (!gameState) return playerColor;
  const player = gameState.players[owner];
  if (!player) return COLORS.enemy;
  return player.color || COLORS.enemy;
}

function getUnitDimensions(type) {
  switch (type) {
    case "ore_miner":
      return { radius: 3.2, height: 2.4, segments: 18 };
    case "grizzly_tank":
      return { radius: 2.8, height: 2.4, segments: 20 };
    case "prism_tank":
      return { radius: 3.0, height: 2.5, segments: 24 };
    case "mirage_tank":
      return { radius: 2.9, height: 2.3, segments: 22 };
    case "kirov_airship":
      return { radius: 3.5, height: 3.2, segments: 26 };
    case "rocketeer":
      return { radius: 1.6, height: 2.6, segments: 16 };
    case "gi":
      return { radius: 1.5, height: 2.0, segments: 14 };
    case "conscript":
      return { radius: 1.4, height: 1.8, segments: 12 };
    default:
      return { radius: 1.6, height: 1.8, segments: 12 };
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
