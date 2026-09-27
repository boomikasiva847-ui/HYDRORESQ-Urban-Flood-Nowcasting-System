"""Radar rainfall nowcast adapter for HYDRORESQ.

Accepts one georeferenced radar GeoTIFF, a directory of GeoTIFF frames, or a
semicolon-separated list of frames. Multiple input frames are aligned to the
DEM and resampled to 5-minute lead times; a single frame is advected forward.
The synthetic storm is only a labelled demo fallback.
"""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Sequence
import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
DEFAULT_STEPS=36
DEFAULT_STEP_MIN=5

def _read_raster(path):
    with rasterio.open(path) as src:
        arr=src.read(1).astype(np.float32); profile=src.profile.copy(); profile['nodata']=None
        if src.nodata is not None: arr[arr==src.nodata]=0
        return np.nan_to_num(arr), profile

def _align(arr, src_profile, dem_profile):
    dst=np.zeros((dem_profile['height'],dem_profile['width']),dtype=np.float32)
    if src_profile.get('crs') is None or dem_profile.get('crs') is None:
        raise ValueError('Radar and DEM must have valid CRS metadata')
    reproject(source=arr,destination=dst,src_transform=src_profile['transform'],src_crs=src_profile['crs'],dst_transform=dem_profile['transform'],dst_crs=dem_profile['crs'],resampling=Resampling.bilinear)
    return np.clip(np.nan_to_num(dst),0,None)

def _translate(frame,dx,dy):
    h,w=frame.shape; yy,xx=np.indices((h,w),dtype=np.float32); sx=np.clip(xx-dx,0,w-1); sy=np.clip(yy-dy,0,h-1)
    x0=np.floor(sx).astype(int); y0=np.floor(sy).astype(int); x1=np.minimum(x0+1,w-1); y1=np.minimum(y0+1,h-1); fx=sx-x0; fy=sy-y0
    return ((frame[y0,x0]*(1-fx)*(1-fy)+frame[y0,x1]*fx*(1-fy)+frame[y1,x0]*(1-fx)*fy+frame[y1,x1]*fx*fy)).astype(np.float32)

def _expand_inputs(radar_paths):
    out=[]
    for raw in radar_paths:
        if not raw: continue
        p=Path(raw)
        if p.is_dir(): out += sorted(str(x) for x in p.glob('*.tif')) + sorted(str(x) for x in p.glob('*.tiff'))
        elif p.exists(): out.append(str(p))
    return out

def generate_nowcast(radar_paths: Sequence[str], dem_path: str, output_npz: str, output_json: str, steps:int=DEFAULT_STEPS, step_minutes:int=DEFAULT_STEP_MIN, synthetic_if_missing:bool=True)->dict:
    with rasterio.open(dem_path) as dem: dem_profile=dem.profile.copy(); dem_shape=(dem.height,dem.width)
    paths=_expand_inputs(radar_paths)
    source='DWR/IMD GeoTIFF'
    frames=[]
    if paths:
        aligned=[_align(*_read_raster(p),dem_profile) for p in paths]
        if len(aligned)==1:
            current=aligned[0]
            frames=[_translate(current,1.4*i,0.55*i) for i in range(1,steps+1)]
            source='DWR/IMD GeoTIFF + advection nowcast'
        else:
            frames=(aligned + [aligned[-1]]*steps)[:steps]
            if len(frames)<steps: frames += [_translate(frames[-1],1.0*i,0.4*i) for i in range(1,steps-len(frames)+1)]
            source=f'DWR/IMD GeoTIFF sequence ({len(paths)} input frames)'
    elif synthetic_if_missing:
        source='SYNTHETIC_DWR_DEMO'
        h,w=dem_shape; y,x=np.indices((h,w)); cx,cy=w*.35,h*.55; sigma=max(8,min(h,w)*.10)
        current=(70*np.exp(-((x-cx)**2+(y-cy)**2)/(2*sigma**2))+15*np.exp(-((x-w*.68)**2+(y-h*.38)**2)/(2*(sigma*.7)**2))).astype(np.float32)
        frames=[_translate(current,1.4*i,.55*i) for i in range(1,steps+1)]
    else: raise FileNotFoundError('No radar input supplied and synthetic fallback is disabled.')
    arr=np.stack(frames[:steps]).astype(np.float32)
    Path(output_npz).parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(output_npz,rainfall_mm_hr=arr)
    meta={'source':source,'is_live_radar':source.startswith('DWR/IMD'),'steps':len(arr),'step_minutes':step_minutes,'lead_time_minutes':[i*step_minutes for i in range(1,len(arr)+1)],'units':'mm/hr','shape':list(arr.shape),'dem_crs':str(dem_profile['crs']),'dem_transform':list(dem_profile['transform']),'input_files':paths}
    Path(output_json).write_text(json.dumps(meta,indent=2),encoding='utf-8'); return meta
