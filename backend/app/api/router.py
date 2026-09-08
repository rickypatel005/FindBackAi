from fastapi import APIRouter

from app.api.routes import admin, ai, auth, matches, notifications, reports, uploads

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(reports.router)
api_router.include_router(uploads.router)
api_router.include_router(ai.router)
api_router.include_router(matches.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
