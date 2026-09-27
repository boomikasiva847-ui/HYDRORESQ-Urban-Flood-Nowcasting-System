from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from src.route_api import router
except ImportError:  # Package/test execution from project root
    from .src.route_api import router

app = FastAPI(title="Module 6 Dynamic Safe Routing Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8005", "http://127.0.0.1:8005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Module 6 Dynamic Safe Routing API is active.",
        "endpoints": ["/health", "/network", "/route"],
        "forecast_source": "Module 4 /forecast",
    }
