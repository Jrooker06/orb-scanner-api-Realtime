from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import json
import time
from datetime import datetime, timedelta, date
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')
VALID_LICENSE_KEYS = os.getenv('VALID_LICENSE_KEYS', 'test-license-123,prod-license-456').split(',')

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60
request_counts = {}

def validate_license_key(license_key):
    if not license_key:
        return False
    return license_key in VALID_LICENSE_KEYS

def rate_limit_check(license_key):
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW
    
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
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_key = request.headers.get('X-License-Key')
        
        if not validate_license_key(license_key):
            return jsonify({'error': 'Invalid license key'}), 401
        
        if not rate_limit_check(license_key):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return jsonify({
        'message': 'ORB Scanner Secure API',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'polygon_api_configured': bool(POLYGON_API_KEY),
        'finnhub_api_configured': bool(FINNHUB_API_KEY)
    })

@app.route('/api/gainers')
@require_license
def get_gainers():
    try:
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
        params = {'apiKey': POLYGON_API_KEY}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error fetching gainers: {e}")
        return jsonify({'error': 'Failed to fetch gainers'}), 500

@app.route('/api/test')
def test():
    return jsonify({
        'message': 'API is working!',
        'polygon_key': bool(POLYGON_API_KEY),
        'finnhub_key': bool(FINNHUB_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 