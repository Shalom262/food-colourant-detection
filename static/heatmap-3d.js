import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const panel = document.getElementById('heat3dPanel');
const host = document.getElementById('heat3dView');
const select = document.getElementById('heat3dTask');
const status = document.getElementById('heat3dStatus');
let cams = null, scene, camera, renderer, controls, surface, frame = 0;
const spiceButtons = [...document.querySelectorAll('[data-spice]')];
function markSpice(powder) { spiceButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.spice === powder))); }
spiceButtons.forEach(button => button.addEventListener('click', () => {
  markSpice(button.dataset.spice);
  window.dispatchEvent(new CustomEvent('spicescope:prediction', {detail: {powder: button.dataset.spice}}));
}));
window.addEventListener('spicescope:prediction', event => markSpice(event.detail?.powder));
markSpice('Chilli');

function initialize() {
  if (renderer) return true;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.append(renderer.domElement);
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(38, 1, .1, 100);
    camera.position.set(3.8, 3.4, 4.7);
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, .35, 0); controls.enableDamping = false; controls.minDistance = 3; controls.maxDistance = 12;
    controls.maxPolarAngle = Math.PI * .49;
    controls.addEventListener('change', draw);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xb1c4a4, 2.5));
    const light = new THREE.DirectionalLight(0xffffff, 2); light.position.set(2, 5, 4); scene.add(light);
    const base = new THREE.GridHelper(4.6, 14, 0x96ab91, 0xd4dfcf); base.position.y = -.035; scene.add(base);
    new ResizeObserver(resize).observe(host);
    resize();
    return true;
  } catch (_) { status.textContent = '3D view is unavailable on this device. The original heatmaps remain available above.'; return false; }
}
function resize() {
  if (!renderer || !host.clientWidth || !host.clientHeight) return;
  renderer.setSize(host.clientWidth, host.clientHeight, false);
  camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); draw();
}
function draw() { if (renderer && panel.open) renderer.render(scene, camera); }
function update() {
  if (!panel.open || !cams || !initialize()) return;
  const cam = cams[select.value];
  if (surface) { scene.remove(surface); surface.geometry.dispose(); surface.material.dispose(); surface = null; }
  if (!cam?.has_positive_activation || !Array.isArray(cam.grid) || cam.grid.length < 2) {
    status.textContent = 'No positive Grad-CAM activation is available for this prediction head.'; draw(); return;
  }
  const grid = cam.grid, rows = grid.length, cols = grid[0].length;
  if (cols < 2 || grid.some(row => !Array.isArray(row) || row.length !== cols || row.some(v => !Number.isFinite(v)))) {
    status.textContent = 'The attribution grid is unavailable.'; draw(); return;
  }
  const geometry = new THREE.PlaneGeometry(4, 4, cols - 1, rows - 1);
  geometry.rotateX(-Math.PI / 2);
  const positions = geometry.attributes.position;
  const colors = [], color = new THREE.Color();
  for (let i = 0; i < positions.count; i++) {
    const value = Math.max(0, Math.min(1, grid[Math.floor(i / cols)][i % cols]));
    positions.setY(i, value * 1.5);
    color.setHSL((1 - value) * .62, .85, .48); colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3)); geometry.computeVertexNormals();
  surface = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({vertexColors: true, side: THREE.DoubleSide, roughness: .82}));
  scene.add(surface); status.textContent = `${select.options[select.selectedIndex].text} head · ${cam.target} · normalized positive attribution`; resize();
}
window.addEventListener('spicescope:explanations', event => { cams = event.detail?.cams || null; update(); });
window.addEventListener('spicescope:explanations-cleared', () => { cams = null; if(surface && scene){scene.remove(surface);surface.geometry.dispose();surface.material.dispose();surface=null;} status.textContent='Generate explanations to view the surface.'; });
panel.addEventListener('toggle', update);
select.addEventListener('change', update);
document.getElementById('heat3dReset').addEventListener('click', () => { if (!controls) return; camera.position.set(3.8,3.4,4.7); controls.target.set(0,.35,0); controls.update(); draw(); });
