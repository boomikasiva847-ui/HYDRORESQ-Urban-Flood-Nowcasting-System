# Road forecast cycle fix

The Module 3 CSV uses `lead_time_min` (5, 10, ..., 180) while Module 4 uses `cycle_offset_min`.
The road-forecast builder previously read only `cycle_offset_min`, so every Module 3 row defaulted to cycle 0 and the real road forecast collapsed to one cycle.

The corrected builder accepts both fields and normalizes them to `cycle_offset_min`. `run_all.py` now removes any stale road forecast before rebuilding and fails fast unless all 36 forecast cycles are produced.

Expected relationship for an N-segment real road network:

`road forecast records = N * 36`

The road network remains independent from the 50 drainage/manhole node IDs.
