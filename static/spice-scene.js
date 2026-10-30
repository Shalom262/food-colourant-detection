import * as THREE from 'three';

const host = document.getElementById('heroArt');
const fallback = document.getElementById('spiceScene');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const lowPower = matchMedia('(max-width: 640px)').matches || (navigator.hardwareConcurrency || 8) <= 4;
const palettes = {
  Chilli: { powder: '#a9442b', grain: '#b95232' },
  CurryPowder: { powder: '#bd842b', grain: '#cf9936' },
  Turmeric: { powder: '#d2a21d', grain: '#e1b42b' }
};
let activePalette = palettes.Chilli;

function drawFallback() {
  fallback.hidden = false;
  const caption = document.getElementById('sceneCaption');
  if (caption) caption.textContent = 'ILLUSTRATIVE VIEW';
  const bounds = host.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
  fallback.width = Math.max(1, Math.round(bounds.width * ratio));
  fallback.height = Math.max(1, Math.round(bounds.height * ratio));
  const context = fallback.getContext('2d');
  if (!context) return;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  const width = bounds.width;
  const height = bounds.height;
  const centerX = width * 0.5;
  const centerY = height * 0.58;
  context.clearRect(0, 0, width, height);
  context.fillStyle = 'rgba(42, 48, 30, .11)';
  context.beginPath();
  context.ellipse(centerX, height * 0.79, width * 0.23, height * 0.055, 0, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = activePalette.powder;
  context.beginPath();
  context.ellipse(centerX, centerY - 13, width * 0.205, height * 0.105, 0, Math.PI, Math.PI * 2);
  context.fill();
  const bowl = context.createLinearGradient(0, centerY, 0, centerY + height * 0.22);
  bowl.addColorStop(0, '#f5efdf');
  bowl.addColorStop(1, '#cfc5ae');
  context.fillStyle = bowl;
  context.beginPath();
  context.moveTo(centerX - width * 0.23, centerY);
  context.quadraticCurveTo(centerX - width * 0.19, centerY + height * 0.24, centerX, centerY + height * 0.24);
  context.quadraticCurveTo(centerX + width * 0.19, centerY + height * 0.24, centerX + width * 0.23, centerY);
  context.quadraticCurveTo(centerX, centerY + height * 0.075, centerX - width * 0.23, centerY);
  context.fill();
  context.strokeStyle = '#fff9e9';
  context.lineWidth = 5;
  context.beginPath();
  context.ellipse(centerX, centerY, width * 0.23, height * 0.07, 0, 0, Math.PI * 2);
  context.stroke();
  for (let index = 0; index < 170; index += 1) {
    const angle = index * 2.399;
    const radius = Math.sqrt((index + 0.5) / 170) * width * 0.19;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY - 13 - Math.sin(angle) * radius * 0.45;
    context.globalAlpha = 0.55 + (index % 5) * 0.08;
    context.fillStyle = index % 3 ? activePalette.grain : '#6f3a24';
    context.beginPath();
    context.ellipse(x, y, 1.5, 1, angle, 0, Math.PI * 2);
    context.fill();
  }
  context.globalAlpha = 1;
}

function startScene() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: !lowPower, powerPreference: 'low-power' });
  } catch {
    drawFallback();
    window.addEventListener('spicescope:prediction', event => {
      activePalette = palettes[event.detail?.powder] || palettes.Chilli;
      drawFallback();
    });
    return;
  }

  const canvas = renderer.domElement;
  canvas.className = 'spice-renderer';
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'Illustrative 3D bowl of spice. Drag to rotate or use the arrow keys.');
  canvas.setAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight ArrowUp ArrowDown');
  canvas.tabIndex = 0;
  host.append(canvas);
  fallback.hidden = true;
  const caption = document.getElementById('sceneCaption');
  if (caption) caption.textContent = 'ILLUSTRATIVE · DRAG TO ROTATE';

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  camera.position.set(0, 2.2, 6.5);
  camera.lookAt(0, 0.35, 0);
  scene.add(new THREE.HemisphereLight(0xfff8e9, 0x53604b, 2.1));
  const keyLight = new THREE.DirectionalLight(0xfff1d8, 3.2);
  keyLight.position.set(-3.2, 5, 4);
  scene.add(keyLight);
  const fillLight = new THREE.DirectionalLight(0xd9e8d0, 1.1);
  fillLight.position.set(3, 2, -3);
  scene.add(fillLight);

  const subject = new THREE.Group();
  subject.position.y = -0.12;
  scene.add(subject);

  const bowlProfile = [
    new THREE.Vector2(0, 0.08), new THREE.Vector2(0.42, 0.08),
    new THREE.Vector2(0.68, 0.14), new THREE.Vector2(0.9, 0.3),
    new THREE.Vector2(1.08, 0.56), new THREE.Vector2(1.16, 0.72),
    new THREE.Vector2(1.13, 0.76), new THREE.Vector2(1.06, 0.63),
    new THREE.Vector2(0.9, 0.4), new THREE.Vector2(0.67, 0.22),
    new THREE.Vector2(0.38, 0.16), new THREE.Vector2(0, 0.16)
  ];
  const ceramic = new THREE.MeshPhysicalMaterial({ color: '#e9e2d2', roughness: 0.27, metalness: 0.02, clearcoat: 0.72, clearcoatRoughness: 0.24 });
  const bowl = new THREE.Mesh(new THREE.LatheGeometry(bowlProfile, 96), ceramic);
  bowl.castShadow = true;
  bowl.receiveShadow = true;
  subject.add(bowl);

  const rim = new THREE.Mesh(
    new THREE.TorusGeometry(1.145, 0.035, 12, 96),
    new THREE.MeshStandardMaterial({ color: '#faf5e8', roughness: 0.26 })
  );
  rim.rotation.x = Math.PI / 2;
  rim.position.y = 0.735;
  subject.add(rim);

  const moundMaterial = new THREE.MeshStandardMaterial({ color: activePalette.powder, roughness: 0.94 });
  const mound = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), moundMaterial);
  mound.position.set(0, 0.55, 0);
  mound.scale.set(1.02, 0.29, 0.94);
  subject.add(mound);

  const grainCount = lowPower ? 720 : 1500;
  const grainGeometry = new THREE.IcosahedronGeometry(0.018, 0);
  const grainMaterial = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.88, vertexColors: true });
  const grains = new THREE.InstancedMesh(grainGeometry, grainMaterial, grainCount);
  grains.castShadow = true;
  grains.receiveShadow = true;
  subject.add(grains);

  const randomState = { value: 42 };
  const random = () => {
    randomState.value = (randomState.value * 1664525 + 1013904223) >>> 0;
    return randomState.value / 4294967296;
  };
  const grainData = [];
  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  const rotation = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const euler = new THREE.Euler();
  const color = new THREE.Color();
  let visible = true;
  let frameId = 0;
  let dragging = false;
  let previousX = 0;
  let previousY = 0;
  let targetYaw = 0;
  let targetTilt = 0;
  const startedAt = performance.now();
  for (let index = 0; index < grainCount; index += 1) {
    const angle = random() * Math.PI * 2;
    const radius = Math.sqrt(random()) * 0.96;
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.88;
    const y = 0.55 + 0.29 * Math.sqrt(Math.max(0, 1 - radius * radius));
    const size = 0.48 + random() * 0.78;
    const tone = random();
    grainData.push({ x, y, z, size, tone, drop: random() * 0.65 });
    position.set(x, y + (reducedMotion ? 0 : grainData[index].drop), z);
    euler.set(random() * Math.PI, random() * Math.PI, random() * Math.PI);
    rotation.setFromEuler(euler);
    scale.set(size, size * (0.55 + random() * 0.35), size * 0.72);
    matrix.compose(position, rotation, scale);
    grains.setMatrixAt(index, matrix);
  }

  function applyPalette(nextPalette) {
    activePalette = nextPalette || palettes.Chilli;
    moundMaterial.color.set(activePalette.powder);
    for (let index = 0; index < grainCount; index += 1) {
      const tone = grainData[index].tone;
      color.set(activePalette.grain).offsetHSL(0, (tone - 0.5) * 0.12, (tone - 0.5) * 0.2);
      grains.setColorAt(index, color);
    }
    if (grains.instanceColor) grains.instanceColor.needsUpdate = true;
    requestFrame();
  }
  applyPalette(activePalette);

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lowPower ? 1.25 : 1.6));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.setClearColor(0x000000, 0);

  function resize() {
    const bounds = host.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    camera.aspect = bounds.width / bounds.height;
    camera.updateProjectionMatrix();
    renderer.setSize(bounds.width, bounds.height, false);
    renderer.render(scene, camera);
    requestFrame();
  }

  let lastFrame = 0;
  function requestFrame() {
    if (!frameId && visible && !document.hidden) frameId = requestAnimationFrame(renderFrame);
  }

  function renderFrame(now) {
    frameId = 0;
    if (!visible || document.hidden) return;
    if (now - lastFrame < 30) {
      requestFrame();
      return;
    }
    lastFrame = now;
    const elapsed = now - startedAt;
    const introProgress = reducedMotion ? 1 : Math.min(1, elapsed / 950);
    const eased = 1 - Math.pow(1 - introProgress, 3);
    if (introProgress < 1) {
      for (let index = 0; index < grainCount; index += 1) {
        const grain = grainData[index];
        position.set(grain.x, grain.y + grain.drop * (1 - eased), grain.z);
        euler.set(grain.tone * Math.PI, grain.size, grain.tone * Math.PI * 2);
        rotation.setFromEuler(euler);
        scale.set(grain.size, grain.size * 0.72, grain.size * 0.72);
        matrix.compose(position, rotation, scale);
        grains.setMatrixAt(index, matrix);
      }
      grains.instanceMatrix.needsUpdate = true;
    }

    const settling = Math.abs(subject.rotation.y - targetYaw) > 0.001 || Math.abs(subject.rotation.x - targetTilt) > 0.001;
    subject.rotation.y += (targetYaw - subject.rotation.y) * 0.12;
    subject.rotation.x += (targetTilt - subject.rotation.x) * 0.12;
    if (!reducedMotion && !dragging) targetYaw += 0.00018;
    renderer.render(scene, camera);
    if (!reducedMotion || introProgress < 1 || dragging || settling) requestFrame();
  }

  canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0 && event.pointerType === 'mouse') return;
    dragging = true;
    previousX = event.clientX;
    previousY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
    canvas.classList.add('is-dragging');
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    targetYaw += (event.clientX - previousX) * 0.008;
    targetTilt = THREE.MathUtils.clamp(targetTilt + (event.clientY - previousY) * 0.004, -0.18, 0.3);
    previousX = event.clientX;
    previousY = event.clientY;
    requestFrame();
  });
  const stopDragging = () => {
    dragging = false;
    canvas.classList.remove('is-dragging');
    requestFrame();
  };
  canvas.addEventListener('pointerup', stopDragging);
  canvas.addEventListener('pointercancel', stopDragging);
  canvas.addEventListener('keydown', event => {
    const step = event.shiftKey ? 0.28 : 0.14;
    if (event.key === 'ArrowLeft') targetYaw -= step;
    else if (event.key === 'ArrowRight') targetYaw += step;
    else if (event.key === 'ArrowUp') targetTilt = THREE.MathUtils.clamp(targetTilt - step, -0.18, 0.3);
    else if (event.key === 'ArrowDown') targetTilt = THREE.MathUtils.clamp(targetTilt + step, -0.18, 0.3);
    else return;
    event.preventDefault();
    requestFrame();
  });

  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    canvas.hidden = true;
    drawFallback();
  });
  window.addEventListener('spicescope:prediction', event => {
    applyPalette(palettes[event.detail?.powder] || palettes.Chilli);
  });
  new ResizeObserver(resize).observe(host);
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible) requestFrame();
  }).observe(host);
  document.addEventListener('visibilitychange', requestFrame);
  resize();
  requestFrame();
}

startScene();