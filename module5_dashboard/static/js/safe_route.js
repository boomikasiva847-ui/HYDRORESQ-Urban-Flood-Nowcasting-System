// ============================================================
// HYDRORESQ - MODULE 5 -> MODULE 6 SAFE ROUTING
// ============================================================

const ROUTING_API = 'http://127.0.0.1:8001';
let routeLayer = null;
let routingNetwork = null;

async function loadRoutingNetwork() {
    try {
        const response = await fetch(`${ROUTING_API}/network`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        routingNetwork = await response.json();

        const origin = document.getElementById('route-origin');
        const destination = document.getElementById('route-destination');
        if (!origin || !destination) return;

        const points = Array.isArray(routingNetwork.monitoring_points) && routingNetwork.monitoring_points.length
            ? routingNetwork.monitoring_points
            : (routingNetwork.nodes || []);
        origin.innerHTML = '';
        destination.innerHTML = '';

        points.forEach(point => {
            const label = `${point.node_id} (${Number(point.latitude).toFixed(4)}, ${Number(point.longitude).toFixed(4)})`;
            const o = new Option(label, point.node_id);
            const d = new Option(label, point.node_id);
            origin.add(o);
            destination.add(d);
        });

        if (points.length > 1) {
            const preferredOrigin = points.find(n => n.node_id === 'MH_VL_016');
            const preferredDestination = points.find(n => n.node_id === 'MH_VL_030');
            origin.value = preferredOrigin ? preferredOrigin.node_id : points[0].node_id;
            destination.value = preferredDestination ? preferredDestination.node_id : points[points.length - 1].node_id;
        }

        setRouteStatus('Module 6 network connected', true);
    } catch (error) {
        console.error('[Module 5] Module 6 network failed:', error);
        setRouteStatus('Module 6 unavailable', false);
    }
}

function setRouteStatus(message, online) {
    const el = document.getElementById('route-status');
    if (!el) return;
    el.textContent = message;
    el.style.color = online ? '#20a464' : '#e74c3c';
}

function clearSafeRoute() {
    if (routeLayer) {
        routeLayer.remove();
        routeLayer = null;
    }
}

function drawSafeRoute(route) {
    clearSafeRoute();
    if (!route.path_coordinates || route.path_coordinates.length < 2) return;

    const latLngs = route.path_coordinates.map(p => [p.latitude, p.longitude]);
    routeLayer = L.polyline(latLngs, {
        color: '#1478c9',
        weight: 8,
        opacity: 0.95
    }).addTo(map);

    routeLayer.bindPopup(`Safe route: ${route.origin} → ${route.destination}<br>ETA: ${route.eta_minutes} min`);
    map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });
}

async function requestSafeRoute() {
    const origin = document.getElementById('route-origin')?.value;
    const destination = document.getElementById('route-destination')?.value;
    const userType = document.getElementById('route-user-type')?.value || 'commuter';
    const result = document.getElementById('route-result');

    if (!origin || !destination) return;
    if (origin === destination) {
        if (result) result.textContent = 'Choose different origin and destination nodes.';
        return;
    }

    const minutes = getForecastMinutes();
    const slider = document.getElementById('time-slider');
    const step = slider ? Number(slider.value) : 0;
    const cycleOffset = minutes.length ? minutes[Math.min(step, minutes.length - 1)] : 60;

    if (result) result.textContent = 'Calculating flood-safe route…';
    setRouteStatus('Routing request in progress…', true);

    try {
        const response = await fetch(`${ROUTING_API}/route`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                origin,
                destination,
                user_type: userType,
                cycle_offset_min: cycleOffset
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

        if (data.status === 'route_found') {
            drawSafeRoute(data);
            const avoided = data.avoided_segments?.length || 0;
            if (result) {
                result.innerHTML = `
                    <strong>Safe route found</strong><br>
                    Forecast: +${data.forecast_offset_min ?? cycleOffset} min<br>
                    User profile: ${data.user_type}<br>
                    ETA: ${data.eta_minutes} min<br>
                    Avoided flooded segments: ${avoided}
                `;
            }
            setRouteStatus('Module 6 route updated', true);
        } else {
            clearSafeRoute();
            if (result) {
                result.innerHTML = `<strong>No safe route</strong><br>All available paths exceed the selected flood-risk threshold.`;
            }
            setRouteStatus('No safe route for this forecast', false);
        }
    } catch (error) {
        console.error('[Module 5] Route request failed:', error);
        if (result) result.textContent = `Routing error: ${error.message}`;
        setRouteStatus('Module 6 unavailable', false);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('calculate-route')?.addEventListener('click', requestSafeRoute);
    document.getElementById('clear-route')?.addEventListener('click', () => {
        clearSafeRoute();
        const result = document.getElementById('route-result');
        if (result) result.textContent = 'Route cleared.';
    });
    loadRoutingNetwork();
});
