from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class FlightResult(BaseModel):
    """Single flight result from scraping"""
    departure_airport: str
    arrival_airport: str
    departure_date: str
    return_date: str
    price: float
    currency: str
    airline: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration: Optional[str] = None
    stops: Optional[int] = None
    link: Optional[str] = None
    # Return flight details
    return_departure_time: Optional[str] = None
    return_arrival_time: Optional[str] = None
    return_duration: Optional[str] = None
    return_stops: Optional[int] = None


class SearchParameters(BaseModel):
    """Search parameters for flight search"""
    departure_airports: List[str]  # e.g., ["BUD", "CGN"]
    arrival_airport: str  # e.g., "ZRH"
    date_from: str  # e.g., "2025-12-15"
    date_to: str  # e.g., "2025-12-30"
    trip_duration_days: int  # e.g., 3 days vacation


class SearchResult(BaseModel):
    """Complete search result with all flights"""
    parameters: SearchParameters
    results: dict  # departure_airport -> List[FlightResult]
    timestamp: str
