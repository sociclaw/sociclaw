import * as THREE from 'three';

// --- CONFIGURATION ---
const CONFIG = {
    bgColor: 0x05050b,
    accent: 0x2d6eff,
    eyeColor: 0x000000,
};

// --- SCENE SETUP ---
const canvas = document.querySelector('#hero-canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;

const scene = new THREE.Scene();
scene.background = new THREE.Color(CONFIG.bgColor);
scene.fog = new THREE.Fog(CONFIG.bgColor, 10, 50);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0, 20);

// Interaction
const interaction = { x: 0, y: 0 };
window.addEventListener('mousemove', (e) => {
    interaction.x = (e.clientX / window.innerWidth) * 2 - 1;
    interaction.y = -(e.clientY / window.innerHeight) * 2 + 1;
});

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// --- TEXTURE GENERATION ---
function createInternalGlowTexture() {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Radial Gradient for "Internal Glow"
    // Center (Hot) -> Edge (Cool/Dark)
    const grd = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grd.addColorStop(0, '#ffffff');   // Hot core White
    grd.addColorStop(0.2, '#00ffff'); // Cyan
    grd.addColorStop(0.5, '#0044ff'); // Blue
    grd.addColorStop(1, '#000022');   // Dark Blue Edge

    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, size, size);

    const texture = new THREE.CanvasTexture(canvas);
    return texture;
}

const glowTexture = createInternalGlowTexture();


// --- VORTEX SCENE ---

const mainGroup = new THREE.Group();
mainGroup.position.x = 3.5;
scene.add(mainGroup);

// 1. Vortex Particles
const count = 6000;
const geom = new THREE.BufferGeometry();
const positions = new Float32Array(count * 3);
const colors = new Float32Array(count * 3);
const sizes = new Float32Array(count);

const colorCenter = new THREE.Color(CONFIG.accent);
const colorEdge = new THREE.Color(0x00ffcc);

for (let i = 0; i < count; i++) {
    const r = Math.random() * 9 + 1.0;
    const spin = r * 3;
    const angle = Math.random() * Math.PI * 2 + spin;

    const x = Math.cos(angle) * r;
    const z = Math.sin(angle) * r;
    const y = (Math.random() - 0.5) * (r * 0.4);

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    const mixedColor = colorCenter.clone().lerp(colorEdge, r / 12);
    colors[i * 3] = mixedColor.r;
    colors[i * 3 + 1] = mixedColor.g;
    colors[i * 3 + 2] = mixedColor.b;

    sizes[i] = Math.random();
}

geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
geom.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

const particlesMat = new THREE.PointsMaterial({
    size: 0.05,
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    transparent: true
});

const particles = new THREE.Points(geom, particlesMat);
particles.rotation.z = 0.2;
mainGroup.add(particles);


// 2. THE ENTITY (Head Group)
const headGroup = new THREE.Group();
mainGroup.add(headGroup);

// CORE (Ball) - Smaller & Internal Glow Gradient
const coreGeo = new THREE.SphereGeometry(0.5, 64, 64); // Reduced from 0.6 to 0.5
const coreMat = new THREE.MeshStandardMaterial({
    map: glowTexture,          // Gradient Map
    emissiveMap: glowTexture,  // Self-illuminated Gradient
    emissive: 0xffffff,
    emissiveIntensity: 2.0,
    roughness: 0.2,
    metalness: 0.5
});
// Rotate texture mapping to face forward correctly if needed, or stick to UVs.
// Sphere UVs wrap around, so gradient might look like a 'seam' or 'pole'.
// For a true radial glow effect on a sphere, looking from any angle, Fresnels are better.
// But map works if we align it. Let's try standard map first.
const core = new THREE.Mesh(coreGeo, coreMat);
headGroup.add(core);

// Inner light (reduced range)
const coreLight = new THREE.PointLight(CONFIG.accent, 2, 10);
headGroup.add(coreLight);

// EYES - Black & Smaller
const eyeGeo = new THREE.SphereGeometry(0.08, 16, 16); // Smaller (was 0.12)
const eyeMat = new THREE.MeshBasicMaterial({ color: CONFIG.eyeColor }); // Black

const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
leftEye.position.set(-0.2, 0.1, 0.45); // Adjusted for smaller core radius (0.5)
leftEye.scale.set(1, 1.2, 0.5);
headGroup.add(leftEye);

const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
rightEye.position.set(0.2, 0.1, 0.45);
rightEye.scale.set(1, 1.2, 0.5);
headGroup.add(rightEye);


// 3. Ambient
const ambient = new THREE.AmbientLight(0xffffff, 0.1);
scene.add(ambient);


// --- ANIMATION ---
const clock = new THREE.Clock();

const tick = () => {
    const t = clock.getElapsedTime();

    particles.rotation.y = t * 0.15;

    // Gentle Breath
    headGroup.scale.setScalar(1 + Math.sin(t * 2.5) * 0.02);

    // Head Tracking (Eyes following mouse)
    // Inverted directions to fix "opposite movement"
    const lookX = interaction.x * 0.5;
    const lookY = interaction.y * 0.5;

    // Note:
    // interaction.x is -1 (Left) to +1 (Right).
    // rotation.y: + is Left, - is Right.
    // So we want interaction.x * 0.5? No, if mouse is Right (+), we want to turn Right (-).
    // Let's negate it? Wait, previously it was positive and user said "opposite".
    // Let's try explicit logic: Mouse Right -> Look Right.

    headGroup.rotation.y = THREE.MathUtils.lerp(headGroup.rotation.y, lookX, 0.1);
    headGroup.rotation.x = THREE.MathUtils.lerp(headGroup.rotation.x, -lookY, 0.1);
    // Note: we inverted Y-axis input logic in the event listener so 'lookY' is correct (Up is +).
    // Rotation.x: + is Down, - is Up. So Up (+) needs to be converted to Up (-). So -lookY.

    // Float
    mainGroup.position.y = Math.sin(t * 0.8) * 0.15;

    renderer.render(scene, camera);
    requestAnimationFrame(tick);
};

// Responsive
const handleResize = () => {
    if (window.innerWidth < 768) {
        mainGroup.position.x = 0;
        mainGroup.position.y = 2;
    } else {
        mainGroup.position.x = 3.5;
        mainGroup.position.y = 0;
    }
}
window.addEventListener('resize', handleResize);
handleResize();

tick();

// --- MODE TOGGLE LOGIC ---
document.addEventListener('DOMContentLoaded', () => {
    const modeBtns = document.querySelectorAll('.mode-btn');
    const agentView = document.getElementById('agent-view');
    const layout = document.querySelector('.layout');

    // Agent Manifest Data
    const manifest = {
        name: "SociClaw",
        type: "Autonomous Agent",
        version: "1.0.0",
        capabilities: [
            "Trend Research",
            "Quarterly Planning",
            "Content Generation (Text + Image)",
            "Trello/Notion Sync"
        ],
        interface: {
            human: "Web UI",
            machine: "CLI / API"
        },
        status: "ONLINE",
        pricing: {
            text: "Free",
            images: "Provider-based (BYO Keys)"
        },
        install: "git clone https://github.com/user/sociclaw"
    };

    // Initialize code block
    const codeEl = document.getElementById('agent-code');
    if (codeEl) {
        codeEl.textContent = JSON.stringify(manifest, null, 2);
    }

    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;

            // Update Buttons
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (mode === 'agent') {
                agentView.classList.remove('hidden');
                agentView.classList.add('visible');
                // Optional: Hide main layout to focus on terminal
                // layout.style.opacity = '0.3';
                // layout.style.filter = 'blur(5px)';
            } else {
                agentView.classList.remove('visible');
                agentView.classList.add('hidden');
                // layout.style.opacity = '1';
                // layout.style.filter = 'none';
            }
        });
    });
});
