// HYDRORESQ presentation helpers for the live flood map.
let hotspotLayer = null;

function updatePresentationHotspots(cycleOffset) {
    if (typeof map === 'undefined') return;
    if (!hotspotLayer) hotspotLayer = L.layerGroup().addTo(map);
    hotspotLayer.clearLayers();

    if (!Array.isArray(cachedForecast)) return;
    const rows = cachedForecast.filter(r => Number(r.cycle_offset_min) === Number(cycleOffset));
    const severe = rows
        .filter(r => Number(r.flood_depth_cm || 0) > 15 || Number(r.blocked))
        .sort((a, b) => Number(b.flood_depth_cm || 0) - Number(a.flood_depth_cm || 0))
        .slice(0, 12);

    severe.forEach(row => {
        const lat = Number(row.latitude);
        const lon = Number(row.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        const depth = Number(row.flood_depth_cm || 0);
        const color = depth > 15 ? '#ff4d5a' : '#ffc857';
        const marker = L.circleMarker([lat, lon], {
            radius: Math.min(13, 7 + depth / 15),
            color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.35
        });
        marker.bindPopup(
            `<strong>Flood hotspot</strong><br>` +
            `Location: ${row.node_id || 'Monitoring point'}<br>` +
            `Forecast: +${cycleOffset} min<br>` +
            `Water depth: <strong>${depth.toFixed(1)} cm</strong>`
        );
        marker.addTo(hotspotLayer);
    });
}

function updateSummaryCards(cycleOffset) {
    const rows = Array.isArray(cachedForecast)
        ? cachedForecast.filter(r => Number(r.cycle_offset_min) === Number(cycleOffset))
        : [];
    const total = rows.length;
    const flooded = rows.filter(r => Number(r.flood_depth_cm || 0) >= 5).length;
    const blocked = rows.filter(r => Number(r.blocked)).length;
    const maxDepth = rows.reduce((m, r) => Math.max(m, Number(r.flood_depth_cm || 0)), 0);

    const totalEl = document.getElementById('total-nodes');
    const floodedEl = document.getElementById('flooded-nodes');
    const blockedEl = document.getElementById('blocked-nodes');
    const maxEl = document.getElementById('max-depth');
    if (totalEl) totalEl.textContent = total || '--';
    if (floodedEl) floodedEl.textContent = flooded || 0;
    if (blockedEl) blockedEl.textContent = blocked || 0;
    if (maxEl) maxEl.textContent = total ? `${maxDepth.toFixed(1)} cm` : '--';
}

const _hydroPresentationRenderCycle = renderCycle;
renderCycle = function(step) {
    _hydroPresentationRenderCycle(step);
    const minutes = getForecastMinutes();
    if (!minutes.length) return;
    const idx = Math.max(0, Math.min(Number(step) || 0, minutes.length - 1));
    const selected = minutes[idx];
    updatePresentationHotspots(selected);
    updateSummaryCards(selected);
};


async function updateRoadSourceBadge() {
    try {
        const res = await fetch('/data/raw/street_network.geojson');
        if (!res.ok) return;
        const data = await res.json();
        const source = String(data?.metadata?.source || 'Unknown');
        const el = document.getElementById('road-source-badge');
        if (!el) return;
        const src = source.toLowerCase();
        if (src.includes('openstreetmap') && !src.includes('fixture') && !src.includes('demo')) {
            el.textContent = 'ROAD DATA: OPENSTREETMAP';
            el.classList.add('online');
            el.classList.remove('warning');
        } else {
            el.textContent = 'ROAD DATA: DEMO FALLBACK';
            el.classList.add('warning');
            el.classList.remove('online');
        }
    } catch (e) {
        console.warn('[Module 5] Road source badge unavailable:', e);
    }
}

document.addEventListener('DOMContentLoaded', updateRoadSourceBadge);
