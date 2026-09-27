"""Run a deterministic audit against the urban-flood challenge requirements."""
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parent
def main():
    meta=json.loads((ROOT/'module2/data/output/radar_nowcast_metadata.json').read_text())
    rows=list(csv.DictReader((ROOT/'module3_simulation/data/output/flood_results.csv').open()))
    roads=json.loads((ROOT/'module4_backend/data/output/road_forecast.json').read_text())
    leads=sorted({int(r['lead_time_min']) for r in rows})
    checks={
      '36 five-minute forecast frames': leads==list(range(5,181,5)),
      'node street depths in cm': all('flood_depth_cm' in r for r in rows),
      'surface + surcharge coupling': all('surface_depth_cm' in r and 'backflow_m3s' in r for r in rows),
      'road forecast': len(roads)>0,
      'road forecast covers all 36 frames': sorted({int(r['cycle_offset_min']) for r in roads})==leads,
      'radar metadata present': 'source' in meta and 'lead_time_minutes' in meta,
    }
    for k,v in checks.items(): print(('PASS' if v else 'FAIL')+' - '+k)
    if not all(checks.values()): raise SystemExit(1)
if __name__=='__main__': main()
