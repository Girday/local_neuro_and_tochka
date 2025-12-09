from fastapi import APIRouter, Depends

from safety_service.config import Settings, get_settings
from safety_service.core.evaluator import evaluate_input, evaluate_output
from safety_service.schemas import InputCheckRequest, OutputCheckRequest, SafetyResponse

router = APIRouter(prefix="/internal/safety", tags=["safety"])


@router.post("/input-check", response_model=SafetyResponse)
async def input_check(
    payload: InputCheckRequest,
    settings: Settings = Depends(get_settings),
) -> SafetyResponse:
    return evaluate_input(payload, settings)


@router.post("/output-check", response_model=SafetyResponse)
async def output_check(
    payload: OutputCheckRequest,
    settings: Settings = Depends(get_settings),
) -> SafetyResponse:
    return evaluate_output(payload, settings)
