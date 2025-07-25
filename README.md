# ORB Scanner Secure API - Realtime

Secure API proxy for ORB Scanner with realtime capabilities, deployed on DigitalOcean App Platform.

## 🚀 Quick Start

### Prerequisites
- DigitalOcean account
- GitHub account
- Polygon API key
- Finnhub API key

### Deployment
1. Clone this repository
2. Deploy to DigitalOcean App Platform
3. Set environment variables in DigitalOcean dashboard

## 📁 Files

- `api_server.py` - Main Flask API server
- `requirements_api.txt` - Python dependencies
- `.do/app.yaml` - DigitalOcean App Platform configuration

## 🔧 Environment Variables

Set these in DigitalOcean App Platform:

| Variable | Description |
|----------|-------------|
| `POLYGON_API_KEY` | Your Polygon API key |
| `FINNHUB_API_KEY` | Your Finnhub API key |
| `VALID_LICENSE_KEYS` | Comma-separated license keys |

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/gainers` | GET | Top gaining stocks |
| `/api/losers` | GET | Top losing stocks |
| `/api/historical/{symbol}` | GET | Historical price data |
| `/api/float/{symbol}` | GET | Float data |
| `/api/news/{symbol}` | GET | News data |
| `/api/volume/{symbol}` | GET | Volume data |

## 🔒 Security

- License key authentication required
- Rate limiting: 100 requests/minute
- API keys stored securely on DigitalOcean
- CORS enabled for cross-origin requests

## 📞 Support

See `SECURE_API_DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## 🔗 Repository

GitHub: https://github.com/Jrooker06/orb-scanner-api-Realtime 