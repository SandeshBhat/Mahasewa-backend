"""Geocoding service for converting addresses to coordinates"""
import logging
import httpx
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for geocoding addresses to coordinates"""
    
    @staticmethod
    async def geocode_address(
        address: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None
    ) -> Optional[Tuple[float, float]]:
        """
        Convert address to latitude/longitude coordinates
        
        Uses OpenStreetMap Nominatim API (free, no API key required)
        Falls back to Google Geocoding API if configured
        
        Args:
            address: Street address
            city: City name
            state: State name
            pincode: Postal code
        
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        # Build full address
        full_address = address
        if city:
            full_address += f", {city}"
        if state:
            full_address += f", {state}"
        if pincode:
            full_address += f" {pincode}"
        full_address += ", India"
        
        # Try OpenStreetMap Nominatim first (free, no API key)
        try:
            coordinates = await GeocodingService._geocode_nominatim(full_address)
            if coordinates:
                logger.info(f"Geocoded address via Nominatim: {full_address} -> {coordinates}")
                return coordinates
        except Exception as e:
            logger.warning(f"Nominatim geocoding failed: {e}")
        
        # Try Google Geocoding API if configured
        if hasattr(settings, 'GOOGLE_MAPS_API_KEY') and settings.GOOGLE_MAPS_API_KEY:
            try:
                coordinates = await GeocodingService._geocode_google(full_address)
                if coordinates:
                    logger.info(f"Geocoded address via Google: {full_address} -> {coordinates}")
                    return coordinates
            except Exception as e:
                logger.warning(f"Google geocoding failed: {e}")
        
        logger.error(f"Failed to geocode address: {full_address}")
        return None
    
    @staticmethod
    async def _geocode_nominatim(address: str) -> Optional[Tuple[float, float]]:
        """Geocode using OpenStreetMap Nominatim API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    "q": address,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "in"  # Limit to India
                }
                headers = {
                    "User-Agent": "MahaSeWA/1.0"  # Required by Nominatim
                }
                
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    lat = float(result.get("lat", 0))
                    lon = float(result.get("lon", 0))
                    if lat and lon:
                        return (lat, lon)
        except Exception as e:
            logger.error(f"Nominatim geocoding error: {e}")
        
        return None
    
    @staticmethod
    async def _geocode_google(address: str) -> Optional[Tuple[float, float]]:
        """Geocode using Google Geocoding API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {
                    "address": address,
                    "key": settings.GOOGLE_MAPS_API_KEY,
                    "region": "in"  # Bias to India
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get("status") == "OK" and data.get("results"):
                    location = data["results"][0]["geometry"]["location"]
                    lat = float(location.get("lat", 0))
                    lng = float(location.get("lng", 0))
                    if lat and lng:
                        return (lat, lng)
        except Exception as e:
            logger.error(f"Google geocoding error: {e}")
        
        return None
    
    @staticmethod
    def calculate_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in kilometers
        Uses Haversine formula
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Earth radius in kilometers
        R = 6371.0
        
        distance = R * c
        return distance


# Create global instance
geocoding_service = GeocodingService()

