async function loadInitialForecast() {
    try {
        const response = await fetch("http://127.0.0.1:8000/forecast");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        cachedForecast = await response.json();
        const minutes = getForecastMinutes();
        const slider = document.getElementById("time-slider");
        if (slider && minutes.length) slider.max = minutes.length - 1;
        renderCycle(0);
        console.log(`[Module 5] Initial Module 4 forecast loaded: ${cachedForecast.length} records / ${minutes.length} frames`);
    } catch (error) {
        console.warn("[Module 5] Initial forecast load failed:", error);
    }
}

document.addEventListener("DOMContentLoaded", loadInitialForecast);
