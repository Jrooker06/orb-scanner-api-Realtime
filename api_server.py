# =============================================================================
# SECURE API SERVER - DigitalOcean App Platform Backend
# =============================================================================

import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from functools import wraps
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get API keys from environment variables (set in DigitalOcean App Platform)
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')

# Finnhub API key should be provided by the user/client
# We'll get it from the request headers or parameters
FINNHUB_API_KEY = None  # Will be set dynamically from client requests

# License validation
VALID_LICENSE_KEYS = os.getenv('VALID_LICENSE_KEYS', 'test-license-123,prod-license-456').split(',')

# Rate limiting
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Cache for rate limiting
request_counts = {}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_license_key(license_key):
    """Validate the license key"""
    if not license_key:
        return False
    return license_key in VALID_LICENSE_KEYS

def rate_limit_check(license_key):
    """Check rate limiting for a license key"""
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
    # Clean old entries
    request_counts = {k: v for k, v in request_counts.items() if v['timestamp'] > window_start}
    
    if license_key not in request_counts:
        request_counts[license_key] = {'count': 1, 'timestamp': current_time}
        return True
    
    if request_counts[license_key]['timestamp'] < window_start:
        request_counts[license_key] = {'count': 1, 'timestamp': current_time}
        return True
    
    if request_counts[license_key]['count'] >= RATE_LIMIT_REQUESTS:
        return False
    
    request_counts[license_key]['count'] += 1
    return True

def require_license(f):
    """Decorator to require valid license key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_key = request.headers.get('X-License-Key')
        
        if not validate_license_key(license_key):
            return jsonify({'error': 'Invalid license key'}), 401
        
        if not rate_limit_check(license_key):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        return f(*args, **kwargs)
    return decorated_function

def get_market_date():
    """Get the appropriate date for market data"""
    today = date.today()
    
    # Check if today is a weekend
    if today.weekday() >= 5:  # Saturday = 5, Sunday = 6
        # Go back to Friday
        days_back = today.weekday() - 4
        return today - timedelta(days=days_back)
    
    return today

# =============================================================================
# POLYGON API FUNCTIONS
# =============================================================================

def get_finnhub_api_key():
    """Get Finnhub API key from request headers or parameters"""
    # Try to get from headers first
    api_key = request.headers.get('X-Finnhub-API-Key')
    if not api_key:
        # Try to get from query parameters
        api_key = request.args.get('finnhub_api_key')
    return api_key

def validate_finnhub_key(api_key):
    """Validate that a Finnhub API key is provided"""
    if not api_key:
        return False
    return len(api_key) > 0

def fetch_polygon_gainers():
    """Fetch top gainers from Polygon API"""
    try:
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
        params = {'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Error fetching gainers: {e}")
        return None

def fetch_polygon_historical(symbol, days_back=0, interval="1"):
    """Fetch historical data from Polygon API"""
    try:
        # Get appropriate date
        target_date = get_market_date()
        if days_back > 0:
            target_date = target_date - timedelta(days=days_back)
        
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Build URL
        if interval == "day":
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{date_str}/{date_str}"
        else:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{interval}/minute/{date_str}/{date_str}"
        
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': '1000',
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame if results exist
        if data.get('results'):
            df = pd.DataFrame(data['results'])
            df['t'] = pd.to_datetime(df['t'], unit='ms')
            df.set_index('t', inplace=True)
            
            # Rename columns
            df.rename(columns={
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
                'vw': 'vwap',
                'n': 'transactions'
            }, inplace=True)
            
            return df.to_dict('records')
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return None

def fetch_polygon_float(symbol):
    """Fetch float data from Polygon API"""
    try:
        url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
        params = {'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Error fetching float data for {symbol}: {e}")
        return None

def fetch_polygon_news(symbol):
    """Fetch news from Polygon API"""
    try:
        url = f"https://api.polygon.io/v2/reference/news"
        params = {
            'ticker': symbol,
            'limit': '10',
            'apiKey': POLYGON_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return None

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'polygon_api_configured': bool(POLYGON_API_KEY),
        'finnhub_api_configured': 'local_gui',
        'message': 'Finnhub API key is handled locally in the GUI'
    })

@app.route('/api/gainers', methods=['GET'])
@require_license
def get_gainers():
    """Get top gainers"""
    try:
        data = fetch_polygon_gainers()
        if data:
            return jsonify(data)
        else:
            return jsonify({'error': 'Failed to fetch gainers'}), 500
    except Exception as e:
        logger.error(f"Error in gainers endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/losers', methods=['GET'])
@require_license
def get_losers():
    """Get top losers"""
    try:
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/losers"
        params = {'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in losers endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/historical/<symbol>', methods=['GET'])
@require_license
def get_historical(symbol):
    """Get historical data for a symbol"""
    try:
        days_back = int(request.args.get('days_back', 0))
        interval = request.args.get('interval', '1')
        
        data = fetch_polygon_historical(symbol, days_back, interval)
        if data is not None:
            return jsonify({'results': data})
        else:
            return jsonify({'error': 'Failed to fetch historical data'}), 500
            
    except Exception as e:
        logger.error(f"Error in historical endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/float/<symbol>', methods=['GET'])
@require_license
def get_float(symbol):
    """Get float data for a symbol"""
    try:
        data = fetch_polygon_float(symbol)
        if data:
            return jsonify(data)
        else:
            return jsonify({'error': 'Failed to fetch float data'}), 500
            
    except Exception as e:
        logger.error(f"Error in float endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/news/<symbol>', methods=['GET'])
@require_license
def get_news(symbol):
    """Get news for a symbol"""
    try:
        data = fetch_polygon_news(symbol)
        if data:
            return jsonify(data)
        else:
            return jsonify({'error': 'Failed to fetch news'}), 500
            
    except Exception as e:
        logger.error(f"Error in news endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/volume/<symbol>', methods=['GET'])
@require_license
def get_volume(symbol):
    """Get volume data for a symbol"""
    try:
        # Get current day's data for volume
        data = fetch_polygon_historical(symbol, 0, "1")
        if data:
            total_volume = sum(item.get('volume', 0) for item in data)
            return jsonify({'volume': total_volume, 'symbol': symbol})
        else:
            return jsonify({'error': 'Failed to fetch volume data'}), 500
            
    except Exception as e:
        logger.error(f"Error in volume endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# FINNHUB API ENDPOINTS (User-provided API key)
# =============================================================================

# Note: Finnhub API calls are handled directly in the GUI
# The user enters their Finnhub API key in the settings
# This keeps the API key secure and local to the user's machine

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Check if API keys are configured
    if not POLYGON_API_KEY:
        logger.warning("POLYGON_API_KEY not configured")
    
    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not configured")
    
    # Get port from environment (DigitalOcean App Platform)
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Starting secure API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 