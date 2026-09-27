import numpy as np

def calculate_pipe_capacity(diameter_m: float, slope: float, mannings_n: float = 0.013, blockage_factor: float = 0.0) -> float:
    """Full-pipe Manning capacity with blockage_factor interpreted as blocked fraction.

    blockage_factor=0.0 means no blockage; 0.25 means 25% of hydraulic capacity is lost.
    """
    effective_slope = max(float(slope), 0.001)
    radius = float(diameter_m) / 2.0
    area = np.pi * radius ** 2
    perimeter = 2.0 * np.pi * radius
    hydraulic_radius = area / perimeter
    blockage = min(max(float(blockage_factor), 0.0), 0.95)
    effective_capacity_fraction = 1.0 - blockage
    q_max = (1.0 / float(mannings_n)) * area * hydraulic_radius ** (2.0 / 3.0) * effective_slope ** 0.5 * effective_capacity_fraction
    return round(float(q_max), 4)
