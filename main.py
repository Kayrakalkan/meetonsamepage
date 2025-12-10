#!/usr/bin/env python3
"""
Flight Scraper CLI
Search for cheapest flights from multiple departure airports to a single destination.
Supports both web scraping (Skyscanner) and API mode (Kiwi.com)
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system env vars

from models import SearchParameters, SearchResult


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search for cheapest flights from multiple airports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using Kiwi API (recommended - no bot detection!)
  python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --api
  
  # Using Skyscanner scraper (may be blocked)
  python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --no-headless
  
  # With manual CAPTCHA solving
  python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --no-headless --manual-captcha
        """
    )
    
    parser.add_argument(
        '--from', '-f',
        dest='departure_airports',
        nargs='+',
        required=True,
        help='Departure airport codes (e.g., BUD CGN)'
    )
    
    parser.add_argument(
        '--to', '-t',
        dest='arrival_airport',
        required=True,
        help='Arrival airport code (e.g., ZRH)'
    )
    
    parser.add_argument(
        '--start', '-s',
        required=True,
        help='Start of date range (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end', '-e',
        required=True,
        help='End of date range (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        required=True,
        help='Trip duration in days'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='flight_results.json',
        help='Output JSON file path (default: flight_results.json)'
    )
    
    parser.add_argument(
        '--api',
        action='store_true',
        help='Use Kiwi.com API instead of scraping (recommended, requires KIWI_API_KEY)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in visible mode (useful for debugging, scraper mode only)'
    )
    
    parser.add_argument(
        '--manual-captcha',
        action='store_true',
        help='Wait for you to manually solve CAPTCHAs (scraper mode only)'
    )
    
    return parser.parse_args()


def validate_date(date_string: str) -> bool:
    """Validate date format"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def print_results(results: dict, params: SearchParameters):
    """Print results in a formatted way"""
    print("\n" + "=" * 60)
    print("🛫 FLIGHT SEARCH RESULTS")
    print("=" * 60)
    print(f"Destination: {params.arrival_airport}")
    print(f"Trip Duration: {params.trip_duration_days} days")
    print(f"Date Range: {params.date_from} to {params.date_to}")
    print("=" * 60)
    
    for airport, flights in results.items():
        print(f"\n📍 FROM {airport}:")
        print("-" * 40)
        
        if not flights:
            print("  No flights found")
            continue
        
        for i, flight in enumerate(flights, 1):
            print(f"\n  #{i} - {flight['price']:.2f} {flight['currency']}")
            print(f"      📅 {flight['departure_date']} → {flight['return_date']}")
            if flight.get('airline'):
                print(f"      ✈️  {flight['airline']}")
            if flight.get('departure_time'):
                print(f"      ⏰ {flight['departure_time']} - {flight.get('arrival_time', 'N/A')}")
            if flight.get('duration'):
                print(f"      ⏱️  {flight['duration']}")
            stops = flight.get('stops', 0)
            print(f"      🔄 {'Direct' if stops == 0 else f'{stops} stop(s)'}")
    
    print("\n" + "=" * 60)


async def main():
    args = parse_args()
    
    # Validate dates
    if not validate_date(args.start):
        print(f"❌ Invalid start date format: {args.start}. Use YYYY-MM-DD")
        return
    
    if not validate_date(args.end):
        print(f"❌ Invalid end date format: {args.end}. Use YYYY-MM-DD")
        return
    
    # Create search parameters
    params = SearchParameters(
        departure_airports=[a.upper() for a in args.departure_airports],
        arrival_airport=args.arrival_airport.upper(),
        date_from=args.start,
        date_to=args.end,
        trip_duration_days=args.days
    )
    
    print("\n🔍 Starting flight search...")
    print(f"  From: {', '.join(params.departure_airports)}")
    print(f"  To: {params.arrival_airport}")
    print(f"  Dates: {params.date_from} to {params.date_to}")
    print(f"  Duration: {params.trip_duration_days} days\n")
    
    # Choose search method
    if args.api:
        # Use Kiwi.com API
        from api_scraper import search_with_api
        
        api_key = os.getenv("KIWI_API_KEY")
        if not api_key:
            print("❌ KIWI_API_KEY not found!")
            print("   1. Get your free API key at: https://tequila.kiwi.com/")
            print("   2. Create a .env file with: KIWI_API_KEY=your_key_here")
            print("   3. Or set environment variable: export KIWI_API_KEY=your_key_here")
            return
        
        print("🌐 Using Kiwi.com API (no bot detection!)\n")
        results = await search_with_api(params, api_key)
    else:
        # Use Skyscanner scraper
        from scraper import search_multiple_origins
        
        headless = not args.no_headless
        manual_captcha = args.manual_captcha
        
        if manual_captcha:
            print("📢 Manual CAPTCHA mode enabled - you'll need to solve CAPTCHAs yourself\n")
        
        print("🕷️ Using Skyscanner scraper (may trigger bot detection)\n")
        results = await search_multiple_origins(params, headless=headless, manual_captcha=manual_captcha)
    
    # Create search result object
    search_result = SearchResult(
        parameters=params,
        results=results,
        timestamp=datetime.now().isoformat()
    )
    
    # Print results
    print_results(results, params)
    
    # Save to JSON
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(search_result.model_dump(), f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
