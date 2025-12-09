from fastapi import FastAPI

from safety_service.config import get_settings
from safety_service.logging import configure_logging
from safety_service.routers import safety

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(safety.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
