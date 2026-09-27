// ============================================================
// HYDRORESQ - MODULE 5 FORECAST CORE
// Provides the shared forecast timeline and map rendering used
// by the dashboard, road overlay, slider and routing widgets.
// ============================================================

function getForecastMinutes() {
    if (!Array.isArray(cachedForecast) || !cachedForecast.length) return [];
    return [...new Set(
        cachedForecast
            .map(item => Number(item.cycle_offset_min))
            .filter(Number.isFinite)
    )].sort((a, b) => a - b);
}

function depthColor(depthCm) {
    const depth = Number(depthCm || 0);
    if (depth > 15) return '#ff4d5a';
    if (depth >= 5) return '#ffc857';
    return '#20d889';
}

function depthStatus(depthCm, blocked) {
    if (Number(blocked)) return 'BLOCKED';
    const depth = Number(depthCm || 0);
    if (depth > 15) return 'SEVERE';
    if (depth >= 5) return 'CAUTION';
    return 'SAFE';
}

function updateForecastCards(selectedMinutes) {
    document.querySelectorAll('.forecast-time').forEach(card => {
        card.classList.remove('active');
        const text = card.textContent || '';
        const match = text.match(/\+(\d+)\s*min/i);
        if (match && Number(match[1]) === Number(selectedMinutes)) {
            card.classList.add('active');
        }
    });
}

function renderNodeForecast(cycleOffset) {
    if (typeof nodeMarkersLayer === 'undefined' || !nodeMarkersLayer) return;
    nodeMarkersLayer.clearLayers();

    const rows = cachedForecast.filter(row => Number(row.cycle_offset_min) === Number(cycleOffset));
    rows.forEach(row => {
        const lat = Number(row.latitude);
        const lon = Number(row.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

        const depth = Number(row.flood_depth_cm || 0);
        const blocked = Boolean(row.blocked);
        // Avoid covering the map with green points. Only show locations
        // that need user attention; severe hotspots get an additional halo.
        if (!blocked && depth < 5) return;
        const color = depthColor(depth);
        const status = depthStatus(depth, blocked);

        const marker = L.circleMarker([lat, lon], {
            radius: blocked ? 8 : (depth > 15 ? 7 : 6),
            color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.85
        });

        marker.bindPopup(
            `<strong>${row.node_id || 'Flood point'}</strong>` +
            `<br>Forecast: +${cycleOffset} min` +
            `<br>Water depth: ${depth.toFixed(1)} cm` +
            `<br>Status: ${status}` +
            `<br>Surface depth: ${Number(row.surface_depth_cm || 0).toFixed(1)} cm` +
            `<br>Backflow: ${Number(row.backflow_m3s || 0).toFixed(3)} m³/s`
        );

        marker.addTo(nodeMarkersLayer);
    });
}

function renderCycle(step) {
    const minutes = getForecastMinutes();
    if (!minutes.length) {
        console.warn('[Module 5] No forecast frames available yet.');
        return;
    }

    const numericStep = Number(step);
    const safeIndex = Number.isFinite(numericStep)
        ? Math.max(0, Math.min(Math.round(numericStep), minutes.length - 1))
        : 0;
    const selectedMinutes = minutes[safeIndex];

    const slider = document.getElementById('time-slider');
    if (slider) {
        slider.max = String(minutes.length - 1);
        slider.value = String(safeIndex);
    }

    const label = document.getElementById('slider-time-label');
    if (label) label.textContent = `Forecast +${selectedMinutes} min`;

    updateForecastCards(selectedMinutes);
    renderNodeForecast(selectedMinutes);

    if (typeof renderRoadForecast === 'function') {
        renderRoadForecast(selectedMinutes);
    }

    console.log(`[Module 5] Rendering forecast +${selectedMinutes} min`);
}
