# ✈️ MeetOnSamePage - Flight Finder

A flight search tool that finds the cheapest flights from multiple departure airports to a common destination. Perfect for couples or friends living in different cities who want to meet somewhere.

## 🎯 Features

- Search from **multiple departure airports** simultaneously
- Find flights within a **date range** with specific trip duration
- **Two search modes:**
  - 🌐 **API Mode** (Recommended) - Uses Kiwi.com API, no bot detection issues
  - 🕷️ **Scraper Mode** - Uses Playwright to scrape Skyscanner

## 📦 Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# For scraper mode only: Install Playwright browsers
playwright install chromium
```

## � API Setup (Recommended)

1. Go to [Kiwi.com Tequila](https://tequila.kiwi.com/) and create a free account
2. Get your API key (free tier: 3000 searches/month)
3. Create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

## 🚀 Usage

### API Mode (Recommended - No Bot Detection!)

```bash
# Search using Kiwi.com API
python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --api
```

### Scraper Mode (May Be Blocked)

```bash
# Basic scraper mode
python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --no-headless

# With manual CAPTCHA solving
python main.py --from BUD CGN --to ZRH --start 2025-12-15 --end 2025-12-30 --days 3 --no-headless --manual-captcha
```

### Arguments

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--from` | `-f` | ✅ | Departure airport codes (space-separated) |
| `--to` | `-t` | ✅ | Arrival airport code |
| `--start` | `-s` | ✅ | Start date (YYYY-MM-DD) |
| `--end` | `-e` | ✅ | End date (YYYY-MM-DD) |
| `--days` | `-d` | ✅ | Trip duration in days |
| `--api` | | ❌ | Use Kiwi.com API (recommended) |
| `--output` | `-o` | ❌ | Output file (default: flight_results.json) |
| `--no-headless` | | ❌ | Show browser window (scraper mode) |
| `--manual-captcha` | | ❌ | Manually solve CAPTCHAs (scraper mode) |

## 📊 Output Format

Results are saved as JSON:

```json
{
  "parameters": {
    "departure_airports": ["BUD", "CGN"],
    "arrival_airport": "ZRH",
    "date_from": "2025-12-15",
    "date_to": "2025-12-30",
    "trip_duration_days": 3
  },
  "results": {
    "BUD": [
      {
        "departure_airport": "BUD",
        "arrival_airport": "ZRH",
        "departure_date": "2025-12-18",
        "return_date": "2025-12-21",
        "price": 89.0,
        "currency": "EUR",
        "airline": "Wizz Air",
        "departure_time": "06:30",
        "arrival_time": "08:15",
        "duration": "1h 45m",
        "stops": 0
      }
    ],
    "CGN": [...]
  },
  "timestamp": "2025-12-05T10:30:00"
}
```

## ⚠️ Notes

- Skyscanner may block automated requests. Use reasonable delays between searches.
- The scraper uses random delays (2-4 seconds) between requests to avoid detection.
- For debugging, use `--no-headless` to see what's happening in the browser.

## 🔧 Project Structure

```
meetonsamepage/
├── main.py           # CLI entry point
├── scraper.py        # Playwright scraper logic
├── models.py         # Pydantic data models
├── requirements.txt  # Dependencies
└── README.md         # This file
```

## 📝 Airport Codes

Common airport codes:
- **BUD** - Budapest
- **CGN** - Cologne
- **ZRH** - Zurich
- **MUC** - Munich
- **PRG** - Prague
- **VIE** - Vienna
- **BCN** - Barcelona
- **FCO** - Rome

Find more at [IATA Airport Codes](https://www.iata.org/en/publications/directories/code-search/)
