// ============================================================
// HYDRORESQ - MODULE 5 STREET FLOOD VISUALIZATION
// ============================================================

let roadForecastLayer = null;
let roadGeometryById = new Map();
let roadNetworkSource = "Unknown";

async function loadRoadGeometry() {
    if (roadGeometryById.size) return;
    try {
        const res = await fetch("/data/raw/street_network.geojson");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        roadNetworkSource = String(data?.metadata?.source || "Unknown");
        for (const feature of (data?.features || [])) {
            const p = feature?.properties || {};
            const g = feature?.geometry || {};
            if (g.type === "LineString" && Array.isArray(g.coordinates) && g.coordinates.length >= 2 && p.id) {
                roadGeometryById.set(String(p.id), {
                    geometry: g.coordinates,
                    name: p.name || p.ref || p.fname || p.id,
                    highway: p.highway || p.fclass || "Road"
                });
            }
        }
        console.log(`[Module 5] Loaded ${roadGeometryById.size} real road geometries from ${roadNetworkSource}`);
    } catch (e) {
        console.warn("[Module 5] Real road geometry load failed:", e);
    }
}

function roadColor(depth) {
    if (depth > 15) return '#ff4d5a';
    if (depth >= 5) return '#ffc857';
    return '#20d889';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function renderRoadForecast(cycleOffset) {
    try {
        await loadRoadGeometry();
        const res = await fetch(
            `http://127.0.0.1:8000/road-forecast?cycle_offset_min=${encodeURIComponent(cycleOffset)}&include_all=false&include_geometry=false&min_depth_cm=5`
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const roads = await res.json();
        if (!Array.isArray(roads)) throw new Error('Invalid road forecast response');

        const realRoads = roads.filter(r => {
            const src = String(r.source || roadNetworkSource || '').toLowerCase();
            return !src.includes('demo_from_drainage_alignment');
        });

        const demoOnly = roads.length > 0 && realRoads.length === 0;

        if (roadForecastLayer) roadForecastLayer.remove();
        roadForecastLayer = L.layerGroup().addTo(map);

        // Presentation mode: use the normal OSM basemap for safe roads and
        // highlight only roads that are caution/severe/blocked.
        const affected = [];
        let unmonitoredCount = 0;

        if (demoOnly) {
            updateRoadRiskPanel([], 0, cycleOffset, 'Real road geometry is not loaded. The demo drainage-alignment network is intentionally hidden to avoid drawing false roads.');
            if (typeof streetNetworkLayer !== 'undefined' && streetNetworkLayer) {
                streetNetworkLayer.remove();
                streetNetworkLayer = null;
            }
            return;
        }

        realRoads.forEach(road => {
            const localRoad = roadGeometryById.get(String(road.segment_id));
            if (!localRoad || !Array.isArray(localRoad.geometry) || localRoad.geometry.length < 2) return;

            const latLngs = localRoad.geometry
                .filter(c => Array.isArray(c) && c.length >= 2)
                .map(c => [Number(c[1]), Number(c[0])])
                .filter(c => Number.isFinite(c[0]) && Number.isFinite(c[1]));

            if (latLngs.length < 2) return;

            const depth = Number(road.flood_depth_cm || 0);
            const blocked = Boolean(road.blocked);
            const coverage = String(road.coverage_status || 'MONITORED');
            if (coverage === 'UNMONITORED') { unmonitoredCount += 1; }
            const isAffected = blocked || depth >= 5;
            if (!isAffected) return;

            const status = blocked ? 'BLOCKED' : (depth > 15 ? 'SEVERE' : 'CAUTION');
            const streetName = road.name || localRoad.name || road.street_name || road.segment_id || 'Road segment';
            const color = roadColor(depth);
            const weight = blocked ? 6 : (depth > 15 ? 5 : 3);

            const line = L.polyline(latLngs, {
                color,
                weight,
                opacity: blocked ? 0.96 : (depth > 15 ? 0.9 : 0.58),
                lineCap: 'round',
                lineJoin: 'round',
                dashArray: blocked ? '9,7' : null
            });

            line.bindTooltip(
                `${escapeHtml(streetName)} · ${depth.toFixed(1)} cm`,
                { sticky: true, direction: 'top', opacity: 0.95 }
            );

            line.bindPopup(
                `<strong>${escapeHtml(streetName)}</strong>` +
                `<br>Forecast: +${Number(road.cycle_offset_min || cycleOffset)} min` +
                `<br>Water depth: <strong>${depth.toFixed(1)} cm</strong>` +
                `<br>Status: <strong>${status}</strong>` +
                (road.segment_id ? `<br>Segment: ${escapeHtml(road.segment_id)}` : '')
            );

            line.addTo(roadForecastLayer);
            affected.push({ road, depth, status, streetName });
        });

        // Focus the viewport on the affected forecast area for a presentation-friendly view.
        if (affected.length) {
            const allLatLngs = [];
            affected.forEach(item => {
                const coords = (roadGeometryById.get(String(item.road.segment_id)) || {}).geometry || [];
                coords.forEach(c => {
                    if (Array.isArray(c) && c.length >= 2) allLatLngs.push([Number(c[1]), Number(c[0])]);
                });
            });
            if (allLatLngs.length >= 2) {
                map.fitBounds(L.latLngBounds(allLatLngs), { padding: [36, 36], maxZoom: 15 });
            }
        }

        // Keep the generated demo network hidden when the forecast layer is shown.
        if (typeof streetNetworkLayer !== 'undefined' && streetNetworkLayer) {
            streetNetworkLayer.setStyle({ opacity: 0, weight: 0 });
        }

        affected.sort((a, b) => b.depth - a.depth);
        const critical = affected.slice(0, 6);
        updateRoadRiskPanel(critical, affected.length, cycleOffset, '', unmonitoredCount);

        console.log(`[Module 5] Presentation map rendered ${affected.length} affected real roads for +${cycleOffset} min.`);
    } catch (e) {
        console.warn('[Module 5] Road forecast unavailable:', e);
        updateRoadRiskPanel([], 0, cycleOffset, e.message);
    }
}

document.addEventListener('DOMContentLoaded', loadRoadGeometry);

function updateRoadRiskPanel(roads, affectedCount, cycleOffset, errorMessage = '', unmonitoredCount = 0) {
    const list = document.getElementById('road-risk-list');
    const count = document.getElementById('road-risk-count');
    const hudForecast = document.getElementById('hud-forecast');
    const hudAffected = document.getElementById('hud-affected');

    if (hudForecast) hudForecast.textContent = `Forecast +${cycleOffset} min`;
    if (hudAffected) hudAffected.textContent = `Affected roads: ${affectedCount}`;
    if (count) count.textContent = `${affectedCount} affected`;

    if (!list) return;
    if (errorMessage) {
        list.innerHTML = `<div class="empty-road-risk">Forecast road layer unavailable: ${escapeHtml(errorMessage)}</div>`;
        return;
    }
    if (!roads.length) {
        list.innerHTML = `<div class="empty-road-risk">No monitored road segment exceeds 5 cm at +${cycleOffset} min.${unmonitoredCount ? ` ${unmonitoredCount.toLocaleString()} road segments are outside the current flood-monitoring coverage.` : ''}</div>`;
        return;
    }

    list.innerHTML = roads.map(item => {
        const color = roadColor(item.depth);
        const road = item.road;
        const sourceLabel = road.source === 'demo_from_drainage_alignment' ? 'Prototype segment' : (road.highway || 'Road');
        return `
            <div class="road-risk-item">
                <span class="road-risk-dot" style="background:${color}"></span>
                <div>
                    <div class="road-risk-name">${escapeHtml(item.streetName)}</div>
                    <div class="road-risk-meta">${escapeHtml(item.status)} · ${escapeHtml(sourceLabel)}</div>
                </div>
                <div class="road-risk-depth">${item.depth.toFixed(1)} cm</div>
            </div>`;
    }).join('');
}

