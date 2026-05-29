from fastapi import APIRouter

from app.schemas.settings import ModelSettings, PublicModelSettings
from app.services.model_settings import read_public_model_settings, update_model_settings

router = APIRouter()


@router.get("/model-config", response_model=PublicModelSettings)
def get_model_config() -> PublicModelSettings:
    return read_public_model_settings()


@router.put("/model-config", response_model=PublicModelSettings)
def update_model_config(payload: ModelSettings) -> PublicModelSettings:
    return update_model_settings(payload)
