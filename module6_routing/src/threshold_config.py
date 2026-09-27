# User type to flood depth tolerance mapping (cm)
USER_THRESHOLDS = {
    "commuter": 15.0,    # Tolerates up to 15cm flood depth
    "emergency": 30.0,   # Tolerates up to 30cm flood depth (ambulances/trucks)
    "transit": 10.0      # Special case: strict tolerance for buses/public transit
}

def resolve_threshold(user_type: str) -> float:
    """Returns depth tolerance in centimeters based on traveler profile."""
    return USER_THRESHOLDS.get(user_type.lower(), 15.0)