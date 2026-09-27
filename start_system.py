"""Start the complete HYDRORESQ six-module system.

Flow:
    Module 1 -> Module 2 -> Module 3 -> Module 4 -> Module 5 -> Module 6

Run from the flood_project directory:
    python start_system.py

Stop with Ctrl+C; child API/dashboard processes are terminated together.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SERVICES = {
    "Module 4 Forecast API": {"module_dir": "module4_backend", "port": 8000, "app_module": "main:app", "health_path": "/health"},
    "Module 6 Safe Routing API": {"module_dir": "module6_routing", "port": 8001, "app_module": "server:app", "health_path": "/health"},
    "Module 5 GIS Dashboard": {"module_dir": "module5_dashboard", "port": 8005, "app_module": "server:app", "health_path": "/health"},
}


def run_pipeline() -> None:
    print("=" * 70)
    print("HYDRORESQ - BUILDING MODULE 1 -> MODULE 3 DATA PIPELINE")
    print("=" * 70)
    subprocess.run([sys.executable, str(ROOT / "run_all.py")], cwd=ROOT, check=True)


def port_is_available(port: int) -> bool:
    """Return True when localhost can bind the requested TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for_service(name: str, process: subprocess.Popen, url: str, timeout_seconds: int = 90):
    """Wait for a real HTTP 2xx readiness response."""
    deadline = time.time() + timeout_seconds
    last_error = "unknown error"

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{name} stopped during startup (exit code {process.returncode})."
            )
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "HYDRORESQ-startup-check/1.0"})
            with urllib.request.urlopen(request, timeout=5) as response:
                if 200 <= response.status < 300:
                    print(f"[READY] {name} ({url})")
                    return process
                last_error = f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(1)

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    raise RuntimeError(f"{name} did not become ready at {url}. Last check: {last_error}")


def start_service(name: str, module_dir: str, port: int, app_module: str, health_path: str = "/health"):
    if not port_is_available(port):
        raise RuntimeError(
            f"Port {port} is already in use, so {name} cannot start. "
            f"Stop the existing service/process using port {port} and run start_system.py again."
        )

    cwd = ROOT / module_dir
    print(f"[START] {name} -> http://127.0.0.1:{port}")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", app_module, "--host", "0.0.0.0", "--port", str(port), "--loop", "asyncio"],
        cwd=cwd,
    )
    url = f"http://127.0.0.1:{port}{health_path}"
    return wait_for_service(name, process, url)


def stop_services(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def main() -> None:
    processes: list[subprocess.Popen] = []
    try:
        subprocess.run([sys.executable, str(ROOT / "preflight_check.py")], cwd=ROOT, check=True)
        run_pipeline()
        subprocess.run([sys.executable, str(ROOT / "integration_check.py")], cwd=ROOT, check=True)

        processes.append(start_service(**{**SERVICES["Module 4 Forecast API"], "name": "Module 4 Forecast API"}))
        try:
            deadline = time.time() + 45
            road_summary = None
            last_summary_error = None
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8000/road-forecast/summary?cycle_offset_min=60", timeout=15) as response:
                        candidate = __import__('json').load(response)
                    if isinstance(candidate, dict) and candidate.get('status') == 'ok':
                        road_summary = candidate
                        break
                    last_summary_error = "Module 4 returned an empty road summary."
                except Exception as probe_error:
                    last_summary_error = probe_error
                time.sleep(1)
            if road_summary is None:
                raise RuntimeError(f"Module 4 returned no road forecast summary within 45 seconds: {last_summary_error}")
            source = str(road_summary.get('source', ''))
            source_text = source.lower()
            real_source = (('openstreetmap' in source_text or 'municipal' in source_text or 'external road' in source_text)
                            and 'demo_from_drainage_alignment' not in source_text
                            and 'sample_osm_fixture' not in source_text)
            if not real_source:
                raise RuntimeError("Module 4 road forecast is not based on the loaded real OSM/municipal network.")
            if int(road_summary.get('segments', 0)) <= 0:
                raise RuntimeError("Module 4 returned zero road segments at +60 min.")
            print(f"[READY] Module 4 real road forecast: {road_summary.get('segments')} segments, {road_summary.get('affected_segments')} affected at +60 min")
        except Exception as exc:
            raise RuntimeError(f"Module 4 road-forecast verification failed: {exc}") from exc
        time.sleep(1)
        processes.append(start_service(**{**SERVICES["Module 6 Safe Routing API"], "name": "Module 6 Safe Routing API"}))
        # Verify Module 6 has a genuine road network, not the synthetic drainage fallback.
        try:
            with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=5) as response:
                health = __import__('json').load(response)
            if not health.get("real_road_data"):
                raise RuntimeError("Module 6 started, but real OSM/municipal road geometry is not loaded.")
            print(f"[READY] Module 6 real road network: {health.get('nodes', 0)} graph nodes")
        except Exception as exc:
            raise RuntimeError(f"Module 6 real-road verification failed: {exc}") from exc
        time.sleep(1)
        processes.append(start_service(**{**SERVICES["Module 5 GIS Dashboard"], "name": "Module 5 GIS Dashboard"}))

        print("\n" + "=" * 70)
        print("HYDRORESQ SIX-MODULE SYSTEM IS RUNNING")
        print("=" * 70)
        print("Module 4 Forecast API : http://127.0.0.1:8000")
        print("Module 6 Routing API  : http://127.0.0.1:8001")
        print("Module 5 Dashboard    : http://127.0.0.1:8005")
        print("\nOpen the dashboard at http://127.0.0.1:8005")
        print("Press Ctrl+C to stop all services.")

        while True:
            dead = [p for p in processes if p.poll() is not None]
            if dead:
                raise RuntimeError("A HYDRORESQ service stopped unexpectedly.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping HYDRORESQ services...")
    except Exception as exc:
        print(f"\n[STARTUP ERROR] {exc}")
        raise
    finally:
        stop_services(processes)


if __name__ == "__main__":
    main()
