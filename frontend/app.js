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
    
    map = L.map('map').setView([centerLat, centerLon], 11);
    
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

// Setup event listeners
function setupEventListeners() {
    // Play/Pause button
    document.getElementById('playPauseBtn').addEventListener('click', togglePlay);
    
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
