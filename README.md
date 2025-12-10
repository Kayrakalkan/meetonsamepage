# MeetOnSamePage - Flight Finder

Find the cheapest flights from two different cities to meet at a common destination. Perfect for long-distance couples, friends, or colleagues who want to meet somewhere in the middle.

## Features

- **Airport Search**: Search flights to a specific airport
- **Country Search**: Find the best airports to meet in a country
- **Everywhere Search**: Discover the cheapest destinations worldwide
- **Smart Matching**: Automatically finds dates when both travelers can fly
- **Side-by-side Comparison**: View both travelers' flights paired by date
- **Multi-currency Support**: EUR, USD, GBP, TRY, CHF

## Live Demo

🚀 [Visit MeetOnSamePage](https://meetonsamepage.onrender.com)

## Deploy Your Own

### Deploy to Render

1. Fork this repository
2. Create a free account on [Render](https://render.com)
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect the configuration from `render.yaml`
6. Add your environment variable:
   - `KIWI_API_KEY`: Your Kiwi.com Tequila API key

### Get a Free API Key

1. Go to [Kiwi.com Tequila](https://tequila.kiwi.com/)
2. Create a free account
3. Get your API key (free tier: 3000 searches/month)

## Local Development

### Prerequisites

- Python 3.11+
- A Kiwi.com Tequila API key

### Setup

```bash
# Clone the repository
git clone https://github.com/Kayrakalkan/meetonsamepage.git
cd meetonsamepage

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and add your KIWI_API_KEY

# Run the server
python app.py
```

Open http://localhost:5000 in your browser.

## Project Structure

```
meetonsamepage/
├── app.py              # Flask web server
├── api_scraper.py      # Kiwi.com API integration
├── models.py           # Data models
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
├── Procfile            # Process file for deployment
├── static/
│   ├── airports.json   # Airport database (180+ airports)
│   ├── script.js       # Frontend JavaScript
│   └── style.css       # Styles
└── templates/
    └── index.html      # Main page
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `KIWI_API_KEY` | Your Kiwi.com Tequila API key | Yes |
| `PORT` | Server port (default: 5000) | No |
| `FLASK_ENV` | Set to `production` for production | No |

## API Limits

The free Kiwi.com Tequila API tier includes:
- 3,000 searches per month
- Access to all flight data
- No credit card required

## Tech Stack

- **Backend**: Python, Flask
- **API**: Kiwi.com Tequila API
- **Frontend**: Vanilla JavaScript, CSS
- **Deployment**: Render

## License

MIT License - feel free to use and modify!

---

Made with ❤️ for long-distance friendships
