from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import init_db
from src.api_routes import router
from src.scheduler import start_scheduler, refresh_cycle

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await refresh_cycle()
    scheduler = start_scheduler()
    try:
        yield
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


app = FastAPI(title="Flood Alerts Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8005", "http://127.0.0.1:8005", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "service": "Flood Alerts Backend API", "endpoints": ["/health", "/forecast", "/ws"]}

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
