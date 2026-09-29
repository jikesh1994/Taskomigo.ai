from fastapi import APIRouter

from app.api.v1 import auth, jobs, preferences, profiles, resumes, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(profiles.router)
api_router.include_router(preferences.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.sources_router)
api_router.include_router(jobs.router)
