from fastapi import APIRouter
from app.api.v1.advisories import router as advisories_router
from app.api.v1.auth import router as auth_router
from app.api.v1.consents import router as consents_router
from app.api.v1.contexts import router as contexts_router
from app.api.v1.disease import router as disease_router
from app.api.v1.farms import router as farms_router
from app.api.v1.health import router as health_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.model_hub import router as model_hub_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.stac import router as stac_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.federation import router as federation_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.broadcasts import router as broadcasts_router
from app.api.v1.voice import router as voice_router

api_router = APIRouter()

# v1 routes
api_router.include_router(auth_router)
api_router.include_router(farms_router)
api_router.include_router(intelligence_router)
api_router.include_router(advisories_router)
api_router.include_router(disease_router)
api_router.include_router(onboarding_router)
api_router.include_router(consents_router)
api_router.include_router(uploads_router)
api_router.include_router(tasks_router)
api_router.include_router(federation_router)
api_router.include_router(model_hub_router)
api_router.include_router(webhooks_router)
api_router.include_router(broadcasts_router)
api_router.include_router(voice_router)

# Interoperability – mounted at root (not under /api/v1/)
interop_router = APIRouter()
interop_router.include_router(stac_router)
interop_router.include_router(contexts_router)


