// ==========================================================================
// SubseaGuard Sentinel-X — Main Application JavaScript
// Bimodal Sensor Fusion Engine & Maritime Tactical C2 Console
// ==========================================================================

// Global state
let map;
let shipsData = [];
let alertsData = [];
let markerLayerGroup;
let currentTimestamp = 1;
let isPlaying = false;
let playInterval = null;
let animationSpeed = 1000;

// Corridor zone boundaries (must match geofence.py exactly)
const CORRIDOR_BOUNDS = {
    latMin: 13.00,
    latMax: 13.10,
    lonMin: 80.35,
    lonMax: 80.50
};

// Acoustic Oscilloscope Engine State
const oscEngine = {
    canvas: null,
    ctx: null,
    animationId: null,
    phase: 0,
    burstLevel: 0,
    targetBurst: 0,
    activeFrequency: 0,
    activeEnergy: 0,
    lastBurstTime: 0
};

// Initialize the application
async function init() {
    try {
        // Initialize Oscilloscope HUD
        initOscilloscope();
        
        // Initialize Map
        initMap();
        
        // Draw corridor and subsea cable
        drawCorridorZone();
        
        // Setup event listeners
        setupEventListeners();
        
        // Load AIS data and initial alerts
        await loadData();
        
        // Render initial frame
        renderFrame(currentTimestamp);
        
        // Start live continuous alert & DAS polling
        startAlertUpdates();
        
        console.log('SubseaGuard Sentinel-X initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
    }
}

// Load data from JSON files with cache-busting
async function loadData() {
    try {
        const shipsResponse = await fetch(`../data/ships_data.json?t=${Date.now()}`);
        shipsData = await shipsResponse.json();
        
        const alertsResponse = await fetch(`../backend/alerts.json?t=${Date.now()}`);
        alertsData = await alertsResponse.json();
        
        updateDasHardwareBadge(alertsData);
        updateThreatIndex(currentTimestamp);
        console.log(`Loaded ${shipsData.length} ship records and ${alertsData.length} alerts`);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// ==========================================================================
// Live Fiber-Optic Acoustic Oscilloscope HUD
// ==========================================================================

function initOscilloscope() {
    oscEngine.canvas = document.getElementById('oscilloscopeCanvas');
    if (!oscEngine.canvas) return;
    oscEngine.ctx = oscEngine.canvas.getContext('2d');
    
    // Responsive high-DPI scaling
    const rect = oscEngine.canvas.getBoundingClientRect();
    oscEngine.canvas.width = rect.width * (window.devicePixelRatio || 1);
    oscEngine.canvas.height = rect.height * (window.devicePixelRatio || 1);
    oscEngine.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    
    renderOscilloscope();
}

function triggerOscilloscopeBurst(frequency = 440, energy = 85000) {
    oscEngine.targetBurst = 1.0;
    oscEngine.burstLevel = 1.0;
    oscEngine.activeFrequency = frequency || 440;
    oscEngine.activeEnergy = energy || 85000;
    oscEngine.lastBurstTime = Date.now();
    
    const statusBadge = document.getElementById('waveformStatus');
    if (statusBadge) {
        statusBadge.textContent = '💥 TRANSIENT BURST';
        statusBadge.classList.add('burst');
    }
}

function renderOscilloscope() {
    if (!oscEngine.ctx || !oscEngine.canvas) return;
    
    const ctx = oscEngine.ctx;
    const width = oscEngine.canvas.width / (window.devicePixelRatio || 1);
    const height = oscEngine.canvas.height / (window.devicePixelRatio || 1);
    const midY = height / 2;
    
    ctx.clearRect(0, 0, width, height);
    
    // Decay burst level
    if (oscEngine.burstLevel > 0.01) {
        oscEngine.burstLevel *= 0.94;
    } else {
        oscEngine.burstLevel = 0;
        const statusBadge = document.getElementById('waveformStatus');
        if (statusBadge && statusBadge.classList.contains('burst')) {
            statusBadge.textContent = 'STANDBY';
            statusBadge.classList.remove('burst');
        }
    }
    
    // Update live metrics on HUD
    const oscFreqEl = document.getElementById('oscFreq');
    const oscEnergyEl = document.getElementById('oscEnergy');
    const oscDecayEl = document.getElementById('oscDecay');
    
    if (oscEngine.burstLevel > 0.05) {
        if (oscFreqEl) oscFreqEl.textContent = `${oscEngine.activeFrequency.toFixed(1)} Hz`;
        if (oscEnergyEl) oscEnergyEl.textContent = `${Math.round(oscEngine.activeEnergy * oscEngine.burstLevel).toLocaleString()}`;
        if (oscDecayEl) oscDecayEl.textContent = `${(oscEngine.burstLevel * 4.5).toFixed(1)}s`;
    } else {
        if (oscFreqEl) oscFreqEl.textContent = '12.4 Hz (Amb)';
        if (oscEnergyEl) oscEnergyEl.textContent = '412 RMS';
        if (oscDecayEl) oscDecayEl.textContent = '0.0s';
    }
    
    oscEngine.phase += 0.08 + (oscEngine.burstLevel * 0.15);
    
    // Draw acoustic wave
    ctx.beginPath();
    ctx.lineWidth = oscEngine.burstLevel > 0.1 ? 2.5 : 1.5;
    
    if (oscEngine.burstLevel > 0.1) {
        ctx.strokeStyle = `rgba(239, 68, 68, ${0.4 + oscEngine.burstLevel * 0.6})`;
        ctx.shadowColor = '#ef4444';
        ctx.shadowBlur = 12 * oscEngine.burstLevel;
    } else {
        ctx.strokeStyle = 'rgba(0, 242, 254, 0.75)';
        ctx.shadowColor = '#00f2fe';
        ctx.shadowBlur = 4;
    }
    
    for (let x = 0; x < width; x += 2) {
        const normX = x / width;
        // Ambient sine with micro-jitter
        let y = Math.sin(normX * 14 + oscEngine.phase) * (4 + Math.sin(normX * 5) * 2);
        y += (Math.random() - 0.5) * 2.5;
        
        // Transient burst injection
        if (oscEngine.burstLevel > 0) {
            const burstFreq = (oscEngine.activeFrequency || 400) / 12;
            const envelope = Math.sin(normX * Math.PI); // Window function
            const transient = Math.sin(normX * burstFreq + oscEngine.phase * 4) * (midY * 0.75 * oscEngine.burstLevel * envelope);
            const spikeNoise = (Math.random() - 0.5) * 12 * oscEngine.burstLevel;
            y += transient + spikeNoise;
        }
        
        const finalY = Math.max(4, Math.min(height - 4, midY + y));
        if (x === 0) {
            ctx.moveTo(x, finalY);
        } else {
            ctx.lineTo(x, finalY);
        }
    }
    
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow
    
    oscEngine.animationId = requestAnimationFrame(renderOscilloscope);
}

// ==========================================================================
// Telemetry & Threat Metrics
// ==========================================================================

function updateThreatIndex(timestamp) {
    const threatValEl = document.getElementById('threatIndexValue');
    const threatBarEl = document.getElementById('threatProgressBar');
    if (!threatValEl || !threatBarEl) return;
    
    const currentEntries = shipsData.filter(e => e.timestamp === timestamp);
    let riskPoints = 0;
    
    currentEntries.forEach(ship => {
        const inCorridor = (ship.lat >= CORRIDOR_BOUNDS.latMin && ship.lat <= CORRIDOR_BOUNDS.latMax &&
                            ship.lon >= CORRIDOR_BOUNDS.lonMin && ship.lon <= CORRIDOR_BOUNDS.lonMax);
        if (inCorridor) {
            riskPoints += (ship.speed < 5) ? 35 : 15;
        }
    });
    
    const hasLiveDAS = alertsData.some(a => a.physical_confirmation === true);
    if (hasLiveDAS) riskPoints += 45;
    
    const threatScore = Math.min(100, Math.round(riskPoints));
    threatValEl.textContent = `${threatScore}%`;
    threatBarEl.style.width = `${threatScore}%`;
    
    if (threatScore >= 60) {
        threatValEl.style.color = '#ef4444';
    } else if (threatScore >= 30) {
        threatValEl.style.color = '#f59e0b';
    } else {
        threatValEl.style.color = '#10b981';
    }
}

// Update DOM DAS / Hardware Confirmation badge
function updateDasHardwareBadge(alerts) {
    const dasBadge = document.getElementById('dasStatusBadge');
    const dasText = document.getElementById('dasStatusText');
    if (!dasBadge || !dasText) return;

    const confirmedAlert = alerts.find(a => a.physical_confirmation === true || (a.status && a.status.includes('CONFIRMED')));
    
    if (confirmedAlert) {
        dasBadge.classList.remove('idle');
        dasBadge.classList.add('confirmed');
        const freq = confirmedAlert.frequency_hz || 440;
        dasText.textContent = `🚨 DAS TRANSIENT CONFIRMED (${freq} Hz)`;
        triggerOscilloscopeBurst(freq, confirmedAlert.energy || 85000);
    } else {
        dasBadge.classList.remove('confirmed');
        dasBadge.classList.add('idle');
        dasText.textContent = 'DAS PIEZO: STANDBY';
    }
}

// Helper to create an alert card element
function createAlertCardElement(alert) {
    const alertCard = document.createElement('div');
    const isConfirmed = alert['physical_confirmation'] === true || (alert['status'] && alert['status'].includes('CONFIRMED'));
    
    alertCard.className = `alert-card ${isConfirmed ? 'confirmed-card' : ''}`;
    alertCard.id = `alert-${alert['ship_id']}-${alert['timestamp']}`;
    
    const confidencePercent = alert['confidence_score'] || 0;
    
    let badgeHtml = '';
    if (isConfirmed) {
        badgeHtml = '<span class="alert-badge alert-badge-confirmed">CONFIRMED (DAS TRANSIENT)</span>';
    } else {
        badgeHtml = '<span class="alert-badge alert-badge-ais-only">SUSPECTED (AIS ONLY)</span>';
    }
    
    let acousticInfoHtml = '';
    if (isConfirmed && alert.frequency_hz) {
        acousticInfoHtml = `
            <div class="acoustic-meta-pill">
                <span>📡 DAS CH-04:</span>
                <span>${alert.frequency_hz} Hz</span>
                <span>•</span>
                <span>${Math.round(alert.energy || 0).toLocaleString()} RMS</span>
                <span>•</span>
                <span>KP 14.2</span>
            </div>
        `;
    }

    alertCard.innerHTML = `
        <div class="alert-card-header">
            <span class="alert-ship-id">${alert['ship_id']}</span>
            <span class="alert-timestamp">T-${String(alert['timestamp']).padStart(2, '0')}</span>
            ${badgeHtml}
        </div>
        <div class="alert-message">${alert['message']}</div>
        ${acousticInfoHtml}
        <div class="confidence-section">
            <span class="confidence-label">ML CONFIDENCE:</span>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
            </div>
            <span class="confidence-value">${confidencePercent.toFixed(1)}%</span>
        </div>
    `;
    return alertCard;
}

// ==========================================================================
// Live Alert Updates with Continuous Polling & Cache Busting
// ==========================================================================

function startAlertUpdates() {
    let previousAlertsJson = '';
    
    setInterval(async () => {
        try {
            const cacheBustUrl = `../backend/alerts.json?t=${Date.now()}`;
            const response = await fetch(cacheBustUrl);
            if (!response.ok) return;
            const newAlertsData = await response.json();
            
            alertsData = newAlertsData;
            updateDasHardwareBadge(alertsData);
            
            // If Manual Mode is active, route acoustic transients directly to manualMode
            if (manualMode.isActive) {
                const liveConfirmedAlert = alertsData.find(a => a.physical_confirmation === true);
                if (liveConfirmedAlert) {
                    manualMode.handleIncomingAcousticTransient(liveConfirmedAlert);
                }
                return; // Suppress rendering static simulation alerts over manual mode HUD
            }
            
            // Only update DOM if alerts changed
            const newAlertsJson = JSON.stringify(newAlertsData);
            if (newAlertsJson !== previousAlertsJson) {
                previousAlertsJson = newAlertsJson;
                
                const alertsContainer = document.getElementById('alertsContainer');
                if (alertsContainer && alertsContainer.style.display !== 'none') {
                    alertsContainer.innerHTML = '';
                    
                    const hasLiveConfirmation = alertsData.some(a => a.physical_confirmation === true);
                    const alertsToShow = alertsData.filter(alert => alert['timestamp'] <= currentTimestamp || hasLiveConfirmation);
                    
                    alertsToShow.forEach(alert => {
                        const card = createAlertCardElement(alert);
                        alertsContainer.insertBefore(card, alertsContainer.firstChild);
                    });
                    
                    const alertCountEl = document.getElementById('alertCount');
                    if (alertCountEl) alertCountEl.textContent = alertsToShow.length;
                }
            }
        } catch (error) {
            // Silently ignore transient network fetch glitches
        }
    }, 1000);
}

// ==========================================================================
// Map Initialization & Corridor Styling
// ==========================================================================

function initMap() {
    const centerLat = (CORRIDOR_BOUNDS.latMin + CORRIDOR_BOUNDS.latMax) / 2;
    const centerLon = (CORRIDOR_BOUNDS.lonMin + CORRIDOR_BOUNDS.lonMax) / 2;
    
    map = L.map('map', { 
        keyboard: false,
        zoomControl: true
    }).setView([centerLat, centerLon], 11);
    
    // Tactical dark tile layer — clean, dark, zero watermark
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ | SubseaGuard Sentinel-X C2',
        maxZoom: 16
    }).addTo(map);
    
    markerLayerGroup = L.layerGroup().addTo(map);
    
    // Live Cursor Telemetry Tracking
    map.on('mousemove', (e) => {
        const coordsEl = document.getElementById('cursorCoords');
        if (coordsEl) {
            coordsEl.textContent = `LAT ${e.latlng.lat.toFixed(4)}° N | LON ${e.latlng.lng.toFixed(4)}° E`;
        }
    });
}

function drawCorridorZone() {
    const corridorCoords = [
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMin],
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMax],
        [CORRIDOR_BOUNDS.latMax, CORRIDOR_BOUNDS.lonMax],
        [CORRIDOR_BOUNDS.latMax, CORRIDOR_BOUNDS.lonMin],
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMin]
    ];
    
    L.polygon(corridorCoords, {
        color: '#00f2fe',
        fillColor: '#00f2fe',
        fillOpacity: 0.12,
        weight: 1.5,
        dashArray: '4, 4'
    }).addTo(map).bindPopup('<b>SMW-4 / BBG Protected Cable Corridor</b><br>LAT 13.00-13.10 | LON 80.35-80.50');
    
    // Submarine cable fiber optic line
    const cableLineCoords = [
        [CORRIDOR_BOUNDS.latMin + 0.02, CORRIDOR_BOUNDS.lonMin + 0.02],
        [CORRIDOR_BOUNDS.latMax - 0.02, CORRIDOR_BOUNDS.lonMax - 0.02]
    ];
    
    L.polyline(cableLineCoords, {
        color: '#f59e0b',
        weight: 3.5,
        opacity: 0.95,
        dashArray: '6, 3'
    }).addTo(map).bindPopup('<b>Fiber-Optic Armored Cable Backbone (SMW-4)</b><br>Continuous DAS Acoustic Monitoring Enabled');
}

function getShipColor(label, shipId = '') {
    if (label === 'anomaly' || shipId === 'S5' || shipId === 'S6') {
        return '#ef4444'; // Tactical Crimson / Red
    }
    if (label === 'near_miss' || shipId === 'S7' || shipId === 'S8') {
        return '#f59e0b'; // High-Visibility Amber
    }
    return '#00e5ff'; // Tactical Cyan / Maritime Blue
}

// Precision naval vessel silhouette with sharp wedge bow, parallel beam, squared transom, bridge, and forward hatches
function createShipIcon(color, isAnomaly = false, heading = 0) {
    const size = isAnomaly ? 38 : 30;
    const pulseClass = isAnomaly ? 'ship-pulse' : '';
    const cleanColor = color.replace('#', '');
    
    const svgIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="${size}" height="${size}" style="transform: rotate(${heading}deg); transform-origin: 20px 20px; overflow: visible;">
            <defs>
                <filter id="glow-${cleanColor}" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="${color}" flood-opacity="0.85"/>
                </filter>
            </defs>
            <!-- Angular Naval Hull Outer Shell -->
            <path d="M 20 3 L 23.5 13 L 23.5 33 L 22.5 37 L 17.5 37 L 16.5 33 L 16.5 13 Z" 
                  fill="${color}" 
                  stroke="#ffffff" 
                  stroke-width="1.2" 
                  stroke-linejoin="miter"
                  filter="url(#glow-${cleanColor})" />
            <!-- Longitudinal Keel / Centerline -->
            <line x1="20" y1="5" x2="20" y2="25" stroke="#ffffff" stroke-width="0.7" opacity="0.65"/>
            <!-- Forward Cargo Hatches -->
            <rect x="18.2" y="11" width="3.6" height="4" rx="0.5" fill="#0b1329" stroke="#ffffff" stroke-width="0.6" opacity="0.85"/>
            <rect x="18.2" y="17" width="3.6" height="4" rx="0.5" fill="#0b1329" stroke="#ffffff" stroke-width="0.6" opacity="0.85"/>
            <!-- Aft Superstructure / Bridge Deckhouse (Stern Quarter) -->
            <rect x="17.2" y="26" width="5.6" height="5.5" rx="0.6" fill="#ffffff" stroke="#0b1329" stroke-width="0.7"/>
            <rect x="16.2" y="27.5" width="7.6" height="1.8" rx="0.4" fill="#ffffff" opacity="0.95"/>
            <circle cx="20" cy="33.5" r="0.9" fill="#0b1329"/>
            <!-- Bow Forward Directional Marker -->
            <polygon points="20,4.5 21.5,8 18.5,8" fill="#ffffff" opacity="0.95"/>
        </svg>
    `;

    return L.divIcon({
        className: `custom-ship-marker ${pulseClass}`,
        html: svgIcon,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2]
    });
}

function createPopupContent(shipId, entry, vesselType) {
    return `
        <div class="popup-ship-id">VESSEL ${shipId}</div>
        <div class="popup-detail">SPEED: ${entry['speed']} kts</div>
        <div class="popup-detail">HEADING: ${entry['heading']}°</div>
        <div class="popup-detail">TYPE: ${vesselType.toUpperCase()}</div>
        <div class="popup-detail">STATUS: ${entry['label'].toUpperCase()}</div>
    `;
}

// Stateless frame rendering
function renderFrame(timestamp) {
    markerLayerGroup.clearLayers();
    map.closePopup();
    
    const entriesAtTimestamp = {};
    shipsData.forEach(entry => {
        if (entry['timestamp'] === timestamp) {
            entriesAtTimestamp[entry['ship_id']] = entry;
        }
    });
    
    const allShipIds = new Set();
    shipsData.forEach(entry => allShipIds.add(entry['ship_id']));
    
    allShipIds.forEach(shipId => {
        const entry = entriesAtTimestamp[shipId];
        if (!entry || entry['lat'] == null || entry['lon'] == null) return;
        
        const currentLabel = entry['label'];
        const isAnomaly = currentLabel === 'anomaly' || shipId === 'S5' || shipId === 'S6';
        const isNearMiss = currentLabel === 'near_miss' || shipId === 'S7' || shipId === 'S8';
        const color = getShipColor(currentLabel, shipId);
        const vesselType = entry['vessel_type'] || 'vessel';
        const heading = entry['heading'] || 0;
        
        const marker = L.marker([entry['lat'], entry['lon']], {
            icon: createShipIcon(color, isAnomaly, heading)
        }).addTo(markerLayerGroup);
        
        // Dynamic Z-Index Stacking (Threats top layer, near-miss middle, normal baseline)
        if (isAnomaly) {
            marker.setZIndexOffset(2000);
        } else if (isNearMiss) {
            marker.setZIndexOffset(1000);
        } else {
            marker.setZIndexOffset(100);
        }
        
        marker.bindPopup(createPopupContent(shipId, entry, vesselType));
    });
    
    // Rebuild alert sidebar
    const alertsContainer = document.getElementById('alertsContainer');
    if (alertsContainer && alertsContainer.style.display !== 'none') {
        alertsContainer.innerHTML = '';
        
        const hasLiveConfirmation = alertsData.some(a => a.physical_confirmation === true);
        const alertsToShow = alertsData.filter(alert => alert['timestamp'] <= timestamp || hasLiveConfirmation);
        
        alertsToShow.forEach(alert => {
            const alertCard = createAlertCardElement(alert);
            alertsContainer.insertBefore(alertCard, alertsContainer.firstChild);
        });
        
        const alertCountEl = document.getElementById('alertCount');
        if (alertCountEl) alertCountEl.textContent = alertsToShow.length;
    }
    
    updateDasHardwareBadge(alertsData);
    updateThreatIndex(timestamp);
}

// ==========================================================================
// PART 1: MANUAL CONTROL MODE WITH BIDIRECTIONAL DAS SENSOR FUSION
// ==========================================================================

const manualMode = {
    isActive: false,
    interval: null,
    ship: null,
    hasFlagged: false,
    currentMarker: null,
    handleKeyDown: null,
    
    start: function() {
        console.log('[ManualMode] Entering Tactical Manual Control Mode...');
        
        if (isPlaying) {
            togglePlay();
        }
        
        // Hide simulation alerts, isolate sidebar
        const alertsContainer = document.getElementById('alertsContainer');
        const manualBanner = document.getElementById('manualBanner');
        const manualModeBtn = document.getElementById('manualModeBtn');
        
        if (alertsContainer) alertsContainer.style.display = 'none';
        if (manualBanner) {
            manualBanner.style.display = 'none';
            manualBanner.className = 'manual-banner';
        }
        if (manualModeBtn) manualModeBtn.classList.add('active');
        
        // Clear simulation markers
        markerLayerGroup.clearLayers();
        map.closePopup();
        
        // Initialize user vessel kinematics in open water west of corridor (Bay of Bengal)
        this.ship = {
            lat: 13.05,
            lon: 80.33,
            speed: 10,
            heading: 90
        };
        
        this.isActive = true;
        this.hasFlagged = false;
        
        this.renderMarker();
        
        // Show Cockpit HUD
        const manualHud = document.getElementById('manualHud');
        if (manualHud) {
            manualHud.style.display = 'block';
            manualHud.className = 'manual-hud';
        }
        this.updateHUD();
        
        this.addKeyboardListeners();
        this.startMovementLoop();
    },
    
    renderMarker: function() {
        const color = getShipColor('normal');
        this.currentMarker = L.marker([this.ship.lat, this.ship.lon], {
            icon: createShipIcon(color, false, this.ship.heading || 0)
        }).addTo(markerLayerGroup);
        map.panTo([this.ship.lat, this.ship.lon]);
    },
    
    updateMarker: function(isAnomaly = false) {
        if (this.currentMarker) {
            markerLayerGroup.removeLayer(this.currentMarker);
        }
        const color = isAnomaly ? getShipColor('anomaly') : (this.isInsideCorridor() && this.ship.speed < 5 ? getShipColor('near_miss') : getShipColor('normal'));
        this.currentMarker = L.marker([this.ship.lat, this.ship.lon], {
            icon: createShipIcon(color, isAnomaly, this.ship.heading || 0)
        }).addTo(markerLayerGroup);
    },
    
    addKeyboardListeners: function() {
        this.handleKeyDown = (e) => {
            if (!this.isActive) return;
            
            const step = e.shiftKey ? 0.015 : 0.005;
            let moved = false;
            
            switch(e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    this.ship.lat += step;
                    this.ship.heading = 0;
                    moved = true;
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.ship.lat -= step;
                    this.ship.heading = 180;
                    moved = true;
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.ship.lon -= step;
                    this.ship.heading = 270;
                    moved = true;
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.ship.lon += step;
                    this.ship.heading = 90;
                    moved = true;
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    this.ship.speed = Math.min(25, this.ship.speed + 1);
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    this.ship.speed = Math.max(0, this.ship.speed - 1);
                    break;
            }
            
            this.updateMarker(this.hasFlagged);
            this.updateHUD();
        };
        document.addEventListener('keydown', this.handleKeyDown);
    },
    
    removeKeyboardListeners: function() {
        if (this.handleKeyDown) {
            document.removeEventListener('keydown', this.handleKeyDown);
            this.handleKeyDown = null;
        }
    },
    
    isInsideCorridor: function() {
        return this.ship.lat >= CORRIDOR_BOUNDS.latMin && 
               this.ship.lat <= CORRIDOR_BOUNDS.latMax && 
               this.ship.lon >= CORRIDOR_BOUNDS.lonMin && 
               this.ship.lon <= CORRIDOR_BOUNDS.lonMax;
    },
    
    updateHUD: function() {
        const inCorridor = this.isInsideCorridor();
        const hud = document.getElementById('manualHud');
        const pill = document.getElementById('manualZonePill');
        const speedVal = document.getElementById('manualSpeedVal');
        const headingVal = document.getElementById('manualHeadingVal');
        const posVal = document.getElementById('manualPosVal');
        const riskVal = document.getElementById('manualRiskVal');
        
        if (speedVal) speedVal.textContent = `${this.ship.speed.toFixed(1)} kts`;
        if (headingVal) headingVal.textContent = `${String(this.ship.heading).padStart(3, '0')}°`;
        if (posVal) posVal.textContent = `${this.ship.lat.toFixed(4)}, ${this.ship.lon.toFixed(4)}`;
        
        if (!hud || !pill || !riskVal) return;
        
        if (this.hasFlagged) {
            pill.textContent = 'CRITICAL SEABED STRIKE';
            pill.className = 'hud-mode-pill critical';
            riskVal.textContent = 'CRITICAL';
            riskVal.className = 'stat-val risk-critical';
            hud.className = 'manual-hud critical-strike';
        } else if (inCorridor) {
            if (this.ship.speed < 5) {
                pill.textContent = 'POTENTIAL ANCHOR DRAG';
                pill.className = 'hud-mode-pill in-corridor';
                riskVal.textContent = 'HIGH (AIS ONLY)';
                riskVal.className = 'stat-val risk-warning';
                hud.className = 'manual-hud inside-corridor';
            } else {
                pill.textContent = 'INSIDE CORRIDOR';
                pill.className = 'hud-mode-pill in-corridor';
                riskVal.textContent = 'TRANSITING (SAFE)';
                riskVal.className = 'stat-val risk-nominal';
                hud.className = 'manual-hud inside-corridor';
            }
        } else {
            pill.textContent = 'OUTSIDE CORRIDOR';
            pill.className = 'hud-mode-pill';
            riskVal.textContent = 'NOMINAL';
            riskVal.className = 'stat-val risk-nominal';
            hud.className = 'manual-hud';
        }
    },
    
    // Handles live acoustic DAS transient while in manual control
    handleIncomingAcousticTransient: function(acousticData) {
        if (!this.isActive || this.hasFlagged) return;
        
        const inCorridor = this.isInsideCorridor();
        const freq = acousticData.frequency_hz || 440;
        const energy = Math.round(acousticData.energy || 85000);
        
        // THREAT CONDITION: Inside corridor + Speed < 5 kts + Piezo Tap -> BIMODAL STRIKE CONFIRMED
        if (inCorridor && this.ship.speed < 5) {
            this.flagCriticalSeabedStrike(freq, energy);
        } 
        // NON-THREAT DEFENSIVE CONDITION: Fast transit OR outside corridor -> Prevent false alarm
        else {
            this.displayDefensiveAcousticNotice(freq, energy, inCorridor);
        }
    },
    
    flagCriticalSeabedStrike: function(freq, energy) {
        this.hasFlagged = true;
        if (this.interval) clearInterval(this.interval);
        this.removeKeyboardListeners();
        
        this.updateMarker(true);
        this.updateHUD();
        
        const banner = document.getElementById('manualBanner');
        const icon = document.getElementById('manualBannerIcon');
        const title = document.getElementById('manualBannerTitle');
        const text = document.getElementById('manualBannerText');
        const breakdown = document.getElementById('manualAcousticBreakdown');
        
        banner.className = 'manual-banner manual-flagged';
        banner.style.display = 'block';
        icon.textContent = '🚨';
        title.textContent = 'CRITICAL SEABED STRIKE CONFIRMED';
        text.innerHTML = `<strong>Bimodal sensor fusion engine confirmed a physical seabed strike!</strong> Vessel drifted below 5 knots inside cable corridor and acoustic DAS transient confirmed direct impact.`;
        
        breakdown.style.display = 'block';
        breakdown.innerHTML = `
            <div>ACOUSTIC FREQUENCY : <strong>${freq} Hz</strong></div>
            <div>BURST ENERGY       : <strong>${energy.toLocaleString()} RMS</strong></div>
            <div>LOCATION CHANNEL   : <strong>KP 14.2 // SMW-4 CHENNAI LANDING</strong></div>
        `;
    },
    
    displayDefensiveAcousticNotice: function(freq, energy, inCorridor) {
        const banner = document.getElementById('manualBanner');
        const icon = document.getElementById('manualBannerIcon');
        const title = document.getElementById('manualBannerTitle');
        const text = document.getElementById('manualBannerText');
        const breakdown = document.getElementById('manualAcousticBreakdown');
        
        banner.className = 'manual-banner manual-defensive';
        banner.style.display = 'block';
        icon.textContent = 'ℹ️';
        title.textContent = 'ACOUSTIC TRANSIENT DETECTED — NON-THREAT';
        text.innerHTML = `Acoustic transient recorded on DAS line, but vessel is <strong>${inCorridor ? `cruising at safe speed (${this.ship.speed} kts)` : 'operating safely outside the corridor'}</strong>. Bimodal fusion successfully suppressed a false alarm.`;
        
        breakdown.style.display = 'block';
        breakdown.innerHTML = `
            <div>TRANSIENT DETECTED : <strong>${freq} Hz (${energy.toLocaleString()} RMS)</strong></div>
            <div>FUSION DECISION    : <strong>FALSE POSITIVE REJECTED (SAFE KINEMATICS)</strong></div>
        `;
    },
    
    passCondition: function() {
        if (this.interval) clearInterval(this.interval);
        this.removeKeyboardListeners();
        
        const banner = document.getElementById('manualBanner');
        const icon = document.getElementById('manualBannerIcon');
        const title = document.getElementById('manualBannerTitle');
        const text = document.getElementById('manualBannerText');
        const breakdown = document.getElementById('manualAcousticBreakdown');
        
        banner.className = 'manual-banner manual-passed';
        banner.style.display = 'block';
        icon.textContent = '✅';
        title.textContent = 'CORRIDOR TRANSIT CLEARED';
        text.innerHTML = `Vessel safely transited the protected Chennai Submarine Cable Corridor (LON > 80.50) without triggering an anchor drag alert.`;
        breakdown.style.display = 'none';
    },
    
    startMovementLoop: function() {
        this.interval = setInterval(() => {
            this.updateHUD();
            
            // Check if user safely transited eastward past corridor
            if (this.ship.lon > CORRIDOR_BOUNDS.lonMax && !this.hasFlagged) {
                this.passCondition();
            }
        }, 150);
    },
    
    exit: function() {
        console.log('[ManualMode] Exiting Manual Control Mode...');
        if (this.interval) clearInterval(this.interval);
        this.removeKeyboardListeners();
        
        if (this.currentMarker) {
            markerLayerGroup.removeLayer(this.currentMarker);
            this.currentMarker = null;
        }
        
        const manualHud = document.getElementById('manualHud');
        const manualBanner = document.getElementById('manualBanner');
        const alertsContainer = document.getElementById('alertsContainer');
        const manualModeBtn = document.getElementById('manualModeBtn');
        
        if (manualHud) manualHud.style.display = 'none';
        if (manualBanner) manualBanner.style.display = 'none';
        if (alertsContainer) alertsContainer.style.display = 'flex';
        if (manualModeBtn) manualModeBtn.classList.remove('active');
        
        this.isActive = false;
        this.hasFlagged = false;
        
        renderFrame(currentTimestamp);
    }
};

// ==========================================================================
// Controls & User Event Handlers
// ==========================================================================

function setupEventListeners() {
    document.getElementById('playPauseBtn').addEventListener('click', togglePlay);
    
    const manualBtn = document.getElementById('manualModeBtn');
    if (manualBtn) {
        manualBtn.addEventListener('click', () => {
            if (manualMode.isActive) {
                manualMode.exit();
            } else {
                manualMode.start();
            }
        });
    }
    
    document.getElementById('speedSelect').addEventListener('change', (e) => {
        animationSpeed = parseInt(e.target.value);
        if (isPlaying) {
            clearInterval(playInterval);
            playInterval = setInterval(advanceTimestamp, animationSpeed);
        }
    });
    
    document.getElementById('timestampSlider').addEventListener('input', (e) => {
        currentTimestamp = parseInt(e.target.value);
        updateTimestampDisplay();
        renderFrame(currentTimestamp);
    });
    
    document.getElementById('resetBtn').addEventListener('click', resetAnimation);
    document.getElementById('manualTryAgainBtn').addEventListener('click', () => manualMode.start());
    document.getElementById('manualExitBtn').addEventListener('click', () => manualMode.exit());
}

function togglePlay() {
    isPlaying = !isPlaying;
    const btn = document.getElementById('playPauseBtn');
    const icon = document.getElementById('playIcon');
    const text = document.getElementById('playText');
    
    if (isPlaying) {
        icon.textContent = '⏸';
        if (text) text.textContent = 'PAUSE RUN';
        playInterval = setInterval(advanceTimestamp, animationSpeed);
    } else {
        icon.textContent = '▶';
        if (text) text.textContent = 'RESUME RUN';
        clearInterval(playInterval);
    }
}

function advanceTimestamp() {
    if (currentTimestamp < 20) {
        currentTimestamp++;
        updateTimestampDisplay();
        renderFrame(currentTimestamp);
    } else {
        togglePlay();
    }
}

function updateTimestampDisplay() {
    const currEl = document.getElementById('currentTimestamp');
    const sliderEl = document.getElementById('timestampSlider');
    if (currEl) currEl.textContent = String(currentTimestamp).padStart(2, '0');
    if (sliderEl) sliderEl.value = currentTimestamp;
}

function resetAnimation() {
    if (isPlaying) togglePlay();
    currentTimestamp = 1;
    updateTimestampDisplay();
    renderFrame(currentTimestamp);
}

// Boot application
document.addEventListener('DOMContentLoaded', init);
