from __future__ import annotations
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
from .surface_router import SurfaceFloodModel

class HydraulicSimulator:
    """Coupled radar-runoff + 2-D surface + directed drainage network model."""
    def __init__(self, graph_path, inflows_csv_path, dem_path=None, manhole_csv_path=None, nowcast_npz_path=None, nowcast_meta_path=None):
        with open(graph_path,'rb') as f: self.graph=pickle.load(f)
        self.df_inflows=pd.read_csv(inflows_csv_path)
        self.dem_path=dem_path; self.manhole_csv_path=manhole_csv_path; self.nowcast_npz_path=nowcast_npz_path; self.nowcast_meta_path=nowcast_meta_path
        self.manholes=pd.read_csv(manhole_csv_path) if manhole_csv_path else self.df_inflows.copy()
        with __import__('rasterio').open(dem_path) as src:
            self.transform=src.transform; self.crs=src.crs; self.dem_shape=(src.height,src.width)
    def _load_nowcast(self):
        data=np.load(self.nowcast_npz_path); rain=data['rainfall_mm_hr']
        meta=json.loads(Path(self.nowcast_meta_path).read_text()) if self.nowcast_meta_path and Path(self.nowcast_meta_path).exists() else {}
        leads=meta.get('lead_time_minutes',[5*(i+1) for i in range(len(rain))])
        return rain,leads
    def _node_cells(self):
        from rasterio.transform import rowcol
        from pyproj import Transformer
        transformer=None
        if self.crs and not self.crs.is_geographic: transformer=Transformer.from_crs('EPSG:4326',self.crs,always_xy=True)
        out={}
        for _,r in self.manholes.iterrows():
            x,y=float(r.longitude),float(r.latitude)
            if transformer: x,y=transformer.transform(x,y)
            rr,cc=rowcol(self.transform,x,y); rr,cc=int(rr),int(cc)
            if 0<=rr<self.dem_shape[0] and 0<=cc<self.dem_shape[1]: out[str(r.node_id)]=(rr,cc)
        return out
    def _network_hydraulics(self, local_q):
        """Route inflow through directed pipes; capacity shortfalls become surcharge/backflow."""
        routed={n:float(q) for n,q in local_q.items()}; surcharge={n:0.0 for n in self.graph.nodes}
        try: order=list(__import__('networkx').topological_sort(self.graph))
        except Exception: order=list(self.graph.nodes)
        for n in order:
            demand=max(0.0,routed.get(n,0.0))
            edges=list(self.graph.out_edges(n,data=True))
            total_cap=sum(float(d.get('Q_max',0.0)) for _,_,d in edges)
            if not edges:
                surcharge[n]=demand; continue
            passed=min(demand,total_cap)
            surcharge[n]=max(0.0,demand-total_cap)
            if passed>0 and total_cap>0:
                for _,v,d in edges:
                    share=passed*(float(d.get('Q_max',0.0))/total_cap)
                    routed[v]=routed.get(v,0.0)+share
        return routed,surcharge
    def run_simulation(self,hours=3,step_minutes=5):
        rainfall,leads=self._load_nowcast(); leads=leads[:int(hours*60/step_minutes)]; rainfall=rainfall[:len(leads)]
        surface=SurfaceFloodModel(self.dem_path,self.manholes,self.graph)
        cells=self._node_cells(); rows=[]
        for frame,lead in zip(rainfall,leads):
            surface_rows=surface.step(frame,dt_seconds=step_minutes*60) if hasattr(surface,'water') else None
            if surface_rows is None:
                surface.water=np.zeros(surface.dem.shape,dtype=np.float32); surface_rows=surface.step(frame,dt_seconds=step_minutes*60)
            surf={r['node_id']:r for r in surface_rows}
            local_q={}
            for _,r in self.manholes.iterrows():
                nid=str(r.node_id); cell=cells.get(nid); intensity=float(frame[cell]) if cell else 0.0
                C=float(r.get('runoff_coefficient',0.85) or 0.85); A=float(r.get('catchment_area_m2',0) or 0)
                local_q[nid]=max(0.0,C*intensity*A/3_600_000.0)
            routed,surcharge=self._network_hydraulics(local_q)
            for _,r in self.manholes.iterrows():
                nid=str(r.node_id); q=local_q[nid]; total_demand=routed.get(nid,q); cap=sum(float(d.get('Q_max',0)) for _,_,d in self.graph.out_edges(nid,data=True)); sur=float(surcharge.get(nid,0)); volume=sur*step_minutes*60; pool=float(r.get('pooling_area_m2',250) or 250); sd=float(surf.get(nid,{}).get('surface_depth_cm',0)); surcharge_depth=volume/max(pool,1)*100; depth=max(sd,surcharge_depth); blocked=depth>15 or sur>0
                rows.append({'timestamp_hour':round(lead/60,4),'lead_time_min':int(lead),'node_id':nid,'latitude':float(r.latitude),'longitude':float(r.longitude),'rainfall_intensity_mm_hr':round(float(frame[cells[nid]]) if nid in cells else 0,3),'Q_in_m3s':round(q,6),'Q_network_demand_m3s':round(total_demand,6),'Q_capacity_m3s':round(cap,6),'drain_utilization_pct':round((total_demand/cap*100) if cap>0 else 0,2),'net_surcharge_m3s':round(sur,6),'backflow_m3s':round(sur,6),'overflow_volume_m3':round(volume,3),'surface_depth_cm':round(sd,2),'surcharge_depth_cm':round(surcharge_depth,2),'flood_depth_cm':round(depth,2),'status':'FLOODED' if depth>15 else ('CAUTION' if depth>=5 else 'SAFE'),'blocked':bool(blocked)})
        return pd.DataFrame(rows)
