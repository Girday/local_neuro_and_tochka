from fastapi import APIRouter, Depends

from api_gateway.core.context import AuthenticatedUser
from api_gateway.dependencies import get_current_user
from api_gateway.schemas import UserProfile

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserProfile)
async def read_current_user(user: AuthenticatedUser = Depends(get_current_user)) -> UserProfile:
    return UserProfile(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
        roles=user.roles,
        tenant_id=user.tenant_id,
    )
