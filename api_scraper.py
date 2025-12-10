"""
Flight search using Kiwi.com Tequila API
Free tier: 3000 searches/month
Sign up at: https://tequila.kiwi.com/
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Optional
from models import FlightResult, SearchParameters


class KiwiFlightAPI:
    """Flight search using Kiwi.com Tequila API"""
    
    BASE_URL = "https://api.tequila.kiwi.com/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15"
        }
    
    def _format_date(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to DD/MM/YYYY for Kiwi API"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        nights_from: int,
        nights_to: int,
        max_results: int = 10,
        currency: str = "EUR",
        one_for_city: int = 0,
        direct_only: bool = False
    ) -> List[FlightResult]:
        """
        Search for round-trip flights
        
        Args:
            origin: Departure airport/city code (e.g., "BUD", "SAW")
            destination: Arrival airport/city/country code (e.g., "ZRH", "DE" for Germany)
            date_from: Start of date range (YYYY-MM-DD)
            date_to: End of date range (YYYY-MM-DD)
            nights_from: Minimum trip duration
            nights_to: Maximum trip duration
            max_results: Maximum number of results
            currency: Currency for prices (EUR, TRY, USD, etc.)
            one_for_city: If 1, return only one result per city
            direct_only: If True, only return direct flights
        
        Returns:
            List of FlightResult objects
        """
        
        params = {
            "fly_from": origin,
            "fly_to": destination,
            "date_from": self._format_date(date_from),
            "date_to": self._format_date(date_to),
            "nights_in_dst_from": nights_from,
            "nights_in_dst_to": nights_to,
            "flight_type": "round",
            "one_for_city": one_for_city,
            "adults": 1,
            "curr": currency,
            "locale": "en",
            "sort": "price",
            "asc": 1,
            "limit": max_results
        }
        
        # Add direct flights filter
        if direct_only:
            params["max_stopovers"] = 0
        
        flights = []
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    params=params
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get("data", []):
                            # Parse outbound flight
                            route = item.get("route", [])
                            outbound = [r for r in route if r.get("return") == 0]
                            inbound = [r for r in route if r.get("return") == 1]
                            
                            # Outbound flight details
                            departure_time = None
                            arrival_time = None
                            airline = None
                            
                            if outbound:
                                departure_time = outbound[0].get("local_departure", "")[:16].replace("T", " ")
                                arrival_time = outbound[-1].get("local_arrival", "")[:16].replace("T", " ")
                                airline = outbound[0].get("airline")
                            
                            # Return flight details
                            return_departure_time = None
                            return_arrival_time = None
                            return_duration = None
                            return_stops = 0
                            
                            if inbound:
                                return_departure_time = inbound[0].get("local_departure", "")[:16].replace("T", " ")
                                return_arrival_time = inbound[-1].get("local_arrival", "")[:16].replace("T", " ")
                                return_stops = len(inbound) - 1
                                
                                # Calculate return duration
                                return_duration_seconds = item.get("duration", {}).get("return", 0)
                                if return_duration_seconds:
                                    r_hours = return_duration_seconds // 3600
                                    r_minutes = (return_duration_seconds % 3600) // 60
                                    return_duration = f"{r_hours}h {r_minutes}m"
                            
                            # Calculate outbound duration
                            outbound_duration_seconds = item.get("duration", {}).get("departure", 0)
                            if outbound_duration_seconds:
                                hours = outbound_duration_seconds // 3600
                                minutes = (outbound_duration_seconds % 3600) // 60
                                duration = f"{hours}h {minutes}m"
                            else:
                                duration_seconds = item.get("duration", {}).get("total", 0)
                                hours = duration_seconds // 3600
                                minutes = (duration_seconds % 3600) // 60
                                duration = f"{hours}h {minutes}m"
                            
                            # Count stops
                            stops = len(outbound) - 1 if outbound else 0
                            
                            # Get return date from last inbound flight
                            return_date = ""
                            if inbound:
                                return_date = inbound[-1].get("local_arrival", "")[:10]
                            
                            flights.append(FlightResult(
                                departure_airport=origin,
                                arrival_airport=destination,
                                departure_date=item.get("local_departure", "")[:10],
                                return_date=return_date,
                                price=float(item.get("price", 0)),
                                currency=item.get("currency", "EUR"),
                                airline=airline,
                                departure_time=departure_time,
                                arrival_time=arrival_time,
                                duration=duration,
                                stops=stops,
                                link=item.get("deep_link", ""),
                                return_departure_time=return_departure_time,
                                return_arrival_time=return_arrival_time,
                                return_duration=return_duration,
                                return_stops=return_stops
                            ))
                    else:
                        error_text = await response.text()
                        print(f"    ⚠️ API Error {response.status}: {error_text[:100]}")
                        
            except Exception as e:
                print(f"    ⚠️ Request error: {e}")
        
        return flights


async def search_with_api(params: SearchParameters, api_key: str) -> dict:
    """
    Search flights from multiple departure airports using Kiwi API
    
    Args:
        params: SearchParameters object
        api_key: Kiwi.com Tequila API key
    
    Returns:
        Dictionary with results for each departure airport
    """
    results = {}
    api = KiwiFlightAPI(api_key)
    
    for origin in params.departure_airports:
        print(f"🔍 Searching flights: {origin} → {params.arrival_airport}")
        
        flights = await api.search_flights(
            origin=origin,
            destination=params.arrival_airport,
            date_from=params.date_from,
            date_to=params.date_to,
            nights_from=params.trip_duration_days,
            nights_to=params.trip_duration_days,
            max_results=50,  # Get more results to find best matches
            currency="EUR"
        )
        
        # Sort by price
        flights.sort(key=lambda x: x.price)
        
        results[origin] = [f.model_dump() for f in flights]
        print(f"✅ Found {len(flights)} flights from {origin}")
        
        # Small delay between requests
        await asyncio.sleep(0.5)
    
    return results


async def search_and_find_best_match(params: SearchParameters, api_key: str, currency: str = "EUR", direct_only: bool = False) -> dict:
    """
    Search flights and find the best matching dates for all travelers
    
    Args:
        params: SearchParameters object
        api_key: Kiwi.com Tequila API key
        currency: Currency for prices
        direct_only: If True, only return direct flights
    
    Returns:
        Dictionary with all results and best matches
    """
    api = KiwiFlightAPI(api_key)
    all_flights = {}
    
    # Search for each origin
    for origin in params.departure_airports:
        print(f"🔍 Searching flights: {origin} → {params.arrival_airport}" + (" (direct only)" if direct_only else ""))
        
        flights = await api.search_flights(
            origin=origin,
            destination=params.arrival_airport,
            date_from=params.date_from,
            date_to=params.date_to,
            nights_from=params.trip_duration_days,
            nights_to=params.trip_duration_days,
            max_results=100,  # Get many results
            currency=currency,
            direct_only=direct_only
        )
        
        all_flights[origin] = flights
        print(f"✅ Found {len(flights)} flights from {origin}")
        
        await asyncio.sleep(0.3)
    
    # Find best matching dates
    best_matches = find_best_date_matches(all_flights, params.departure_airports)
    
    # Prepare results - top 5 per origin
    results = {}
    for origin, flights in all_flights.items():
        flights.sort(key=lambda x: x.price)
        results[origin] = [f.model_dump() for f in flights[:5]]
    
    return {
        "results": results,
        "best_matches": best_matches
    }


def find_best_date_matches(all_flights: dict, origins: list) -> list:
    """
    Find the best date combinations where all travelers can meet
    
    Args:
        all_flights: Dictionary of origin -> list of FlightResult
        origins: List of origin airport codes
    
    Returns:
        List of best matches sorted by total price
    """
    if len(origins) < 2:
        return []
    
    origin1, origin2 = origins[0], origins[1]
    flights1 = all_flights.get(origin1, [])
    flights2 = all_flights.get(origin2, [])
    
    if not flights1 or not flights2:
        return []
    
    matches = []
    
    # Group flights by departure date
    flights1_by_date = {}
    for f in flights1:
        date = f.departure_date
        if date not in flights1_by_date:
            flights1_by_date[date] = []
        flights1_by_date[date].append(f)
    
    flights2_by_date = {}
    for f in flights2:
        date = f.departure_date
        if date not in flights2_by_date:
            flights2_by_date[date] = []
        flights2_by_date[date].append(f)
    
    # Find matching dates (same day or within 1 day)
    for date1, f1_list in flights1_by_date.items():
        # Get cheapest flight for this date from origin 1
        cheapest_f1 = min(f1_list, key=lambda x: x.price)
        
        # Look for same date or +/- 1 day from origin 2
        from datetime import datetime, timedelta
        
        try:
            dt1 = datetime.strptime(date1, "%Y-%m-%d")
        except:
            continue
        
        for day_offset in [0, 1, -1]:  # Same day first, then +/- 1 day
            check_date = (dt1 + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            
            if check_date in flights2_by_date:
                cheapest_f2 = min(flights2_by_date[check_date], key=lambda x: x.price)
                
                combined_price = cheapest_f1.price + cheapest_f2.price
                
                matches.append({
                    "departure_date": date1,
                    "return_date": cheapest_f1.return_date or "",
                    "combined_price": combined_price,
                    "currency": cheapest_f1.currency,
                    "date_match": "same_day" if day_offset == 0 else f"{abs(day_offset)}_day_diff",
                    "flights": [
                        cheapest_f1.model_dump(),
                        cheapest_f2.model_dump()
                    ]
                })
    
    # Sort by combined price and return top 5
    matches.sort(key=lambda x: x["combined_price"])
    
    # Remove duplicates (same dates)
    seen_dates = set()
    unique_matches = []
    for match in matches:
        date_key = match["departure_date"]
        if date_key not in seen_dates:
            seen_dates.add(date_key)
            unique_matches.append(match)
    
    return unique_matches[:5]


async def search_best_destinations(
    origins: list,
    destination_airports: list,
    date_from: str,
    date_to: str,
    trip_days: int,
    api_key: str,
    currency: str = "EUR",
    direct_only: bool = False
) -> list:
    """
    Search multiple destination airports and find the best combined prices
    
    Args:
        origins: List of origin airport codes (e.g., ["BUD", "CGN"])
        destination_airports: List of destination airport codes to check
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        trip_days: Trip duration in days
        api_key: Kiwi API key
        currency: Currency for prices
        direct_only: Only search direct flights
    
    Returns:
        List of best destinations with combined prices
    """
    api = KiwiFlightAPI(api_key)
    destination_results = []
    
    for dest in destination_airports:
        print(f"🔍 Checking destination: {dest}")
        
        dest_flights = {}
        total_found = True
        
        for origin in origins:
            flights = await api.search_flights(
                origin=origin,
                destination=dest,
                date_from=date_from,
                date_to=date_to,
                nights_from=trip_days,
                nights_to=trip_days,
                max_results=20,
                currency=currency,
                direct_only=direct_only
            )
            
            if not flights:
                total_found = False
                break
            
            dest_flights[origin] = flights
            await asyncio.sleep(0.2)
        
        if not total_found or len(dest_flights) < len(origins):
            print(f"  ⚠️ Not all origins have flights to {dest}")
            continue
        
        # Find best combined price for this destination
        best_matches = find_best_date_matches(dest_flights, origins)
        
        if best_matches:
            best = best_matches[0]
            destination_results.append({
                "destination": dest,
                "combined_price": best["combined_price"],
                "currency": currency,
                "departure_date": best["departure_date"],
                "return_date": best["return_date"],
                "flights": best["flights"]
            })
            print(f"  ✅ {dest}: {currency} {best['combined_price']:.0f}")
    
    # Sort by combined price
    destination_results.sort(key=lambda x: x["combined_price"])
    
    return destination_results[:10]


async def search_everywhere(
    origins: list,
    date_from: str,
    date_to: str,
    trip_days: int,
    api_key: str,
    currency: str = "EUR",
    direct_only: bool = False,
    airports_list: list = None
) -> list:
    """
    Search all airports in our database to find the cheapest destinations 
    where both travelers can meet.
    
    Args:
        origins: List of origin airport codes (e.g., ["BUD", "CGN"])
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        trip_days: Trip duration in days
        api_key: Kiwi API key
        currency: Currency for prices
        direct_only: Only search direct flights
        airports_list: List of airport codes to search through
    
    Returns:
        List of cheapest destinations with combined prices
    """
    api = KiwiFlightAPI(api_key)
    
    if not airports_list:
        return []
    
    # Filter out origins from destination list
    destinations_to_check = [a for a in airports_list if a not in origins]
    
    print(f"🌍 Searching everywhere: checking {len(destinations_to_check)} destinations from {origins}...")
    
    results = []
    checked = 0
    
    for dest in destinations_to_check:
        checked += 1
        if checked % 10 == 0:
            print(f"  📍 Progress: {checked}/{len(destinations_to_check)} destinations checked...")
        
        dest_flights = {}
        all_found = True
        
        # Search flights from each origin to this destination
        for origin in origins:
            try:
                flights = await api.search_flights(
                    origin=origin,
                    destination=dest,
                    date_from=date_from,
                    date_to=date_to,
                    nights_from=trip_days,
                    nights_to=trip_days,
                    max_results=5,
                    currency=currency,
                    direct_only=direct_only
                )
                
                if flights:
                    dest_flights[origin] = flights
                else:
                    all_found = False
                    break
                    
                await asyncio.sleep(0.1)  # Small delay to avoid rate limiting
                
            except Exception as e:
                all_found = False
                break
        
        # If we found flights from both origins, find best match
        if all_found and len(dest_flights) == len(origins):
            best_matches = find_best_date_matches(dest_flights, origins)
            
            if best_matches:
                best = best_matches[0]
                results.append({
                    "destination": dest,
                    "combined_price": best["combined_price"],
                    "currency": currency,
                    "departure_date": best["departure_date"],
                    "return_date": best["return_date"],
                    "flights": best["flights"]
                })
                print(f"  ✅ {dest}: {currency} {best['combined_price']:.0f}")
        
        # Stop after finding 15 valid destinations to save API calls
        if len(results) >= 15:
            break
    
    # Sort by combined price and return top 10
    results.sort(key=lambda x: x["combined_price"])
    
    print(f"🎯 Found {len(results)} destinations, returning top 10 cheapest")
    
    return results[:10]


# For testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test():
        api_key = os.getenv("KIWI_API_KEY")
        if not api_key:
            print("❌ Please set KIWI_API_KEY in .env file")
            print("   Get your free API key at: https://tequila.kiwi.com/")
            return
        
        params = SearchParameters(
            departure_airports=["BUD", "CGN"],
            arrival_airport="ZRH",
            date_from="2025-12-15",
            date_to="2025-12-30",
            trip_duration_days=3
        )
        
        results = await search_with_api(params, api_key)
        print(json.dumps(results, indent=2))
    
    asyncio.run(test())
