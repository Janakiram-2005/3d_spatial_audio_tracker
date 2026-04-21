// WebSocket connection
let ws;
const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = () => {
        document.getElementById('connection-status').className = "flex items-center gap-2 bg-green-500/20 text-green-400 px-4 py-2 rounded-full border border-green-500/30 font-medium text-sm transition-all duration-300";
        document.getElementById('status-text').innerText = "Connected to Server";
    };

    ws.onclose = () => {
        document.getElementById('connection-status').className = "flex items-center gap-2 bg-red-500/20 text-red-400 px-4 py-2 rounded-full border border-red-500/30 font-medium text-sm transition-all duration-300";
        document.getElementById('status-text').innerText = "Disconnected - Retrying...";
        setTimeout(connectWebSocket, 2000);
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "settings") {
            updateSettingsUI(msg.data);
        } else if (msg.type === "state") {
            updateStateUI(msg.data);
        }
    };
};

// UI Elements
const els = {
    comInput: document.getElementById('com-port-input'),
    saveComBtn: document.getElementById('save-com-btn'),
    audioToggle: document.getElementById('audio-enable-toggle'),
    
    pitchMaxSlide: document.getElementById('pitch-max-slide'),
    pitchMaxLbl: document.getElementById('pitch-max-lbl'),
    rollMaxSlide: document.getElementById('roll-max-slide'),
    rollMaxLbl: document.getElementById('roll-max-lbl'),
    
    pitchDeadzoneSlide: document.getElementById('pitch-deadzone-slide'),
    pitchDeadzoneLbl: document.getElementById('pitch-deadzone-lbl'),
    rollDeadzoneSlide: document.getElementById('roll-deadzone-slide'),
    rollDeadzoneLbl: document.getElementById('roll-deadzone-lbl'),

    // Visualizers
    pitchVal: document.getElementById('pitch-val'),
    rollVal: document.getElementById('roll-val'),
    pitchBar: document.getElementById('pitch-bar'),
    rollBar: document.getElementById('roll-bar'),
    
    maxSystemVolumeSlide: document.getElementById('max-system-volume-slide'),
    maxSystemVolumeLbl: document.getElementById('max-system-volume-lbl'),
    recalibrateBtn: document.getElementById('recalibrate-btn'),

    masterVolList: document.getElementById('master-vol-read'),
    leftVolList: document.getElementById('left-vol-read'),
    rightVolList: document.getElementById('right-vol-read')
};

let currentSettings = {};

function updateSettingsUI(settings) {
    currentSettings = settings;
    els.comInput.value = settings.com_port;
    els.audioToggle.checked = settings.audio_enabled;
    
    els.pitchMaxSlide.value = settings.pitch_max;
    els.pitchMaxLbl.innerText = `${settings.pitch_max}°`;
    els.rollMaxSlide.value = settings.roll_max;
    els.rollMaxLbl.innerText = `${settings.roll_max}°`;
    
    els.pitchDeadzoneSlide.value = settings.pitch_deadzone;
    els.pitchDeadzoneLbl.innerText = `${settings.pitch_deadzone}°`;
    els.rollDeadzoneSlide.value = settings.roll_deadzone;
    els.rollDeadzoneLbl.innerText = `${settings.roll_deadzone}°`;
    
    if (settings.max_system_volume !== undefined) {
        els.maxSystemVolumeSlide.value = settings.max_system_volume;
        els.maxSystemVolumeLbl.innerText = `${settings.max_system_volume}%`;
    }
}

function updateStateUI(state) {
    // Top connection status from python
    if(state.status && !state.status.startsWith("Connected")) {
         document.getElementById('status-text').innerText = state.status;
    } else {
         document.getElementById('status-text').innerText = "Connected to Server";
    }

    els.pitchVal.innerText = `${state.raw_pitch.toFixed(1)}°`;
    els.rollVal.innerText = `${state.raw_roll.toFixed(1)}°`;

    // Map -90..90 to 0..100% for the bars just for visual reference
    const pitchPcnt = Math.max(0, Math.min(100, (state.raw_pitch + 90) / 180 * 100));
    const rollPcnt = Math.max(0, Math.min(100, (state.raw_roll + 90) / 180 * 100));
    
    els.pitchBar.style.width = `${pitchPcnt}%`;
    els.rollBar.style.width = `${rollPcnt}%`;

    // Update 3D variables smoothly
    targetRotX = state.raw_pitch * Math.PI / 180;
    targetRotZ = -state.raw_roll * Math.PI / 180;

    // Audio Output Visuals
    els.masterVolList.innerText = `${Math.round(state.master_volume * 100)}%`;
    els.leftVolList.innerText = `${Math.round(state.left_balance * 100)}%`;
    els.rightVolList.innerText = `${Math.round(state.right_balance * 100)}%`;
}

function sendSettingsUpdate(newValues) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: "update_settings",
            data: newValues
        }));
    }
}

// Event Listeners
els.saveComBtn.addEventListener('click', () => {
    sendSettingsUpdate({ com_port: els.comInput.value });
});

els.audioToggle.addEventListener('change', (e) => {
    sendSettingsUpdate({ audio_enabled: e.target.checked });
});

['pitchMax', 'rollMax', 'pitchDeadzone', 'rollDeadzone'].forEach(key => {
    els[`${key}Slide`].addEventListener('input', (e) => {
        els[`${key}Lbl`].innerText = `${e.target.value}°`;
    });
    els[`${key}Slide`].addEventListener('change', (e) => {
        const payload = {};
        let pyKey = key.replace(/([A-Z])/g, "_$1").toLowerCase();
        payload[pyKey] = parseFloat(e.target.value);
        sendSettingsUpdate(payload);
    });
});

els.maxSystemVolumeSlide.addEventListener('input', (e) => {
    els.maxSystemVolumeLbl.innerText = `${e.target.value}%`;
});
els.maxSystemVolumeSlide.addEventListener('change', (e) => {
    sendSettingsUpdate({ max_system_volume: parseFloat(e.target.value) });
});

els.recalibrateBtn.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "recalibrate" }));
    }
    // Simple visual feedback
    els.recalibrateBtn.classList.add('bg-indigo-500', 'text-white');
    setTimeout(() => els.recalibrateBtn.classList.remove('bg-indigo-500', 'text-white'), 200);
});

// --- Three.js Setup ---
const container = document.getElementById('three-container');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });

// We set size after a tiny tick to let the container size calculate properly
setTimeout(() => {
    renderer.setSize(container.clientWidth || 160, container.clientHeight || 160);
}, 100);

container.appendChild(renderer.domElement);

const geometry = new THREE.IcosahedronGeometry(2, 0); 
const material = new THREE.MeshPhysicalMaterial({
    color: 0x8b5cf6,
    metalness: 0.8,
    roughness: 0.2,
    wireframe: true,
    emissive: 0x3b82f6,
    emissiveIntensity: 0.4
});
const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);

const light1 = new THREE.PointLight(0xffffff, 1, 100);
light1.position.set(10, 10, 10);
scene.add(light1);
const light2 = new THREE.PointLight(0xff00ff, 1, 100);
light2.position.set(-10, -10, 10);
scene.add(light2);

camera.position.z = 6;

let targetRotX = 0;
let targetRotZ = 0;

function animate() {
    requestAnimationFrame(animate);
    
    // Smooth interpolation (GLiding toward target)
    mesh.rotation.x += (targetRotX - mesh.rotation.x) * 0.15;
    mesh.rotation.z += (targetRotZ - mesh.rotation.z) * 0.15;
    mesh.rotation.y += 0.003; // Aesthetic slow idle spin
    
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    if(container.clientWidth > 0) {
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
});

// Start WS connection
connectWebSocket();
