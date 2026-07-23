from fastapi import APIRouter

from app.api.v1.routes import (
    assessments,
    auth,
    compliance,
    documents,
    health,
    incidents,
    organization,
    public_questionnaires,
    suppliers,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organization.router)
api_router.include_router(assessments.router)
api_router.include_router(compliance.router)
api_router.include_router(documents.router)
api_router.include_router(incidents.router)
api_router.include_router(suppliers.router)
api_router.include_router(public_questionnaires.router)
