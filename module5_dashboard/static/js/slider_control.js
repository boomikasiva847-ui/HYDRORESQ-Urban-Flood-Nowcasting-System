// ============================================================
// HYDRORESQ - FORECAST TIMELINE CONTROLLER
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const slider = document.getElementById('time-slider');
    const sliderLabel = document.getElementById('slider-time-label');

    if (!slider) {
        console.warn('[Module 5] Time slider not found.');
        return;
    }

    slider.addEventListener('input', event => {
        const step = Number(event.target.value);
        const minutes = getForecastMinutes();
        if (!minutes.length) return;

        const safeStep = Math.max(0, Math.min(step, minutes.length - 1));
        if (sliderLabel) sliderLabel.textContent = `Forecast +${minutes[safeStep]} min`;
        renderCycle(safeStep);
    });

    // Forecast cards represent +60, +120 and +180 minutes in the current UI.
    document.querySelectorAll('.forecast-time').forEach(card => {
        card.addEventListener('click', () => {
            const match = (card.textContent || '').match(/\+(\d+)\s*min/i);
            const targetMinutes = match ? Number(match[1]) : NaN;
            const minutes = getForecastMinutes();
            if (!minutes.length || !Number.isFinite(targetMinutes)) return;

            let bestIndex = 0;
            let bestDiff = Infinity;
            minutes.forEach((m, i) => {
                const diff = Math.abs(m - targetMinutes);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    bestIndex = i;
                }
            });

            slider.value = String(bestIndex);
            if (sliderLabel) sliderLabel.textContent = `Forecast +${minutes[bestIndex]} min`;
            renderCycle(bestIndex);
        });
    });

    console.log('[Module 5] Forecast timeline initialized.');
});
