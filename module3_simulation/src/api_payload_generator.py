import json


def generate_dashboard_payload(
    df_forecast,
    output_json_path
):

    features = []

    # Use the peak hour available in the forecast
    peak_hour = df_forecast[
        "timestamp_hour"
    ].max()

    peak_df = df_forecast[
        df_forecast["timestamp_hour"] == peak_hour
    ]

    for _, row in peak_df.iterrows():

        feature = {

            "type": "Feature",

            "geometry": {

                "type": "Point",

                "coordinates": [
                    float(row["longitude"]),
                    float(row["latitude"])
                ]
            },

            "properties": {

                "node_id": row["node_id"],

                "flood_depth_cm": float(
                    row["flood_depth_cm"]
                ),

                "status": row["status"],

                "Q_in_m3s": float(
                    row["Q_in_m3s"]
                ),

                "Q_capacity_m3s": float(
                    row["Q_capacity_m3s"]
                )
            }
        }

        features.append(feature)

    payload = {

        "type": "FeatureCollection",

        "features": features
    }

    with open(
        output_json_path,
        "w"
    ) as f:

        json.dump(
            payload,
            f,
            indent=4
        )


def generate_routing_exclusion_list(
    df_forecast,
    output_json_path,
    threshold_cm=15.0
):

    blocked_df = df_forecast[
        df_forecast["flood_depth_cm"] >
        threshold_cm
    ]

    blocked_nodes = sorted(
        blocked_df["node_id"]
        .unique()
        .tolist()
    )

    exclusion_data = {

        "threshold_cm": threshold_cm,

        "total_blocked_nodes": len(
            blocked_nodes
        ),

        "blocked_nodes": blocked_nodes
    }

    with open(
        output_json_path,
        "w"
    ) as f:

        json.dump(
            exclusion_data,
            f,
            indent=4
        )