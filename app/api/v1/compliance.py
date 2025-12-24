"""Compliance endpoints"""
from fastapi import APIRouter
router = APIRouter()

@router.get("/requirements")
async def list_requirements():
    return {"requirements": [], "total": 0}
