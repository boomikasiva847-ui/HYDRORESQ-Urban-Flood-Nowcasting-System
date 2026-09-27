import os
import json
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.database import SessionLocal
from src.models import ForecastCycle
from src.websocket_manager import manager


# ============================================================
# PATHS
# ============================================================

# module4_backend/src/scheduler.py
#       ↓
# module4_backend
#       ↓
# flood_project
#       ↓
# module3_simulation/data/output/flood_results.csv

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

MODULE3_OUTPUT = os.path.join(
    PROJECT_ROOT,
    "module3_simulation",
    "data",
    "output"
)

FLOOD_RESULTS_PATH = os.path.join(
    MODULE3_OUTPUT,
    "flood_results.csv"
)

MODULE4_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "output"
)

LATEST_FORECAST_PATH = os.path.join(
    MODULE4_OUTPUT,
    "latest_forecast.json"
)
ROAD_FORECAST_PATH = os.path.join(MODULE4_OUTPUT, "road_forecast.json")
ROAD_NETWORK_PATH = os.path.join(PROJECT_ROOT, "module6_routing", "data", "raw", "road_network.geojson")


# ============================================================
# READ MODULE 3 OUTPUT
# ============================================================

def get_forecast_data():

    print("\nReading Module 3 output...")

    # --------------------------------------------------------
    # Check Module 3 file
    # --------------------------------------------------------

    if not os.path.exists(FLOOD_RESULTS_PATH):

        print(
            "ERROR: Module 3 flood results not found:"
        )

        print(
            FLOOD_RESULTS_PATH
        )

        return []

    print(
        "✔ Module 3 file found:"
    )

    print(
        FLOOD_RESULTS_PATH
    )

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    try:

        import pandas as pd

        df = pd.read_csv(
            FLOOD_RESULTS_PATH
        )

    except Exception as e:

        print(
            f"ERROR reading Module 3 output: {e}"
        )

        return []

    print(
        f"✔ Module 3 rows received: {len(df)}"
    )

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required_columns = [
        "timestamp_hour",
        "node_id",
        "latitude",
        "longitude",
        "Q_in_m3s",
        "Q_capacity_m3s",
        "overflow_volume_m3",
        "flood_depth_cm",
        "status"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        print(
            "ERROR: Missing Module 3 columns:"
        )

        print(
            missing_columns
        )

        return []

    print(
        "✔ Module 3 columns verified"
    )

    # --------------------------------------------------------
    # Convert Module 3 data to Module 4 format
    # --------------------------------------------------------

    forecasts = []

    current_time = datetime.now(
        timezone.utc
    ).isoformat()

    for _, row in df.iterrows():

        # Preserve the native 5-minute forecast lead time.
        cycle_offset_min = int(row.get("lead_time_min", round(float(row["timestamp_hour"]) * 60)))

        flood_depth = float(
            row["flood_depth_cm"]
        )

        # Module 4 considers a location blocked
        # when flood depth is greater than 15 cm.

        blocked = (
            flood_depth > 15.0
        )

        forecasts.append({

            "node_id":
                str(row["node_id"]),

            "latitude":
                float(row["latitude"]),

            "longitude":
                float(row["longitude"]),

            "timestamp":
                current_time,

            "cycle_offset_min":
                cycle_offset_min,

            "flood_depth_cm":
                round(
                    flood_depth,
                    2
                ),

            "blocked":
                blocked,

            "status":
                str(row["status"]),

            "Q_in_m3s":
                float(
                    row["Q_in_m3s"]
                ),

            "Q_capacity_m3s":
                float(
                    row["Q_capacity_m3s"]
                ),

            "overflow_volume_m3":
                float(
                    row["overflow_volume_m3"]
                )
        })

    print(
        f"✔ Converted {len(forecasts)} records for Module 4"
    )

    return forecasts


from src.road_forecast_builder import build_road_forecast

# ============================================================
# REFRESH MODULE 4
# ============================================================

async def refresh_cycle():

    print()
    print("=" * 60)
    print("MODULE 4 FORECAST REFRESH")
    print("=" * 60)

    # --------------------------------------------------------
    # Get Module 3 data
    # --------------------------------------------------------

    forecast_data = get_forecast_data()

    if not forecast_data:

        print(
            "No Module 3 forecast data available."
        )

        return

    # --------------------------------------------------------
    # Save latest forecast JSON
    # --------------------------------------------------------

    try:

        os.makedirs(
            MODULE4_OUTPUT,
            exist_ok=True
        )

        with open(
            LATEST_FORECAST_PATH,
            "w"
        ) as f:

            json.dump(
                forecast_data,
                f,
                indent=4
            )

        print(
            "✔ latest_forecast.json updated"
        )
        # The end-to-end build pipeline already generates the real-road forecast
        # before Module 4 starts. Rebuilding 563k+ JSON records again during
        # FastAPI startup can block the event loop long enough for the startup
        # health check to time out on Windows. Reuse a valid existing artifact
        # and only rebuild it when it is missing.
        reuse_existing_road = False
        if os.path.exists(ROAD_FORECAST_PATH):
            try:
                reuse_existing_road = os.path.getsize(ROAD_FORECAST_PATH) > 0
            except OSError:
                reuse_existing_road = False

        if reuse_existing_road:
            print("✔ Reusing prebuilt road forecast artifact")
        else:
            road_data = build_road_forecast(forecast_data)
            if not road_data:
                raise RuntimeError("Road forecast could not be generated from the loaded real road network.")
            with open(ROAD_FORECAST_PATH, "w", encoding="utf-8") as f:
                json.dump(road_data, f, indent=2)
            print("✔ road_forecast.json generated")


    except Exception as e:

        print(
            f"ERROR writing forecast JSON: {e}"
        )

    # --------------------------------------------------------
    # Save to database
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        for data in forecast_data:

            fc = ForecastCycle(

                node_id=data["node_id"],

                timestamp=data["timestamp"],

                cycle_offset_min=
                    data["cycle_offset_min"],

                flood_depth_cm=
                    data["flood_depth_cm"],

                blocked=
                    data["blocked"]
            )

            db.add(fc)

        db.commit()

        print(
            f"✔ Saved {len(forecast_data)} records to database"
        )

    except Exception as e:

        print(
            f"ERROR writing to database: {e}"
        )

        db.rollback()

    finally:

        db.close()

    # --------------------------------------------------------
    # WebSocket broadcast
    # --------------------------------------------------------

    try:

        await manager.broadcast(
            forecast_data
        )

        print(
            "✔ Forecast broadcast completed"
        )

    except Exception as e:

        print(
            f"WebSocket broadcast error: {e}"
        )

    print(
        "✔ Module 4 forecast refresh complete."
    )


# ============================================================
# START SCHEDULER
# ============================================================

def start_scheduler():

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        refresh_cycle,
        "interval",
        minutes=5
    )

    scheduler.start()

    print(
        "✔ Module 4 scheduler started."
    )
    return scheduler
