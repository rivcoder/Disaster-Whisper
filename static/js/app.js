/**
 * Disaster-Whisper Front-End Controller
 * =====================================
 * Handles:
 * 1. Leaflet Map setup, waypoint drawing/selection in Indore.
 * 2. Real-time selection of hazard types and role bitmasks.
 * 3. Client-side and server-side state synchronisation.
 * 4. Character budget calculations vs. SMS limits.
 * 5. Device Tier switching (mocking system specifications & RAM).
 * 6. Live call to Flask backend API for encoding/decoding/synthesis.
 */

// Indore default coordinate centering
const INDORE_LAT = 22.7196;
const INDORE_LNG = 75.8577;

let map;
let routePathLine;
let waypoints = []; // List of L.Marker objects
let waypointCoords = []; // List of [lat, lng] arrays
let activeHazardCode = 'F';
let activeRoleMask = 0;
let activeDeviceTier = 2; // Default to Tier 2 (SLM)
let activeLanguage = 'en';

// Backend state loaded dynamically
let hazardRegistry = {};
let roleRegistry = {};

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupMap();
    await loadRegistries();
    setupEventListeners();
    
    // Set default route coordinates (from paper)
    setDefaultRoute();
    updateServerAlertState();
}

// ── MAP MANAGEMENT ──────────────────────────────────────────────────────────

function setupMap() {
    // Initialise Leaflet Map
    map = L.map('route-map').setView([INDORE_LAT, INDORE_LNG], 13);
    
    // Add dark elegant map theme
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Click handler to draw waypoints
    map.on('click', (e) => {
        if (waypointCoords.length >= 20) {
            alert("Maximum route waypoints (20) reached. Clean or clear the route.");
            return;
        }
        addWaypoint(e.latlng.lat, e.latlng.lng);
        updateServerAlertState();
    });
}

function addWaypoint(lat, lng) {
    const latRounded = parseFloat(lat.toFixed(4));
    const lngRounded = parseFloat(lng.toFixed(4));
    
    const index = waypointCoords.length + 1;
    
    // Custom icon for pins
    const marker = L.marker([latRounded, lngRounded], {
        draggable: true,
        title: `Waypoint ${index}`
    }).addTo(map);

    marker.on('dragend', (e) => {
        const position = marker.getLatLng();
        const idx = waypoints.indexOf(marker);
        if (idx !== -1) {
            waypointCoords[idx] = [
                parseFloat(position.lat.toFixed(4)),
                parseFloat(position.lng.toFixed(4))
            ];
            updateMapPolyline();
            updateServerAlertState();
        }
    });

    waypoints.push(marker);
    waypointCoords.push([latRounded, lngRounded]);
    
    updateMapPolyline();
    renderWaypointsList();
}

function updateMapPolyline() {
    if (routePathLine) {
        map.removeLayer(routePathLine);
    }
    if (waypointCoords.length > 1) {
        routePathLine = L.polyline(waypointCoords, {
            color: getHazardColor(activeHazardCode),
            weight: 4,
            opacity: 0.8,
            dashArray: '5, 10'
        }).addTo(map);
        map.fitBounds(routePathLine.getBounds(), { padding: [30, 30] });
    }
}

function renderWaypointsList() {
    const listEl = document.getElementById('waypoint-list');
    listEl.innerHTML = '';
    
    if (waypointCoords.length === 0) {
        listEl.innerHTML = '<li class="empty-list-msg">No coordinates placed yet. Click on the map.</li>';
        return;
    }

    waypointCoords.forEach((coord, idx) => {
        const item = document.createElement('li');
        item.className = 'waypoint-item';
        item.innerHTML = `
            <div>
                <span class="wp-index">#${idx + 1}</span>
                <span class="wp-coords mono">[${coord[0]}, ${coord[1]}]</span>
            </div>
            <button class="wp-delete" onclick="deleteWaypoint(${idx})">×</button>
        `;
        listEl.appendChild(item);
    });
}

window.deleteWaypoint = function(index) {
    map.removeLayer(waypoints[index]);
    waypoints.splice(index, 1);
    waypointCoords.splice(index, 1);
    
    // Re-index remaining markers
    waypoints.forEach((marker, idx) => {
        marker.unbindTooltip();
        marker.bindTooltip(`Waypoint ${idx + 1}`);
    });
    
    updateMapPolyline();
    renderWaypointsList();
    updateServerAlertState();
};

function setDefaultRoute() {
    const paperIndoreRoute = [
        [22.7181, 75.8574], // Rajwada Palace
        [22.7325, 75.8763], // LIG Square
        [22.7410, 75.9006], // Geeta Bhawan
        [22.7527, 75.8944], // Vijay Nagar Square
        [22.7284, 75.9112]  // Scheme 54
    ];
    paperIndoreRoute.forEach(pt => addWaypoint(pt[0], pt[1]));
}

// ── REGISTRIES AND API CALLS ────────────────────────────────────────────────

async function loadRegistries() {
    try {
        const resH = await fetch('/api/hazards');
        hazardRegistry = await resH.json();
        renderHazardsSelector();

        const resR = await fetch('/api/roles');
        const rolesData = await resR.json();
        roleRegistry = rolesData.bits;
        renderRolesSelector();
    } catch (e) {
        console.error("Failed to load backend metadata registries", e);
    }
}

function renderHazardsSelector() {
    const parent = document.getElementById('hazard-selector');
    parent.innerHTML = '';
    
    Object.entries(hazardRegistry).forEach(([code, meta]) => {
        const btn = document.createElement('button');
        btn.className = `hazard-btn ${code === activeHazardCode ? 'active' : ''}`;
        btn.style.setProperty('--hazard-color', meta.color);
        btn.style.setProperty('--hazard-color-alpha', meta.color + '4D'); // 30% alpha
        btn.innerHTML = `
            <span class="hazard-icon">${meta.icon}</span>
            <span class="hazard-lbl">${meta.name}</span>
        `;
        btn.onclick = () => {
            activeHazardCode = code;
            document.querySelectorAll('.hazard-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            updateMapPolyline();
            updateServerAlertState();
        };
        parent.appendChild(btn);
    });
}

function renderRolesSelector() {
    const parent = document.getElementById('role-selector');
    parent.innerHTML = '';
    
    Object.entries(roleRegistry).forEach(([bitStr, meta]) => {
        const bitVal = parseInt(meta.bit);
        const btn = document.createElement('button');
        btn.className = `role-btn ${((activeRoleMask & bitVal) === bitVal) && activeRoleMask !== 0 ? 'active' : ''}`;
        btn.dataset.bit = bitVal;
        btn.innerHTML = `
            <span>${meta.label}</span>
            <div class="role-checkbox">✓</div>
        `;
        btn.onclick = () => {
            if ((activeRoleMask & bitVal) === bitVal) {
                activeRoleMask &= ~bitVal; // unset bit
            } else {
                activeRoleMask |= bitVal; // set bit
            }
            btn.classList.toggle('active');
            
            // Update summary UI
            document.getElementById('selected-hex').innerText = `0x${activeRoleMask.toString(16).toUpperCase().padStart(2, '0')}`;
            document.getElementById('selected-bin').innerText = `0b${activeRoleMask.toString(2).padStart(4, '0')}`;
            
            updateServerAlertState();
        };
        parent.appendChild(btn);
    });
}

function getHazardColor(code) {
    return hazardRegistry[code] ? hazardRegistry[code].color : '#0ea5e9';
}

// ── STATE COMPILATION & SMS BUDGETING ──────────────────────────────────────

async function updateServerAlertState() {
    if (waypointCoords.length < 2) {
        document.getElementById('payload-visualizer').innerHTML = '<span class="text-muted">Minimum 2 waypoints required</span>';
        document.getElementById('char-counter').innerText = '0 / 160 Chars';
        return;
    }

    const plaintext = document.getElementById('plaintext-suffix').value;

    try {
        const response = await fetch('/api/encode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hazard: activeHazardCode,
                role_flags: activeRoleMask,
                coordinates: waypointCoords,
                plain_text_suffix: plaintext
            })
        });

        const data = await response.json();
        if (!response.ok) {
            console.error("Encoding error:", data.error);
            return;
        }

        renderPayloadVisualizer(data.breakdown);
        updateBudgetMeter(data.sms_budget);
    } catch (e) {
        console.error("API call to encode failed", e);
    }
}

function renderPayloadVisualizer(breakdown) {
    const parent = document.getElementById('payload-visualizer');
    parent.innerHTML = '';
    
    const parts = [
        { class: 'part-hazard', text: breakdown.hazard_code.char, title: breakdown.hazard_code.description },
        { class: 'part-role', text: breakdown.role_flag.char, title: breakdown.role_flag.description },
        { class: 'part-polyline', text: breakdown.polyline.str, title: breakdown.polyline.description },
        { class: 'part-checksum', text: breakdown.checksum.char, title: breakdown.checksum.description }
    ];
    
    parts.forEach(part => {
        const span = document.createElement('span');
        span.className = part.class;
        span.title = part.title;
        span.innerText = part.text;
        parent.appendChild(span);
    });
}

function updateBudgetMeter(budget) {
    const counter = document.getElementById('char-counter');
    counter.innerText = `${budget.total_chars} / 160 Chars`;

    const fill = document.getElementById('budget-progress-fill');
    const percent = Math.min((budget.total_chars / 160) * 100, 100);
    fill.style.width = `${percent}%`;

    // Visual classification based on limits
    fill.classList.remove('warning', 'danger');
    if (budget.total_chars > 160) {
        fill.classList.add('danger');
        counter.style.color = 'var(--accent-red)';
    } else if (budget.total_chars > 140) {
        fill.classList.add('warning');
        counter.style.color = 'var(--accent-amber)';
    } else {
        counter.style.color = 'var(--accent-emerald)';
    }

    // Update stats cards
    document.getElementById('stat-payload-size').innerText = `${budget.payload_chars}B`;
    document.getElementById('stat-avail-fallback').innerText = `${budget.remaining >= 0 ? budget.remaining : 0}`;
}

// ── CLIENT-SIDE SIMULATOR (SMARTPHONE EMULATION) ────────────────────────────

function setupEventListeners() {
    // Clear route
    document.getElementById('clear-route-btn').onclick = () => {
        waypoints.forEach(w => map.removeLayer(w));
        waypoints = [];
        waypointCoords = [];
        updateMapPolyline();
        renderWaypointsList();
        updateServerAlertState();
    };

    // Suffix text watcher
    document.getElementById('plaintext-suffix').oninput = () => {
        updateServerAlertState();
    };

    // Copy broadcast
    document.getElementById('copy-broadcast-btn').onclick = () => {
        const payloadText = document.getElementById('payload-visualizer').innerText;
        const suffix = document.getElementById('plaintext-suffix').value;
        const fullMessage = payloadText + suffix;
        
        navigator.clipboard.writeText(fullMessage);
        
        // Custom micro animation
        const btn = document.getElementById('copy-broadcast-btn');
        btn.innerText = '✓ Copied!';
        btn.style.background = 'var(--accent-emerald)';
        setTimeout(() => {
            btn.innerText = '📋 Copy Message';
            btn.style.background = '';
        }, 1500);
    };

    // Sim paste button
    document.getElementById('paste-sim-btn').onclick = async () => {
        try {
            const clipText = await navigator.clipboard.readText();
            document.getElementById('paste-broadcast-input').value = clipText;
        } catch (e) {
            // Fallback if browser blocks clipboard API
            const payloadText = document.getElementById('payload-visualizer').innerText;
            const suffix = document.getElementById('plaintext-suffix').value;
            document.getElementById('paste-broadcast-input').value = payloadText + suffix;
        }
    };

    // Decode & process button
    document.getElementById('decode-btn').onclick = () => {
        processClientAlert();
    };

    // Asymmetric Tiers buttons toggle
    document.getElementById('tier2-btn').onclick = () => {
        setDeviceTier(2);
    };
    document.getElementById('tier1-btn').onclick = () => {
        setDeviceTier(1);
    };
}

function setDeviceTier(tier) {
    activeDeviceTier = tier;
    document.querySelectorAll('.tier-tab').forEach(b => b.classList.remove('active'));
    
    if (tier === 2) {
        document.getElementById('tier2-btn').classList.add('active');
        document.getElementById('device-tier-lbl').innerText = 'Tier 2 | 8GB RAM | SLM-Capable';
        document.getElementById('diag-ram-spec').innerText = '8.0 GB RAM (Eligible for Tier 2 Local SLM)';
        document.getElementById('prompt-box-wrapper').classList.remove('hidden');
    } else {
        document.getElementById('tier1-btn').classList.add('active');
        document.getElementById('device-tier-lbl').innerText = 'Tier 1 | <4GB RAM | Template Only';
        document.getElementById('diag-ram-spec').innerText = '3.0 GB RAM (Tier 1 Fallback enforced)';
        document.getElementById('prompt-box-wrapper').classList.add('hidden');
    }
}

async function processClientAlert() {
    const input = document.getElementById('paste-broadcast-input').value;
    if (!input) {
        alert("Please paste a broadcast message first!");
        return;
    }

    // Trigger Phone Emulator Loading State
    const loader = document.getElementById('phone-loader');
    const alertArea = document.getElementById('alert-render-area');
    loader.classList.remove('hidden');
    alertArea.classList.add('hidden');

    if (activeDeviceTier === 2) {
        document.getElementById('loader-text').innerText = 'Loading Small Language Model...';
    } else {
        document.getElementById('loader-text').innerText = 'Decoding payload...';
    }

    try {
        const response = await fetch('/api/decode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sms_text: input,
                tier: activeDeviceTier
            })
        });

        const data = await response.json();
        
        // Artificial delay for realistic SLM model load / rendering demo speed
        setTimeout(() => {
            loader.classList.add('hidden');
            
            if (!response.ok) {
                alert("Processing failed: " + data.error);
                return;
            }

            renderClientAlertOutput(data);
        }, 1200);

    } catch (e) {
        console.error("Decoding error:", e);
        loader.classList.add('hidden');
    }
}

function renderClientAlertOutput(data) {
    const alertArea = document.getElementById('alert-render-area');
    alertArea.classList.remove('hidden');

    // 1. Title and color scheme
    const titleEl = document.getElementById('render-alert-title');
    const haz = data.payload_decoded.hazard;
    titleEl.innerText = `${haz.icon} ${haz.name.toUpperCase()} ALERT`;
    
    // Customize phone CSS variables dynamically based on disaster color
    document.documentElement.style.setProperty('--hazard-bg', haz.color + '26'); // 15% opacity
    document.documentElement.style.setProperty('--hazard-border', haz.color);
    document.documentElement.style.setProperty('--hazard-text', haz.color);

    // 2. Audience metadata tags
    const targetRoles = data.payload_decoded.role.active_roles.map(r => r.label).join(', ');
    document.getElementById('meta-tag-audience').innerText = `Target: ${targetRoles}`;

    const integrityText = data.payload_decoded.checksum_ok ? 'Integrity: Verified ✓' : 'Integrity: FAILED ❌';
    const integTag = document.getElementById('meta-tag-integrity');
    integTag.innerText = integrityText;
    integTag.style.borderColor = data.payload_decoded.checksum_ok ? 'var(--accent-emerald)' : 'var(--accent-red)';
    integTag.style.color = data.payload_decoded.checksum_ok ? 'var(--accent-emerald)' : 'var(--accent-red)';

    // 3. Message rendering
    document.getElementById('render-alert-text').innerText = data.rendered_alert.alert_text;

    // 4. Reconstructed route steps
    const routeFlow = document.getElementById('recon-route-flow');
    routeFlow.innerHTML = '';
    
    if (data.payload_decoded.coordinates && data.payload_decoded.coordinates.length > 0) {
        data.rendered_alert.route_waypoints.forEach((wp, idx) => {
            const step = document.createElement('div');
            step.className = 'flow-step-node';
            step.innerHTML = `
                <span class="flow-step-num">${idx + 1}</span>
                <span class="wp-landmark">${wp}</span>
            `;
            routeFlow.appendChild(step);
        });
    }

    // 5. Diagnostics logs update
    document.getElementById('diag-checksum-status').innerText = data.payload_decoded.checksum_ok ? 'Checksum MATCHED' : 'Checksum MISMATCH (Corrupted)';
    document.getElementById('diag-checksum-status').style.color = data.payload_decoded.checksum_ok ? 'var(--accent-emerald)' : 'var(--accent-red)';

    // Prompt updates
    const promptText = document.getElementById('diag-slm-prompt');
    if (data.rendered_alert.prompt) {
        promptText.innerText = data.rendered_alert.prompt;
    } else {
        promptText.innerText = "// Prompt not generated (Device set to Tier-1 deterministic templating)";
    }

    // Validator check logs rendering
    const listEl = document.getElementById('validator-checks-list');
    listEl.innerHTML = '';

    if (data.validation) {
        // Output Checks
        data.validation.checks_passed.forEach(check => {
            const li = document.createElement('li');
            li.className = 'check-item pass';
            li.innerHTML = `<span>✓ ${check.replace('_', ' ').toUpperCase()}</span> <span>PASS</span>`;
            listEl.appendChild(li);
        });

        data.validation.checks_failed.forEach(check => {
            const li = document.createElement('li');
            li.className = 'check-item fail';
            li.innerHTML = `<span>❌ ${check.replace('_', ' ').toUpperCase()}</span> <span>FAIL</span>`;
            listEl.appendChild(li);
        });

        data.validation.warnings.forEach(warn => {
            const li = document.createElement('li');
            li.className = 'check-item warn';
            li.innerHTML = `<span>⚠️ ${warn}</span>`;
            listEl.appendChild(li);
        });
        
        if (data.rendered_alert.fallback_reason) {
            const li = document.createElement('li');
            li.className = 'check-item fail';
            li.innerHTML = `<span>🚨 HALLUCINATION DETECTED: ${data.rendered_alert.fallback_reason}</span>`;
            listEl.appendChild(li);
        }
    } else {
        // Deterministic template checks
        listEl.innerHTML = '<li class="check-item pass"><span>✓ DETERMINISTIC ENCODING</span> <span>PASS (100% SAFE)</span></li>';
    }
}
