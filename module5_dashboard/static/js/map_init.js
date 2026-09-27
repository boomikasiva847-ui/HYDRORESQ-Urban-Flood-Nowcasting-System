// Initialize Leaflet map with a satellite basemap.
const map = L.map('map').setView([12.980, 80.216], 14);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Imagery © Esri'
}).addTo(map);

let cachedForecast = [];
let streetNetworkLayer = null;
let nodeMarkersLayer = L.layerGroup().addTo(map);
let blockedRoadsLayer = L.layerGroup().addTo(map);

// The OSM basemap already contains the street geometry. We deliberately do NOT
// draw the old drainage-node connector GeoJSON as a road layer because those
// lines can cross homes, parks, water bodies, and other non-road areas.
// Module 5 renders only road forecast geometries supplied by Module 4.
fetch('/data/raw/street_network.geojson')
    .then(res => res.ok ? res.json() : null)
    .then(data => {
        if (!data) return;
        const source = data.metadata?.source || 'Unknown';
        console.log(`[Module 5] Road source: ${source}`);
    })
    .catch(err => console.warn('[Module 5] Road metadata check failed:', err));
