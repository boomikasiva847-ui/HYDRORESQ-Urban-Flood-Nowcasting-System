import uvicorn

if __name__ == "__main__":
    print("[Module 5] Launching Web GIS Command Dashboard Server on http://localhost:8005 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8005, reload=False)