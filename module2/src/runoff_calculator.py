# module2/src/runoff_calculator.py

def compute_rational_runoff(df_manholes):
    """
    Calculate runoff inflow using the Rational Method.

    Q = C × I × A

    C = runoff coefficient
    I = rainfall intensity in mm/hr
    A = catchment area in m²

    Q = runoff flow in m³/s
    """

    # Check required columns
    required_columns = [
        "runoff_coefficient",
        "rainfall_intensity_mm_hr",
        "catchment_area_m2"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df_manholes.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # -----------------------------------------
    # Get input values
    # -----------------------------------------

    C = df_manholes["runoff_coefficient"]

    I = df_manholes["rainfall_intensity_mm_hr"]

    A = df_manholes["catchment_area_m2"]

    # -----------------------------------------
    # Rational Method
    # -----------------------------------------
    #
    # I = mm/hr
    # A = m²
    #
    # Convert result to m³/s:
    #
    # Q = C × I × A / 3,600,000
    #

    df_manholes["Q_in"] = (
        C * I * A
    ) / 3_600_000.0

    return df_manholes