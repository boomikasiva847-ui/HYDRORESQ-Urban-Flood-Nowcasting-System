import uvicorn

if __name__ == "__main__":
    print("[Module 6] Launching Dynamic Safe Routing Engine API on http://localhost:8001 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)