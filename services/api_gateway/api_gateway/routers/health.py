from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
