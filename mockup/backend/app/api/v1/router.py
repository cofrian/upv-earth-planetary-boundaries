from fastapi import APIRouter

from app.api.v1.routes import analytics, chat, jobs, papers, uploads

api_router = APIRouter()
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
