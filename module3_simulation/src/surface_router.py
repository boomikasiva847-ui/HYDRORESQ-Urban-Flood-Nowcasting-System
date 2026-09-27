"""Lightweight 2-D urban surface-water routing on the high-resolution DEM."""
from __future__ import annotations

import numpy as np
import rasterio
from pyproj import Transformer


class SurfaceFloodModel:
    """D8 surface routing + manhole drainage/surcharge coupling.

    This is a fast, transparent nowcasting model rather than a replacement for
    a full Saint-Venant solver. Each 5-minute frame adds radar rainfall runoff,
    routes water toward the steepest lower neighbour, and removes water through
    the underground network up to the hydraulic capacity calculated by Module 1.
    """

    def __init__(self, dem_path, manholes, graph, routing_fraction=0.55):
        self.dem_path = dem_path
        self.graph = graph
        self.manholes = manholes.copy()
        with rasterio.open(dem_path) as src:
            self.dem = src.read(1).astype(np.float32)
            self.transform = src.transform
            self.crs = src.crs
            self.nodata = src.nodata
            self.height, self.width = self.dem.shape
        self.cell_area = self._cell_area_m2()
        self.routing_fraction = float(routing_fraction)
        self.downstream = self._build_d8()
        self.node_cells = self._map_nodes()
        self.runoff_coeff_grid = self._build_runoff_coeff_grid()

    def _cell_area_m2(self):
        # For geographic DEMs use a local metres-per-degree approximation.
        if self.crs and self.crs.is_geographic:
            mean_lat = float(np.nanmean(self.manholes["latitude"]))
            dy = abs(float(self.transform.e)) * 111_320.0
            dx = abs(float(self.transform.a)) * 111_320.0 * np.cos(np.deg2rad(mean_lat))
            return max(1.0, dx * dy)
        return max(1.0, abs(float(self.transform.a * self.transform.e)))

    def _build_d8(self):
        z = self.dem
        h, w = z.shape
        best = np.full((h, w), -1, dtype=np.int32)
        best_drop = np.zeros((h, w), dtype=np.float32)
        cell = np.arange(h * w, dtype=np.int32).reshape(h, w)
        for dy, dx, dist in [(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,1.414),(1,1,1.414),(-1,1,1.414),(1,-1,1.414)]:
            src_y0, src_y1 = max(0, -dy), min(h, h - dy)
            src_x0, src_x1 = max(0, -dx), min(w, w - dx)
            yy = slice(src_y0, src_y1); xx = slice(src_x0, src_x1)
            nyy = slice(src_y0 + dy, src_y1 + dy); nxx = slice(src_x0 + dx, src_x1 + dx)
            drop = (z[yy, xx] - z[nyy, nxx]) / dist
            current_best = best_drop[yy, xx]
            mask = drop > current_best
            best_view = best[yy, xx]
            target = cell[nyy, nxx]
            best_view[mask] = target[mask]
            current_best[mask] = drop[mask]
        return best

    def _map_nodes(self):
        result = {}
        for _, row in self.manholes.iterrows():
            x, y = float(row.longitude), float(row.latitude)
            if self.crs and not self.crs.is_geographic:
                x, y = Transformer.from_crs("EPSG:4326", self.crs, always_xy=True).transform(x, y)
            rr, cc = rasterio.transform.rowcol(self.transform, x, y)
            rr, cc = int(rr), int(cc)
            if 0 <= rr < self.height and 0 <= cc < self.width:
                result[str(row.node_id)] = (rr, cc)
        return result


    def _build_runoff_coeff_grid(self):
        """Paint node land-use/runoff coefficients onto local surface patches."""
        grid = np.full((self.height, self.width), 0.85, dtype=np.float32)
        for _, row in self.manholes.iterrows():
            cell = self.node_cells.get(str(row.node_id))
            if cell is None:
                continue
            rr, cc = cell
            coeff = float(row.get("runoff_coefficient", 0.85) or 0.85)
            # Approximate the imperviousness/catchment influence around each inlet.
            radius = 8 if str(row.get("land_use", "")).upper() in {"ROAD", "COMMERCIAL", "CONCRETE"} else 5
            r0, r1 = max(0, rr-radius), min(self.height, rr+radius+1)
            c0, c1 = max(0, cc-radius), min(self.width, cc+radius+1)
            grid[r0:r1, c0:c1] = np.minimum(grid[r0:r1, c0:c1], coeff) if coeff < 0.85 else np.maximum(grid[r0:r1, c0:c1], coeff)
        return np.clip(grid, 0.15, 0.95)

    def _node_capacity(self, node_id):
        if node_id not in self.graph:
            return 0.0
        return float(sum(float(d.get("Q_max", 0.0)) for _, _, d in self.graph.out_edges(node_id, data=True)))

    def step(self, rainfall_mm_hr, dt_seconds=300):
        water = self.water
        # Convert rainfall intensity to water depth during this 5-minute frame.
        rain_m = np.maximum(rainfall_mm_hr, 0.0) / 1000.0 * (dt_seconds / 3600.0) * self.runoff_coeff_grid
        water += rain_m

        # D8 routing: move a fraction of available surface water downhill.
        flat = water.ravel()
        send = flat * self.routing_fraction
        dest = self.downstream.ravel()
        valid = dest >= 0
        np.add.at(flat, dest[valid], send[valid])
        flat[valid] -= send[valid]
        water = flat.reshape(water.shape)

        node_results = []
        for _, row in self.manholes.iterrows():
            node_id = str(row.node_id)
            cell = self.node_cells.get(node_id)
            if cell is None:
                continue
            rr, cc = cell
            # Street/intersection flood depth is the local 3x3 maximum.
            r0, r1 = max(0, rr - 1), min(self.height, rr + 2)
            c0, c1 = max(0, cc - 1), min(self.width, cc + 2)
            local_depth_m = float(np.max(water[r0:r1, c0:c1]))

            capacity = self._node_capacity(node_id)
            available_volume = float(water[rr, cc] * self.cell_area)
            drain_volume = min(available_volume, max(0.0, capacity * dt_seconds))
            if drain_volume > 0:
                water[rr, cc] = max(0.0, water[rr, cc] - drain_volume / self.cell_area)

            after_drain = float(np.max(water[r0:r1, c0:c1]))
            node_results.append({
                "node_id": node_id,
                "surface_depth_cm": after_drain * 100.0,
                "drain_capacity_m3s": capacity,
                "drained_volume_m3": drain_volume,
            })

        # A street depression cannot retain arbitrary metres of water. Excess
        # above 0.60 m is treated as spill leaving the local 2-D cell system,
        # which prevents numerical sink accumulation while retaining severe
        # street-flood states for the dashboard.
        water = np.minimum(water, 0.60)
        self.water = water
        return node_results

    def run(self, rainfall_frames, lead_minutes, initial_water_m=0.0):
        self.water = np.full((self.height, self.width), float(initial_water_m), dtype=np.float32)
        frames = []
        for rainfall, lead in zip(rainfall_frames, lead_minutes):
            frames.append((lead, self.step(rainfall)))
        return frames
