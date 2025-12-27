"""Geocoding utility endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.geocoding_service import geocoding_service

router = APIRouter()


class GeocodeRequest(BaseModel):
    """Request schema for geocoding"""
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


@router.post("/geocode")
async def geocode_address(
    request: GeocodeRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Geocode an address to get latitude/longitude coordinates
    
    Uses OpenStreetMap Nominatim (free) or Google Maps API (if configured)
    """
    coordinates = await geocoding_service.geocode_address(
        address=request.address,
        city=request.city,
        state=request.state,
        pincode=request.pincode
    )
    
    if not coordinates:
        raise HTTPException(
            status_code=404,
            detail="Could not geocode the provided address"
        )
    
    return {
        "success": True,
        "address": request.address,
        "latitude": coordinates[0],
        "longitude": coordinates[1]
    }


@router.get("/distance")
async def calculate_distance_between_points(
    lat1: float = Query(..., description="Latitude of first point"),
    lon1: float = Query(..., description="Longitude of first point"),
    lat2: float = Query(..., description="Latitude of second point"),
    lon2: float = Query(..., description="Longitude of second point"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate distance between two coordinates in kilometers
    """
    distance = geocoding_service.calculate_distance(lat1, lon1, lat2, lon2)
    
    return {
        "success": True,
        "distance_km": round(distance, 2),
        "point1": {"latitude": lat1, "longitude": lon1},
        "point2": {"latitude": lat2, "longitude": lon2}
    }

