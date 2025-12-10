#!/usr/bin/env python3
"""
Flask web server for MeetOnSamePage flight finder
"""

import os
import json
import asyncio
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from models import SearchParameters
from api_scraper import search_and_find_best_match, search_best_destinations, search_everywhere

load_dotenv()

app = Flask(__name__)

# Get API key from environment
KIWI_API_KEY = os.getenv("KIWI_API_KEY")

# Load airports data
AIRPORTS_DATA = None
def load_airports():
    global AIRPORTS_DATA
    if AIRPORTS_DATA is None:
        with open(os.path.join(app.static_folder, 'airports.json'), 'r') as f:
            AIRPORTS_DATA = json.load(f)
    return AIRPORTS_DATA


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/airports', methods=['GET'])
def search_airports():
    """Search airports by query (code, name, city, or country)"""
    query = request.args.get('q', '').lower().strip()
    
    if len(query) < 1:
        return jsonify([])
    
    data = load_airports()
    results = []
    
    for airport in data['airports']:
        # Search in code, name, city, and country
        if (query in airport['code'].lower() or
            query in airport['name'].lower() or
            query in airport['city'].lower() or
            query in airport['country'].lower()):
            results.append(airport)
    
    # Sort: exact code match first, then by relevance
    def sort_key(a):
        if a['code'].lower() == query:
            return (0, a['city'])
        if a['code'].lower().startswith(query):
            return (1, a['city'])
        if a['city'].lower().startswith(query):
            return (2, a['city'])
        return (3, a['city'])
    
    results.sort(key=sort_key)
    return jsonify(results[:20])


@app.route('/api/countries', methods=['GET'])
def get_countries():
    """Get list of all countries"""
    data = load_airports()
    return jsonify(data['countries'])


@app.route('/api/airports/country/<country_code>', methods=['GET'])
def get_airports_by_country(country_code):
    """Get all airports in a country"""
    data = load_airports()
    airports = [a for a in data['airports'] if a['country_code'].upper() == country_code.upper()]
    return jsonify(airports)


@app.route('/api/search/destinations', methods=['POST'])
def search_best_destinations_api():
    """Find best destination airports in a country for two origins"""
    if not KIWI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500
    
    try:
        req_data = request.get_json()
        
        origins = req_data.get('origins', [])
        country_code = req_data.get('country_code', '')
        date_from = req_data.get('date_from')
        date_to = req_data.get('date_to')
        trip_days = req_data.get('trip_days', 3)
        currency = req_data.get('currency', 'EUR')
        direct_only = req_data.get('direct_only', False)
        
        if not origins or not country_code:
            return jsonify({"error": "Missing origins or country_code"}), 400
        
        # Get airports in the country
        data = load_airports()
        country_airports = [a['code'] for a in data['airports'] if a['country_code'].upper() == country_code.upper()]
        
        if not country_airports:
            return jsonify({"error": f"No airports found in country {country_code}"}), 404
        
        # Limit to first 5 major airports
        country_airports = country_airports[:5]
        
        # Run search for best destinations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                search_best_destinations(
                    origins=[o.upper() for o in origins],
                    destination_airports=country_airports,
                    date_from=date_from,
                    date_to=date_to,
                    trip_days=trip_days,
                    api_key=KIWI_API_KEY,
                    currency=currency,
                    direct_only=direct_only
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "destinations": results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/search/everywhere', methods=['POST'])
def search_everywhere_api():
    """Find cheapest destinations worldwide for two origins"""
    if not KIWI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500
    
    try:
        req_data = request.get_json()
        
        origins = req_data.get('origins', [])
        date_from = req_data.get('date_from')
        date_to = req_data.get('date_to')
        trip_days = req_data.get('trip_days', 3)
        currency = req_data.get('currency', 'EUR')
        direct_only = req_data.get('direct_only', False)
        
        if not origins:
            return jsonify({"error": "Missing origins"}), 400
        
        # Run everywhere search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(
                search_everywhere(
                    origins=[o.upper() for o in origins],
                    date_from=date_from,
                    date_to=date_to,
                    trip_days=trip_days,
                    api_key=KIWI_API_KEY,
                    currency=currency,
                    direct_only=direct_only
                )
            )
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "destinations": results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search_flights():
    """API endpoint for flight search"""
    
    if not KIWI_API_KEY:
        return jsonify({"error": "API key not configured"}), 500
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['origins', 'destination', 'date_from', 'date_to', 'trip_days']
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create search parameters
        params = SearchParameters(
            departure_airports=[o.upper() for o in data['origins']],
            arrival_airport=data['destination'].upper(),
            date_from=data['date_from'],
            date_to=data['date_to'],
            trip_duration_days=data['trip_days']
        )
        
        currency = data.get('currency', 'EUR')
        direct_only = data.get('direct_only', False)
        
        # Run async search in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            search_result = loop.run_until_complete(
                search_and_find_best_match(params, KIWI_API_KEY, currency, direct_only)
            )
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "results": search_result["results"],
            "best_matches": search_result["best_matches"]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


async def search_with_api_extended(params: SearchParameters, api_key: str, currency: str = "EUR") -> dict:
    """Extended search function with currency support"""
    from api_scraper import KiwiFlightAPI
    
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
            max_results=10,
            currency=currency
        )
        
        # Get top 3 cheapest
        flights.sort(key=lambda x: x.price)
        top_flights = flights[:5]
        
        results[origin] = [f.model_dump() for f in top_flights]
        print(f"✅ Found {len(top_flights)} flights from {origin}")
        
        # Small delay between requests
        await asyncio.sleep(0.3)
    
    return results


if __name__ == '__main__':
    if not KIWI_API_KEY:
        print("⚠️  Warning: KIWI_API_KEY not set in .env file")
        print("   Get your free API key at: https://tequila.kiwi.com/")
    
    print("\n🚀 Starting MeetOnSamePage server...")
    print("   Open http://localhost:5000 in your browser\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
