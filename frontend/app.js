// SubseaGuard - Main Application JavaScript

// Global state
let map;
let shipsData = [];
let alertsData = [];
let markerLayerGroup;
let currentTimestamp = 1;
let isPlaying = false;
let playInterval = null;
let animationSpeed = 1000;

// Corridor zone boundaries (from geofence.py)
// Must match exactly: CORRIDOR_LAT_MIN/MAX and CORRIDOR_LON_MIN/MAX
const CORRIDOR_BOUNDS = {
    latMin: 13.00,
    latMax: 13.10,
    lonMin: 80.35,
    lonMax: 80.50
};

// Initialize the application
async function init() {
    try {
        // Load data
        await loadData();
        
        // Initialize map
        initMap();
        
        // Draw corridor zone
        drawCorridorZone();
        
        // Setup event listeners
        setupEventListeners();
        
        // Render initial frame
        renderFrame(currentTimestamp);
        
        console.log('SubseaGuard initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
        alert('Error initializing application. Please check console for details.');
    }
}

// Load data from JSON files
async function loadData() {
    try {
        const shipsResponse = await fetch('../data/ships_data.json');
        shipsData = await shipsResponse.json();
        
        const alertsResponse = await fetch('../backend/alerts.json');
        alertsData = await alertsResponse.json();
        
        console.log(`Loaded ${shipsData.length} ship records and ${alertsData.length} alerts`);
    } catch (error) {
        console.error('Error loading data:', error);
        throw error;
    }
}

// Initialize Leaflet map
function initMap() {
    // Center on corridor zone with appropriate zoom
    const centerLat = (CORRIDOR_BOUNDS.latMin + CORRIDOR_BOUNDS.latMax) / 2;
    const centerLon = (CORRIDOR_BOUNDS.lonMin + CORRIDOR_BOUNDS.lonMax) / 2;
    
    map = L.map('map', { keyboard: false }).setView([centerLat, centerLon], 11);
    
    // Add CartoDB Dark Matter tile layer (dark land, blue water, no API key needed)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
    
    // Create marker layer group for ship markers
    markerLayerGroup = L.layerGroup().addTo(map);
}

// Draw the corridor zone polygon
function drawCorridorZone() {
    const corridorCoords = [
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMin],
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMax],
        [CORRIDOR_BOUNDS.latMax, CORRIDOR_BOUNDS.lonMax],
        [CORRIDOR_BOUNDS.latMax, CORRIDOR_BOUNDS.lonMin],
        [CORRIDOR_BOUNDS.latMin, CORRIDOR_BOUNDS.lonMin]
    ];
    
    L.polygon(corridorCoords, {
        color: '#e94560',
        fillColor: '#e94560',
        fillOpacity: 0.15,
        weight: 2
    }).addTo(map).bindPopup('Protected Cable Corridor');
    
    // Add decorative submarine cable line (purely visual, does not affect geofence logic)
    const cableLineCoords = [
        [CORRIDOR_BOUNDS.latMin + 0.02, CORRIDOR_BOUNDS.lonMin + 0.02],  // Shore landing point
        [CORRIDOR_BOUNDS.latMax - 0.02, CORRIDOR_BOUNDS.lonMax - 0.02]   // Open sea landing point
    ];
    
    L.polyline(cableLineCoords, {
        color: '#f4c542',
        weight: 4,
        opacity: 0.9
    }).addTo(map);
    
    // Add landing point markers (decorative)
    const landingPointIcon = L.divIcon({
        className: 'landing-point',
        html: `<div style="
            width: 8px;
            height: 8px;
            background: #333333;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        "></div>`,
        iconSize: [8, 8],
        iconAnchor: [4, 4]
    });
    
    L.marker(cableLineCoords[0], { icon: landingPointIcon }).addTo(map).bindPopup('Shore Landing Point');
    L.marker(cableLineCoords[1], { icon: landingPointIcon }).addTo(map).bindPopup('Sea Landing Point');
}

// Get ship color based on label
function getShipColor(label) {
    switch (label) {
        case 'anomaly':
            return '#e94560'; // Red
        case 'near_miss':
            return '#f39c12'; // Amber/Yellow
        case 'normal':
        default:
            return '#2ecc71'; // Green
    }
}

// Create custom ship marker icon
function createShipIcon(color, isAnomaly = false) {
    const size = isAnomaly ? 24 : 20;
    
    return L.divIcon({
        className: 'ship-marker' + (isAnomaly ? ' anomaly' : ''),
        html: `<div style="
            width: ${size}px;
            height: ${size}px;
            ${isAnomaly ? 'animation: pulse-marker 1s infinite;' : ''}
        ">
            <svg viewBox="0 0 24 24" width="${size}" height="${size}" style="fill: ${color}; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
                <path d="M2 18 L2 16 L4 14 L20 14 L22 16 L22 18 Z M12 14 L12 4 L16 6 L12 8 Z"/>
            </svg>
        </div>`,
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2]
    });
}

// Create popup content
function createPopupContent(shipId, entry, vesselType) {
    return `
        <div class="popup-ship-id">${shipId}</div>
        <div class="popup-detail">Speed: ${entry['speed']} knots</div>
        <div class="popup-detail">Heading: ${entry['heading']}°</div>
        <div class="popup-detail">Type: ${vesselType}</div>
        <div class="popup-detail">Status: ${entry['label']}</div>
    `;
}

// Stateless frame rendering - completely rebuilds markers and alerts each frame
function renderFrame(timestamp) {
    // Step 1: Clear all existing markers
    markerLayerGroup.clearLayers();
    
    // Step 2: Close any open popups
    map.closePopup();
    
    // Step 3: Build lookup for this timestamp
    const entriesAtTimestamp = {};
    shipsData.forEach(entry => {
        if (entry['timestamp'] === timestamp) {
            entriesAtTimestamp[entry['ship_id']] = entry;
        }
    });
    
    // Step 4: Get all unique ship IDs from data
    const allShipIds = new Set();
    shipsData.forEach(entry => allShipIds.add(entry['ship_id']));
    
    // Step 5: Create one marker per ship for this timestamp
    let markerCount = 0;
    allShipIds.forEach(shipId => {
        const entry = entriesAtTimestamp[shipId];
        
        if (!entry) {
            console.warn(`No data for ${shipId} at timestamp ${timestamp}`);
            return;
        }
        
        // Validate coordinates
        if (entry['lat'] == null || entry['lon'] == null) {
            console.warn(`Missing coordinates for ${shipId} at timestamp ${timestamp}`);
            return;
        }
        
        // Log coordinates for debugging
        console.log(`Frame ${timestamp}: Ship ${shipId} at [${entry['lat']}, ${entry['lon']}]`);
        
        // Determine color and icon based on current frame's label ONLY
        const currentLabel = entry['label'];
        const isAnomaly = currentLabel === 'anomaly';
        const color = getShipColor(currentLabel);
        const vesselType = entry['vessel_type'] || 'unknown';
        
        // Create marker
        const marker = L.marker([entry['lat'], entry['lon']], {
            icon: createShipIcon(color, isAnomaly)
        }).addTo(markerLayerGroup);
        
        markerCount++;
        
        // Add popup
        marker.bindPopup(createPopupContent(shipId, entry, vesselType));
    });
    
    // Log total marker count
    console.log(`Frame ${timestamp}: Total markers created = ${markerCount}, Layer group layers = ${markerLayerGroup.getLayers().length}`);
    
    // Step 6: Rebuild alert sidebar statelessly
    const alertsContainer = document.getElementById('alertsContainer');
    alertsContainer.innerHTML = '';
    
    // Show only alerts where alert.timestamp <= current timestamp
    const alertsToShow = alertsData.filter(alert => alert['timestamp'] <= timestamp);
    
    alertsToShow.forEach(alert => {
        const alertCard = document.createElement('div');
        alertCard.className = 'alert-card';
        alertCard.id = `alert-${alert['ship_id']}-${alert['timestamp']}`;
        
        const confidencePercent = alert['confidence_score'] || 0;
        
        alertCard.innerHTML = `
            <div class="alert-card-header">
                <span class="alert-ship-id">${alert['ship_id']}</span>
                <span class="alert-timestamp">T${alert['timestamp']}</span>
            </div>
            <div class="alert-message">${alert['message']}</div>
            <div class="confidence-section">
                <span class="confidence-label">Confidence:</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                </div>
                <span class="confidence-value">${confidencePercent.toFixed(1)}%</span>
            </div>
        `;
        
        // Insert at the top
        alertsContainer.insertBefore(alertCard, alertsContainer.firstChild);
    });
    
    // Update alert count
    document.getElementById('alertCount').textContent = alertsToShow.length;
}

// Manual Control Mode - Isolated namespace
const manualMode = {
    isActive: false,
    interval: null,
    ship: null,
    hasFlagged: false,
    
    start: function() {
        console.log('[ManualMode] Executing start()...');
        
        // Step 2a: If main simulation is playing, stop it
        if (isPlaying) {
            console.log('[ManualMode] Stopping playback...');
            togglePlay();
        }
        
        // Step 2b: Hide alert sidebar content, show manual banner
        console.log('[ManualMode] Hiding alerts, showing banner...');
        const alertsContainer = document.getElementById('alertsContainer');
        const manualBanner = document.getElementById('manualBanner');
        const manualBannerText = document.getElementById('manualBannerText');
        const manualTryAgainBtn = document.getElementById('manualTryAgainBtn');
        
        if (!alertsContainer) console.error('[ManualMode] alertsContainer not found!');
        if (!manualBanner) console.error('[ManualMode] manualBanner not found!');
        if (!manualBannerText) console.error('[ManualMode] manualBannerText not found!');
        if (!manualTryAgainBtn) console.error('[ManualMode] manualTryAgainBtn not found!');
        
        if (alertsContainer) alertsContainer.style.display = 'none';
        if (manualBanner) manualBanner.style.display = 'block';
        if (manualBanner) manualBanner.className = 'manual-banner';
        if (manualBannerText) manualBannerText.textContent = '';
        if (manualTryAgainBtn) manualTryAgainBtn.style.display = 'none';
        
        // Step 2c: Clear existing markers
        console.log('[ManualMode] Clearing markers...');
        markerLayerGroup.clearLayers();
        map.closePopup();
        
        // Step 2d: Create ship state
        console.log('[ManualMode] Creating ship state...');
        this.ship = {
            lat: 13.05,
            lon: 80.32,
            speed: 10,
            heading: 90
        };
        
        // Step 2e: Render initial marker
        console.log('[ManualMode] Rendering marker at', this.ship.lat, this.ship.lon);
        this.renderMarker();
        
        // Show HUD
        console.log('[ManualMode] Showing HUD...');
        const manualHud = document.getElementById('manualHud');
        if (!manualHud) console.error('[ManualMode] manualHud not found!');
        if (manualHud) manualHud.style.display = 'block';
        this.updateHUD();
        
        // Set active flag
        this.isActive = true;
        this.hasFlagged = false;
        
        // Add keyboard listeners
        console.log('[ManualMode] Adding keyboard listeners...');
        this.addKeyboardListeners();
        
        // Start movement loop
        console.log('[ManualMode] Starting movement loop...');
        this.startMovementLoop();
        
        console.log('[ManualMode] start() completed successfully');
    },
    
    renderMarker: function() {
        console.log('[ManualMode] renderMarker() called with lat:', this.ship.lat, 'lon:', this.ship.lon);
        const color = getShipColor('normal');
        const marker = L.marker([this.ship.lat, this.ship.lon], {
            icon: createShipIcon(color, false)
        }).addTo(markerLayerGroup);
        
        this.currentMarker = marker;
        console.log('[ManualMode] Marker created and added to layer group. Layer count:', markerLayerGroup.getLayers().length);
        
        // Pan map to the manual ship position to make it visible
        map.panTo([this.ship.lat, this.ship.lon]);
    },
    
    updateMarker: function() {
        if (this.currentMarker) {
            markerLayerGroup.removeLayer(this.currentMarker);
        }
        
        const color = this.hasFlagged ? getShipColor('anomaly') : getShipColor('normal');
        const isAnomaly = this.hasFlagged;
        
        this.currentMarker = L.marker([this.ship.lat, this.ship.lon], {
            icon: createShipIcon(color, isAnomaly)
        }).addTo(markerLayerGroup);
    },
    
    addKeyboardListeners: function() {
        this.handleKeyDown = (e) => {
            if (!this.isActive) return;
            
            const step = e.shiftKey ? 0.015 : 0.005;
            
            switch(e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    this.ship.lat += step;
                    console.log('[ManualMode] ArrowUp: lat =', this.ship.lat.toFixed(4), 'lon =', this.ship.lon.toFixed(4));
                    this.updateMarker();
                    this.updateHUD();
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.ship.lat -= step;
                    console.log('[ManualMode] ArrowDown: lat =', this.ship.lat.toFixed(4), 'lon =', this.ship.lon.toFixed(4));
                    this.updateMarker();
                    this.updateHUD();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.ship.lon -= step;
                    console.log('[ManualMode] ArrowLeft: lat =', this.ship.lat.toFixed(4), 'lon =', this.ship.lon.toFixed(4));
                    this.updateMarker();
                    this.updateHUD();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.ship.lon += step;
                    console.log('[ManualMode] ArrowRight: lat =', this.ship.lat.toFixed(4), 'lon =', this.ship.lon.toFixed(4));
                    this.updateMarker();
                    this.updateHUD();
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    this.ship.speed = Math.min(20, this.ship.speed + 1);
                    console.log('[ManualMode] Speed increased to', this.ship.speed);
                    this.updateHUD();
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    this.ship.speed = Math.max(0, this.ship.speed - 1);
                    console.log('[ManualMode] Speed decreased to', this.ship.speed);
                    this.updateHUD();
                    break;
            }
        };
        
        document.addEventListener('keydown', this.handleKeyDown);
    },
    
    removeKeyboardListeners: function() {
        if (this.handleKeyDown) {
            document.removeEventListener('keydown', this.handleKeyDown);
            this.handleKeyDown = null;
        }
    },
    
    updateHUD: function() {
        const insideCorridor = this.isInsideCorridor();
        const hud = document.getElementById('manualHud');
        hud.textContent = `Speed: ${this.ship.speed} kt | Position: ${insideCorridor ? 'INSIDE' : 'OUTSIDE'} corridor`;
        
        if (insideCorridor) {
            hud.classList.add('inside-corridor');
        } else {
            hud.classList.remove('inside-corridor');
        }
    },
    
    isInsideCorridor: function() {
        return this.ship.lat >= CORRIDOR_BOUNDS.latMin && 
               this.ship.lat <= CORRIDOR_BOUNDS.latMax && 
               this.ship.lon >= CORRIDOR_BOUNDS.lonMin && 
               this.ship.lon <= CORRIDOR_BOUNDS.lonMax;
    },
    
    startMovementLoop: function() {
        // Movement loop now only checks detection and updates HUD
        // Position changes only on keypress (direct control)
        this.interval = setInterval(() => {
            // Update HUD
            this.updateHUD();
            
            // Detection check: speed represents current movement rate (boosted via Shift = fast/safe, normal = slow/risky)
            if (this.isInsideCorridor() && this.ship.speed < 5 && !this.hasFlagged) {
                this.flagAnomaly();
                return;
            }
            
            // Pass condition
            if (this.ship.lon > CORRIDOR_BOUNDS.lonMax && !this.hasFlagged) {
                this.passCondition();
                return;
            }
        }, 200);
    },
    
    flagAnomaly: function() {
        // Stop the loop
        clearInterval(this.interval);
        this.interval = null;
        
        // Set flagged state
        this.hasFlagged = true;
        
        // Change marker to red + pulse
        this.updateMarker();
        
        // Show banner
        const banner = document.getElementById('manualBanner');
        banner.className = 'manual-banner manual-flagged';
        document.getElementById('manualBannerText').textContent = 
            `🚨 FLAGGED — Anchor drag detected inside cable corridor at ${this.ship.speed} knots`;
        document.getElementById('manualTryAgainBtn').style.display = 'inline-block';
        
        // Remove keyboard listeners
        this.removeKeyboardListeners();
    },
    
    passCondition: function() {
        // Stop the loop
        clearInterval(this.interval);
        this.interval = null;
        
        // Show banner
        const banner = document.getElementById('manualBanner');
        banner.className = 'manual-banner manual-passed';
        document.getElementById('manualBannerText').textContent = 
            '✅ PASSED — Vessel transited corridor without triggering an alert';
        document.getElementById('manualTryAgainBtn').style.display = 'inline-block';
        
        // Remove keyboard listeners
        this.removeKeyboardListeners();
    },
    
    exit: function() {
        console.log('[ManualMode] exit() called...');
        
        // Step 7a: Stop interval and remove listeners
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.removeKeyboardListeners();
        
        // Step 7b: Explicitly remove manual marker before clearing layers
        if (this.currentMarker) {
            markerLayerGroup.removeLayer(this.currentMarker);
            this.currentMarker = null;
        }
        
        // Clear all remaining markers
        markerLayerGroup.clearLayers();
        
        // Step 7c: Restore alert sidebar
        document.getElementById('alertsContainer').style.display = 'block';
        document.getElementById('manualBanner').style.display = 'none';
        document.getElementById('manualHud').style.display = 'none';
        
        // Step 7d: Render original simulation
        renderFrame(currentTimestamp);
        
        // Verify marker count is exactly 8
        console.log('[ManualMode] After exit, marker count:', markerLayerGroup.getLayers().length);
        
        // Step 7e: Hide manual mode UI (already done above)
        
        // Reset active flag
        this.isActive = false;
        this.hasFlagged = false;
        
        console.log('[ManualMode] exit() completed');
    }
};

// Setup event listeners
function setupEventListeners() {
    console.log('[DEBUG] setupEventListeners() executing...');
    
    // Play/Pause button
    document.getElementById('playPauseBtn').addEventListener('click', togglePlay);
    
    // Manual Mode button
    const manualBtn = document.getElementById('manualModeBtn');
    if (manualBtn) {
        manualBtn.addEventListener('click', () => {
            console.log('[ManualMode] Button clicked!');
            manualMode.start();
        });
    } else {
        console.error('[ManualMode] Button element not found in DOM!');
    }
    
    // Speed control
    document.getElementById('speedSelect').addEventListener('change', (e) => {
        animationSpeed = parseInt(e.target.value);
        
        // Restart interval if playing
        if (isPlaying) {
            clearInterval(playInterval);
            playInterval = setInterval(advanceTimestamp, animationSpeed);
        }
    });
    
    // Timestamp slider
    document.getElementById('timestampSlider').addEventListener('input', (e) => {
        currentTimestamp = parseInt(e.target.value);
        updateTimestampDisplay();
        renderFrame(currentTimestamp);
    });
    
    // Reset button
    document.getElementById('resetBtn').addEventListener('click', resetAnimation);
    
    // Manual mode buttons
    document.getElementById('manualTryAgainBtn').addEventListener('click', () => manualMode.start());
    document.getElementById('manualExitBtn').addEventListener('click', () => manualMode.exit());
}

// Toggle play/pause
function togglePlay() {
    isPlaying = !isPlaying;
    const btn = document.getElementById('playPauseBtn');
    const icon = document.getElementById('playIcon');
    
    if (isPlaying) {
        btn.innerHTML = '<span id="playIcon">⏸</span> Pause';
        playInterval = setInterval(advanceTimestamp, animationSpeed);
    } else {
        btn.innerHTML = '<span id="playIcon">▶</span> Play';
        clearInterval(playInterval);
    }
}

// Advance to next timestamp
function advanceTimestamp() {
    if (currentTimestamp < 20) {
        currentTimestamp++;
        updateTimestampDisplay();
        renderFrame(currentTimestamp);
    } else {
        // Stop at end
        togglePlay();
    }
}

// Update timestamp display
function updateTimestampDisplay() {
    document.getElementById('currentTimestamp').textContent = currentTimestamp;
    document.getElementById('timestampSlider').value = currentTimestamp;
}

// Reset animation
function resetAnimation() {
    if (isPlaying) {
        togglePlay();
    }
    
    currentTimestamp = 1;
    updateTimestampDisplay();
    renderFrame(currentTimestamp);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
