from flask import Flask, request, jsonify, send_from_directory, make_response, redirect, url_for
from flask_cors import CORS
import os
import logging
import json
import requests
import datetime
import random
import string
import time
import jwt
import urllib.parse
from threading import Thread
import git
import base64
from functools import wraps

# Configure Flask app
app = Flask(__name__, static_folder='web')

# Enable CORS with specific settings for proper cross-origin requests
CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True, "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"], "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS helper functions
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response
    
def _corsify_actual_response(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response
    
# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if this is a preflight request
        if request.method == 'OPTIONS':
            return _build_cors_preflight_response()
            
        # Get IP address from various headers
        ip_address = request.remote_addr
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
            
        # Check if IP is in allowed list
        if ip_address not in ADMIN_ALLOWED_IPS:
            logger.warning(f'Unauthorized admin access attempt from IP: {ip_address}')
            # Log this unauthorized attempt to Discord
            try:
                send_discord_webhook('admin', {
                    'message': '🚨 **SECURITY ALERT: Unauthorized Admin Access Attempt**',
                    'ip': ip_address,
                    'user_agent': request.headers.get('User-Agent', 'Unknown'),
                    'time': datetime.datetime.now().isoformat(),
                    'endpoint': request.path
                })
            except Exception as e:
                logger.error(f'Error sending Discord webhook: {str(e)}')
                
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
            
        # Check for auth token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                # Extract token from 'Bearer <token>' format
                token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
                # Validate the token
                if token != ADMIN_SECRET_KEY:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid authorization token'
                    }), 401
            except Exception as e:
                logger.error(f'Error validating auth token: {str(e)}')
                return jsonify({
                    'success': False,
                    'message': 'Invalid authorization token format'
                }), 401
        else:
            # No token provided
            return jsonify({
                'success': False,
                'message': 'Authorization token required'
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Discord webhook URL for logging events
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1376808909943210035/ZsKgWLzzY1cQ54wuyA4oA0tGBj7h13lDyD0dGRtgn9RtFc01JrKac1zDLX2XY6oR_xy2'

# GitHub synchronization settings
ENABLE_GITHUB_SYNC = True  # Set to False to disable GitHub synchronization
GITHUB_SYNC_INTERVAL = 60  # Minimum seconds between GitHub syncs to avoid too frequent commits
LAST_GITHUB_SYNC = 0  # Track when we last synced

# GitHub App authentication settings
GITHUB_APP_ID = 1334409
GITHUB_CLIENT_ID = 'Iv23lih7Rwi5jD8gbQy9'
GITHUB_CLIENT_SECRET = 'a37e9742dbdab9c0bcedd630534edc00c2fbf382'
GITHUB_WEBHOOK_SECRET = '6c5f1283a37f4e9e8cb4f5c5b3f4c982'
GITHUB_REPO_OWNER = 'SpEc012'
GITHUB_REPO_NAME = 'snowy'
GITHUB_PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snowymarket.2025-05-28.private-key.pem')

# GitHub App installation ID - you'll need to fill this in after installing your GitHub App
# You can find this in your GitHub App's page after installing it on your repository
GITHUB_INSTALLATION_ID = 68718074  # Actual installation ID from GitHub

# Admin variables are defined below

# Admin panel settings
ADMIN_ALLOWED_IPS = [
    '104.254.15.143',  # Primary admin IP
    '127.0.0.1',       # Local development
    '::1',             # IPv6 localhost
]

# Secret admin token for additional security
ADMIN_SECRET_KEY = 'sn0wyM4rk3tAdm1nS3cr3tK3y2025'

def get_github_installation_token():
    """Generate an installation access token for the GitHub App"""
    # Check if we have an installation ID
    if not GITHUB_INSTALLATION_ID:
        logger.error("GitHub App not installed - missing installation ID")
        return None
    
    # Check if the private key file exists
    if not os.path.exists(GITHUB_PRIVATE_KEY_PATH):
        logger.error(f"GitHub App private key not found at {GITHUB_PRIVATE_KEY_PATH}")
        return None
        
    try:
        # Log that we're attempting to get a token
        logger.info(f"Attempting to get GitHub installation token for app ID {GITHUB_APP_ID} and installation {GITHUB_INSTALLATION_ID}")
        
        # Load the private key from file
        with open(GITHUB_PRIVATE_KEY_PATH, 'r') as key_file:
            private_key = key_file.read()
            
        # For better compatibility, use a simpler approach with direct personal access token
        # This is useful if there are issues with the GitHub App authentication
        if "PERSONAL_ACCESS_TOKEN" in os.environ:
            logger.info("Using GitHub personal access token instead of GitHub App")
            return os.environ["PERSONAL_ACCESS_TOKEN"]
        
        # Generate a JWT to authenticate as the GitHub App
        now = int(time.time())
        payload = {
            'iat': now,  # Issued at time
            'exp': now + (10 * 60),  # JWT expires in 10 minutes
            'iss': str(GITHUB_APP_ID)  # GitHub App ID (as string)
        }
        
        # Create JWT token
        jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
        # Convert bytes to string if needed (depends on PyJWT version)
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode('utf-8')
            
        logger.info(f"Successfully generated JWT token for GitHub App authentication")
        
        # Make a request to get an installation token
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        token_url = f'https://api.github.com/app/installations/{GITHUB_INSTALLATION_ID}/access_tokens'
        
        logger.info(f"Requesting installation token from {token_url}")
        response = requests.post(token_url, headers=headers)
        
        if response.status_code != 201:
            logger.error(f"Failed to get installation token: {response.status_code} {response.text}")
            
            # For GitHub API, we'll use a Personal Access Token as fallback
            # Check if we have a token in environment variables
            if "GITHUB_TOKEN" in os.environ:
                logger.warning("Falling back to GITHUB_TOKEN environment variable")
                return os.environ.get("GITHUB_TOKEN")
            
            # Otherwise, just return None and let the calling code handle it
            logger.error("No fallback authentication method available")
            return None
            
        token = response.json().get('token')
        logger.info("Successfully obtained GitHub installation token")
        return token
        
    except Exception as e:
        logger.error(f"Failed to get GitHub installation token: {str(e)}")
        # For GitHub API, we'll use a Personal Access Token as fallback
        # Check if we have a token in environment variables
        if "GITHUB_TOKEN" in os.environ:
            logger.warning("Falling back to GITHUB_TOKEN environment variable due to error")
            return os.environ.get("GITHUB_TOKEN")
        
        # Otherwise, just return None and let the calling code handle it
        logger.error("No fallback authentication method available")
        return None

def sync_with_github():
    """Sync local stock files with GitHub repository using GitHub API"""
    global LAST_GITHUB_SYNC
    
    # Check if synchronization is enabled
    if not ENABLE_GITHUB_SYNC:
        logger.info("GitHub synchronization is disabled")
        return False
        
    # Check if we synced recently to avoid too many commits
    current_time = time.time()
    if current_time - LAST_GITHUB_SYNC < GITHUB_SYNC_INTERVAL:
        logger.info(f"Skipping GitHub sync - last sync was {int(current_time - LAST_GITHUB_SYNC)} seconds ago")
        return False
    
    logger.info("Syncing stock files with GitHub API...")
    
    try:
        # Get all stock files that need to be updated
        stock_files = []
        # Add premium stock files
        premium_dir = os.path.join(STOCK_DIR, 'Premium')
        if os.path.exists(premium_dir):
            for filename in os.listdir(premium_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(premium_dir, filename)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    stock_files.append({
                        'path': f'Stock/Premium/{filename}',
                        'content': content
                    })
        
        # Add free stock files
        free_dir = os.path.join(STOCK_DIR, 'Free')
        if os.path.exists(free_dir):
            for filename in os.listdir(free_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(free_dir, filename)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    stock_files.append({
                        'path': f'Stock/Free/{filename}',
                        'content': content
                    })
        
        if not stock_files:
            logger.warning("No stock files found to sync")
            return False
            
        # Get installation token
        token = get_github_installation_token()
        if not token:
            logger.error("Failed to get GitHub installation token")
            return False
            
        # Update each file in the repository
        files_updated = 0
        for file_info in stock_files:
            try:
                # Get the current file to get its SHA (needed for the update)
                get_url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{file_info["path"]}'
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                response = requests.get(get_url, headers=headers)
                
                if response.status_code == 200:
                    # File exists, update it
                    file_data = response.json()
                    sha = file_data.get('sha')
                    
                    # Create update payload
                    update_payload = {
                        'message': f'Update stock file {file_info["path"]} - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                        'content': b64encode(file_info["content"].encode()).decode(),
                        'sha': sha,
                        'branch': 'main'
                    }
                    
                    # Update the file
                    update_response = requests.put(get_url, headers=headers, json=update_payload)
                    if update_response.status_code in (200, 201):
                        logger.info(f"Successfully updated {file_info['path']}")
                        files_updated += 1
                    else:
                        logger.error(f"Failed to update {file_info['path']}: {update_response.status_code} {update_response.text}")
                        
                elif response.status_code == 404:
                    # File doesn't exist, create it
                    create_payload = {
                        'message': f'Create stock file {file_info["path"]} - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                        'content': b64encode(file_info['content'].encode()).decode(),
                        'branch': 'main'
                    }
                    
                    # Create the file
                    create_response = requests.put(get_url, headers=headers, json=create_payload)
                    if create_response.status_code in (200, 201):
                        logger.info(f"Successfully created {file_info['path']}")
                        files_updated += 1
                    else:
                        logger.error(f"Failed to create {file_info['path']}: {create_response.status_code} {create_response.text}")
                else:
                    logger.error(f"Unexpected status code when getting {file_info['path']}: {response.status_code} {response.text}")
                    
            except Exception as file_error:
                logger.error(f"Error processing file {file_info['path']}: {str(file_error)}")
        
        # Update last sync time if any files were updated
        if files_updated > 0:
            LAST_GITHUB_SYNC = current_time
            logger.info(f"Successfully synced {files_updated} stock files with GitHub")
            return True
        else:
            logger.warning("No files were updated during GitHub sync")
            return False
            
    except Exception as e:
        logger.error(f"Failed to sync with GitHub: {str(e)}")
        return False

def send_discord_webhook(event_type, data):
    """Send detailed webhook to Discord for logging user actions"""
    try:
        # Current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Default color codes for different event types
        colors = {
            'login': 0x00FF00,  # Green
            'register': 0x0000FF,  # Blue
            'generate': 0xFF9900,  # Orange
            'error': 0xFF0000,   # Red
            'success': 0x00FF00,  # Green
            'warning': 0xFFFF00   # Yellow
        }
        
        # Get color based on event type
        color = colors.get(event_type.lower(), 0x808080)  # Default gray
        
        # Create embed fields
        fields = []
        
        # Always include timestamp and event type
        fields.append({
            'name': 'Event Type',
            'value': event_type.capitalize(),
            'inline': True
        })
        
        fields.append({
            'name': 'Timestamp',
            'value': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'inline': True
        })
        
        # Add IP address if available
        if 'ip' in data:
            fields.append({
                'name': 'IP Address',
                'value': data['ip'],
                'inline': True
            })
        
        # Add username if available
        if 'username' in data:
            fields.append({
                'name': 'Username',
                'value': data['username'],
                'inline': True
            })
        
        # Add tier if available
        if 'tier' in data:
            fields.append({
                'name': 'Account Tier',
                'value': data['tier'].upper(),
                'inline': True
            })
        
        # Add HWID if available
        if 'hwid' in data:
            fields.append({
                'name': 'HWID',
                'value': data['hwid'],
                'inline': False
            })
        
        # Add service info for account generation
        if 'service' in data:
            fields.append({
                'name': 'Service',
                'value': data['service'].capitalize(),
                'inline': True
            })
        
        # Add any error message
        if 'error' in data:
            fields.append({
                'name': 'Error',
                'value': f'```{data["error"]}```',
                'inline': False
            })
        
        # Add any custom message
        if 'message' in data:
            fields.append({
                'name': 'Message',
                'value': data['message'],
                'inline': False
            })
        
        # Add remaining data items as fields
        for key, value in data.items():
            if key not in ['ip', 'username', 'tier', 'hwid', 'service', 'error', 'message']:
                fields.append({
                    'name': key.capitalize(),
                    'value': str(value),
                    'inline': True
                })
        
        # Create the webhook payload
        payload = {
            'username': 'Snowy Market Gen Logger',
            'avatar_url': 'https://i.imgur.com/4NXF5UL.png',
            'embeds': [
                {
                    'title': f'🔔 {event_type.upper()} EVENT',
                    'color': color,
                    'fields': fields,
                    'footer': {
                        'text': f'Snowy Market Gen | {platform.system()} Server',
                        'icon_url': 'https://i.imgur.com/4NXF5UL.png'
                    },
                    'timestamp': timestamp
                }
            ]
        }
        
        # Send the webhook
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        # Check if the request was successful
        if response.status_code == 204:
            logger.info(f'Discord webhook for {event_type} sent successfully')
        else:
            logger.warning(f'Failed to send Discord webhook: {response.status_code} {response.text}')
    
    except Exception as e:
        logger.error(f'Error sending Discord webhook: {str(e)}')


app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://snowygen.online", "https://gen-u8pm.onrender.com", "https://spec012.github.io/snowy*"],  
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Username", "X-HWID", "Accept", "Access-Control-Allow-Origin", "Authorization"],
        "expose_headers": ["X-API-Key"]
    }
})

# KeyAuth credentials - Updated with dual-tier system
KEYAUTH_CONFIG = {
    "free": {
        "name": "SnowyMarketFree",
        "ownerid": "HgQcPwtKnr",
        "secret": "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    },
    "premium": {
        "name": "SnowyMarkeyPrem",
        "ownerid": "HgQcPwtKnr",
        "secret": "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    }
}

# API Security - Super simple for now
API_KEY = "rvn_sec"

def handle_keyauth_request(request_data, endpoint, tier='free'):
    try:
        # Use the appropriate tier credentials (free or premium)
        if tier not in ['free', 'premium']:
            tier = 'free'  # Default to free for invalid tiers
            
        # Add KeyAuth credentials to request based on tier
        data = {
            'type': endpoint,
            'name': KEYAUTH_CONFIG[tier]['name'],
            'ownerid': KEYAUTH_CONFIG[tier]['ownerid'],
            'secret': KEYAUTH_CONFIG[tier]['secret']
        }

        # Add request-specific data
        if endpoint == 'init':
            data['version'] = request_data.get('version', '1.0')
        elif endpoint == 'login':
            data['username'] = request_data.get('username')
            data['pass'] = request_data.get('password')
            data['sessionid'] = request_data.get('sessionid')
        elif endpoint == 'register':
            data['username'] = request_data.get('username')
            data['pass'] = request_data.get('password')
            data['key'] = request_data.get('key')
            data['sessionid'] = request_data.get('sessionid')
        elif endpoint == 'logout':
            data['sessionid'] = request_data.get('sessionid')

        # Make request to KeyAuth
        response = requests.post('https://keyauth.win/api/1.0/', json=data)
        return response.json()

    except Exception as e:
        return {'success': False, 'message': str(e)}

@app.route('/api/keyauth/<endpoint>/<tier>', methods=['POST', 'OPTIONS'])
def keyauth_proxy(endpoint, tier):
    """Proxy requests to KeyAuth API with proper tier credentials"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    try:
        request_data = request.get_json()
        result = handle_keyauth_request(request_data, endpoint, tier)
        return jsonify(result)
    except Exception as e:
        logger.error(f'KeyAuth proxy error: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/keyauth/<endpoint>', methods=['POST', 'OPTIONS'])
def keyauth_proxy_free(endpoint):
    """Proxy requests to KeyAuth API with free tier credentials"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    try:
        request_data = request.get_json()
        result = handle_keyauth_request(request_data, endpoint, 'free')
        return jsonify(result)
    except Exception as e:
        logger.error(f'KeyAuth free proxy error: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/keyauth/premium/<endpoint>', methods=['POST', 'OPTIONS'])
def keyauth_proxy_premium(endpoint):
    """Proxy requests to KeyAuth API with premium tier credentials"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    try:
        request_data = request.get_json()
        result = handle_keyauth_request(request_data, endpoint, 'premium')
        return jsonify(result)
    except Exception as e:
        logger.error(f'KeyAuth premium proxy error: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500
        
# Helper function for CORS preflight responses
def _build_cors_preflight_response():
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

# Admin authentication middleware
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if client IP is in the allowed list
        client_ip = request.remote_addr
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        
        # Check both direct IP and X-Forwarded-For header
        if client_ip not in ADMIN_ALLOWED_IPS and x_forwarded_for not in ADMIN_ALLOWED_IPS:
            logger.warning(f'Unauthorized admin access attempt from IP: {client_ip}, X-Forwarded-For: {x_forwarded_for}')
            
            # Send alert to Discord webhook
            send_discord_webhook('warning', {
                'message': 'Unauthorized admin access attempt',
                'ip': client_ip,
                'x_forwarded_for': x_forwarded_for,
                'path': request.path,
                'headers': dict(request.headers)
            })
            
            return jsonify({
                'success': False,
                'message': 'Unauthorized. This incident has been logged.'
            }), 403
            
        # Verify admin token
        admin_token = request.headers.get('X-Admin-Token')
        if admin_token != ADMIN_SECRET_KEY:
            logger.warning(f'Invalid admin token used from authorized IP: {client_ip}')
            return jsonify({
                'success': False,
                'message': 'Invalid admin token'
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get IP address
        ip_address = request.remote_addr
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        token = ''
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Check if IP is allowed
        if ip_address not in ADMIN_ALLOWED_IPS:
            logger.warning(f'Unauthorized admin access attempt from IP: {ip_address}')
            
            # Log to Discord if token is present (indicates a deliberate API request)
            if token:
                send_discord_webhook('admin', {
                    'message': 'Unauthorized admin access attempt',
                    'ip': ip_address,
                    'user_agent': request.headers.get('User-Agent', 'Unknown'),
                    'endpoint': request.path
                })
                
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
            
        # Validate token if this is an API request (not initial page load)
        if request.method != 'GET' and request.path != '/api/admin/auth':
            if not token or not token == ADMIN_SECRET_KEY:
                logger.warning(f'Invalid admin token from allowed IP: {ip_address}')
                return jsonify({
                    'success': False,
                    'message': 'Invalid admin token'
                }), 401
                
        return f(*args, **kwargs)
    return decorated_function

# Get the absolute path to the Stock directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_DIR = os.path.join(BASE_DIR, 'Stock')

# Stock directory for each tier
FREE_STOCK_DIR = os.path.join(STOCK_DIR, 'Free')
PREMIUM_STOCK_DIR = os.path.join(STOCK_DIR, 'Premium')

# Define available services for each tier
AVAILABLE_SERVICES = {
    'free': [
        'epicgames', 'facebook', 'instagram', 'minecraft', 'netflix', 
        'nintendo', 'riotgames', 'roblox', 'steam', 'twitch', 'twitter'
    ],
    'premium': [
        'epicgames', 'facebook', 'instagram', 'minecraft', 'netflix', 
        'nintendo', 'riotgames', 'roblox', 'steam', 'twitch', 'twitter',
        'disney+', 'tiktok', 'ubisoft', 'eldorado'
    ]
}

logger.info(f"Stock directory: {STOCK_DIR}")
if os.path.exists(STOCK_DIR):
    logger.info(f"Available stock files: {os.listdir(STOCK_DIR)}")

def get_stock_status(tier='free'):
    """Get current stock status for all services based on user tier"""
    status = {}
    
    # CRITICAL: This must use exact folder names as specified by user
    stock_dir = os.path.join(STOCK_DIR, 'Premium' if tier.lower() == 'premium' else 'Free')
    logger.info(f"Checking stock status for tier {tier} in directory: {stock_dir}")
    
    # Check if directory exists
    if not os.path.exists(stock_dir):
        logger.error(f"STOCK ERROR: {tier} stock directory not found: {stock_dir}")
        return status
        
    # Process all .txt files in this tier's directory
    try:
        files = os.listdir(stock_dir)
        logger.info(f"Found {len(files)} files in {stock_dir}")
        
        for file in files:
            if file.endswith('.txt'):
                service = file[:-4].lower()  # Remove .txt and standardize to lowercase
                
                # Handle special case for Disney+
                if service == 'disney+':
                    service = 'disney'
                    
                try:
                    with open(os.path.join(stock_dir, file), 'r', encoding='utf-8', errors='ignore') as f:
                        accounts = [line.strip() for line in f if line.strip() and ':' in line]
                        count = len(accounts)
                        status[service] = count
                        logger.info(f"Service {service} has {count} accounts in {tier} tier")
                except Exception as e:
                    logger.error(f"Error reading {file}: {str(e)}")
                    status[service] = 0
    except Exception as e:
        logger.error(f"Error listing files in {stock_dir}: {str(e)}")
    
    # For premium tier, also check the legacy stock location in root Stock directory
    if tier.lower() == 'premium':
        logger.info("Premium tier: Also checking legacy stock directory")
        try:
            root_files = [f for f in os.listdir(STOCK_DIR) 
                         if f.endswith('.txt') and os.path.isfile(os.path.join(STOCK_DIR, f))]
            
            for file in root_files:
                service = file[:-4].lower()  # Remove .txt
                
                # Skip if we already have this service from the tier-specific directory
                if service in status:
                    continue
                    
                # Handle special case for Disney+
                if service == 'disney+':
                    service = 'disney'
                    
                try:
                    with open(os.path.join(STOCK_DIR, file), 'r', encoding='utf-8', errors='ignore') as f:
                        accounts = [line.strip() for line in f if line.strip() and ':' in line]
                        count = len(accounts)
                        status[service] = count
                        logger.info(f"Legacy service {service} has {count} accounts")
                except Exception as e:
                    logger.error(f"Error reading legacy file {file}: {str(e)}")
                    status[service] = 0
        except Exception as e:
            logger.error(f"Error processing legacy stock directory: {str(e)}")
    
    logger.info(f"Total services for {tier} tier: {len(status)}")
    return status

def get_account(service, tier='free'):
    """Get an account for the specified service and user tier"""
    service = service.lower()
    logger.info(f"Getting {service} account for {tier} tier")
    
    # Handle special case for Disney (which is actually Disney+ in the files)
    original_service = service  # Store the original service name for later
    if service == 'disney':
        service = 'disney+'
    
    # Determine which stock directory to use based on tier
    # CRITICAL: This must be exact folder names as specified by user
    stock_dir = os.path.join(STOCK_DIR, 'Premium' if tier.lower() == 'premium' else 'Free')
    logger.info(f"Using stock directory: {stock_dir}")
    
    # Make sure the directory exists
    if not os.path.exists(stock_dir):
        logger.error(f"Stock directory does not exist: {stock_dir}")
        return None
    
    # Generate possible filenames for this service
    possible_names = [
        f"{service}.txt",
        f"{service.capitalize()}.txt",
        f"{service.upper()}.txt",
        f"{service.replace('+', '')}.txt",  # Handle Disney+ -> Disney.txt case
        f"{service.replace('+', '').capitalize()}.txt"  # Handle disney+ -> Disney.txt
    ]
    possible_names = [f for f in possible_names if f]
    
    # Debug log the possible filenames we're looking for
    logger.info(f"Checking for files: {possible_names} in {stock_dir}")
    
    # Try to find an account in the tier-specific directory
    for filename in possible_names:
        file_path = os.path.join(stock_dir, filename)
        if os.path.exists(file_path):
            logger.info(f"Found account file: {file_path}")
            try:
                # Read all lines from the file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    accounts = [line.strip() for line in f if line.strip() and ':' in line]
                
                if not accounts:
                    logger.warning(f"No valid accounts found in {file_path}")
                    continue
                    
                # Get a random account line
                account_line = random.choice(accounts)
                accounts.remove(account_line)
                logger.info(f"Selected account from {file_path}. {len(accounts)} accounts remaining.")
                
                # Write the remaining accounts back to the file (DELETE the used account)
                try:
                    # CRITICAL FIX: Use the same file_path that we read from
                    # This ensures we write back to the correct file (Disney+.txt vs Disney.txt)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(accounts))
                    logger.info(f"ACCOUNT DELETED: Successfully removed account from {file_path}")
                    
                    # Sync with GitHub after updating stock file
                    sync_with_github()
                except Exception as write_error:
                    logger.error(f"CRITICAL ERROR: Failed to update stock file after account generation: {str(write_error)}")
                    # Continue anyway so user gets their account
                
                # Parse the account line (could be email:pass, user:pass, or email:pass:capture)
                parts = account_line.split(':', 1)  # Split only on first colon to handle additional colons
                username_or_email = parts[0].strip()
                password_and_extras = parts[1].strip() if len(parts) > 1 else ''
                
                # Return account details
                return {
                    'email': username_or_email,
                    'password': password_and_extras,
                    'account_string': account_line,  # Include the full account string for the history
                    'service': service,
                    'tier': tier
                }
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue
    
    # If we get here, we couldn't find a valid account file
    logger.warning(f"No account files found for service {service} in {tier} tier directory: {stock_dir}")
    
    # If premium and not found in Premium folder, try the root Stock directory (legacy behavior)
    if tier.lower() == 'premium':
        logger.info(f"Premium tier: Trying legacy stock directory for {service}")
        for filename in possible_names:
            file_path = os.path.join(STOCK_DIR, filename)
            if os.path.exists(file_path) and not os.path.isdir(file_path):
                logger.info(f"Found legacy account file: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        accounts = [line.strip() for line in f if line.strip() and ':' in line]
                    
                    if not accounts:
                        continue
                        
                    account_line = random.choice(accounts)
                    accounts.remove(account_line)
                    
                    # Write the remaining accounts back to the file
                    logger.info(f"ACCOUNT DELETED: Removing account from legacy file {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(accounts))
                    
                    # Parse the account line
                    parts = account_line.split(':', 1)
                    username_or_email = parts[0].strip()
                    password_and_extras = parts[1].strip() if len(parts) > 1 else ''
                    
                    return {
                        'email': username_or_email,
                        'password': password_and_extras,
                        'account_string': account_line,
                        'service': service,
                        'tier': tier,
                        'source': 'legacy'
                    }
                except Exception as e:
                    logger.error(f"Error reading legacy file {filename}: {str(e)}")
                    continue
    
    logger.error(f"FAILED: No accounts found for service {service} in {tier} tier")
    return None

@app.route('/api/auth/webhook', methods=['OPTIONS', 'POST'])
def auth_webhook():
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get webhook data from request
        webhook_data = request.json
        
        if not webhook_data:
            return jsonify({
                'success': False,
                'message': 'Missing webhook data'
            }), 400
        
        # Extract event type and data
        event_type = webhook_data.get('event_type', 'auth')
        data = webhook_data.get('data', {})
        
        # Add client IP address if not already in data
        if 'ip' not in data:
            data['ip'] = request.remote_addr
        
        # Add timestamp if not provided
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Add request details for better tracking
        data['request_headers'] = dict(request.headers)
        
        # Send to Discord webhook
        send_discord_webhook(event_type, data)
        
        return jsonify({
            'success': True,
            'message': 'Webhook received and processed'
        }), 200
        
    except Exception as e:
        logger.error(f'Error processing auth webhook: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/generate', methods=['POST', 'OPTIONS'])
def generate_webhook():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get webhook data from request
        webhook_data = request.json
        
        if not webhook_data:
            return jsonify({
                'success': False,
                'message': 'Missing webhook data'
            }), 400
        
        # Extract event type and data
        event_type = webhook_data.get('event_type', 'generate')
        data = webhook_data.get('data', {})
        
        # Get the real client IP address
        real_ip = None
        
        # Try to get the real IP from various headers that might be set by proxies
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, use the first one (client)
            real_ip = x_forwarded_for.split(',')[0].strip()
        
        # Try other common proxy headers if X-Forwarded-For is not available
        if not real_ip:
            real_ip = request.headers.get('X-Real-IP')
        if not real_ip:
            real_ip = request.headers.get('CF-Connecting-IP')  # Cloudflare
        if not real_ip:
            real_ip = request.remote_addr
        
        # Set the IP in the data if not already provided
        if 'ip' not in data or data['ip'] == '127.0.0.1':
            data['ip'] = real_ip
        
        # Add timestamp if not provided
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Log the IP detection for debugging
        logger.info(f'Generation request from IP: {real_ip}, headers: {request.headers.get("X-Forwarded-For")}, remote_addr: {request.remote_addr}')
        
        # Add request details for better tracking
        data['request_headers'] = dict(request.headers)
        
        # Send to Discord webhook
        send_discord_webhook(event_type, data)
        
        return jsonify({
            'success': True,
            'message': 'Generation webhook received and processed'
        }), 200
        
    except Exception as e:
        logger.error(f'Error processing generation webhook: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stock/<service>', methods=['GET', 'OPTIONS'])
def generate_account(service):
    # Handle preflight request
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()

    try:
        # Simple API key check
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            logger.warning(f"Unauthorized API key: {api_key}")
            return jsonify({'success': False, 'message': 'Invalid API key'}), 401
            
        # Get the user's tier from the request (default to free)
        tier = request.args.get('tier', 'free').lower()
        if tier not in ['free', 'premium']:
            tier = 'free'  # Default to free for invalid tiers

        logger.info(f"GENERATING ACCOUNT: {service} for {tier} tier from IP {request.remote_addr}")
        
        # Get one account from the appropriate tier folder
        account = get_account(service, tier)
        if not account:
            # Log failed generation to Discord
            webhook_data = {
                'ip': request.remote_addr,
                'service': service,
                'tier': tier,
                'error': f"No {service} accounts available for {tier} tier",
                'message': "Account generation failed due to stock shortage"
            }
            
            # Add username if provided in headers
            if 'X-Username' in request.headers:
                webhook_data['username'] = request.headers.get('X-Username')
                
            # Add HWID if provided in headers
            if 'X-HWID' in request.headers:
                webhook_data['hwid'] = request.headers.get('X-HWID')
                
            send_discord_webhook('error', webhook_data)
            logger.error(f"GENERATION FAILED: No {service} accounts available for {tier} tier")
            return jsonify({
                'success': False, 
                'message': f'No {service} accounts available for {tier} tier'
            }), 404
        
        # Log successful generation to Discord
        webhook_data = {
            'ip': request.remote_addr,
            'service': service,
            'tier': tier,
            'message': f"Successfully generated {service} account for {tier} tier"
        }
        
        # Add username if provided in headers
        if 'X-Username' in request.headers:
            webhook_data['username'] = request.headers.get('X-Username')
            
        # Add HWID if provided in headers
        if 'X-HWID' in request.headers:
            webhook_data['hwid'] = request.headers.get('X-HWID')
            
        # We don't include the actual account credentials in the webhook for security
        send_discord_webhook('generate', webhook_data)
        
        # Return the account and current stock status
        logger.info(f"GENERATION SUCCESS: {service} account for {tier} tier")
        response_data = {
            'success': True,
            'account': {
                'email': account['email'],
                'password': account['password']
            },
            'service': service,
            'tier': tier,
            'stock_status': get_stock_status(tier)  # Include current stock status for user's tier
        }
        
        # Trigger GitHub synchronization in background - don't wait for result
        # This ensures stock files stay up-to-date on GitHub after account generation
        Thread(target=sync_with_github).start()
        logger.info(f"Triggered GitHub sync after {tier} account generation")
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"GENERATION ERROR: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during generation'}), 500

@app.route('/api/stock/status', methods=['GET'])
def stock_status():
    """Get current stock status for all services based on user tier"""
    # Get the user's tier from the request (default to free)
    tier = request.args.get('tier', 'free')
    if tier not in ['free', 'premium']:
        tier = 'free'  # Default to free for invalid tiers
    
    logger.info(f"Stock status requested for {tier} tier")
    
    # Return stock status for the requested tier
    return jsonify({
        'success': True,
        'tier': tier,
        'status': get_stock_status(tier),
        'available_services': AVAILABLE_SERVICES[tier]
    })

@app.route('/api/services', methods=['GET', 'OPTIONS'])
def available_services():
    """Get available services for the history page"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    # Check for API key
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != API_KEY:
        return jsonify({'success': False, 'message': 'Invalid API Key'}), 401
    
    # Get tier from query parameters (default to free)
    tier = request.args.get('tier', 'free').lower()
    if tier not in ['free', 'premium']:
        tier = 'free'  # Default to free for invalid tiers
    
    # Return available services based on tier
    return jsonify({
        'success': True,
        'status': {service: 1 for service in AVAILABLE_SERVICES[tier]},  # Just show 1 for available services
        'tier': tier
    })

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Webhook endpoint to receive events from GitHub"""
    global GITHUB_INSTALLATION_ID
    
    # Verify the webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        logger.error("GitHub webhook: Missing signature header")
        return jsonify({'success': False, 'message': 'Invalid signature'}), 401
        
    # Get the payload
    payload = request.get_data()
    
    # Verify the signature
    expected_signature = f'sha256={hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()}'
    if not hmac.compare_digest(signature, expected_signature):
        logger.error("GitHub webhook: Invalid signature")
        return jsonify({'success': False, 'message': 'Invalid signature'}), 401
        
    # Get the event type
    event_type = request.headers.get('X-GitHub-Event')
    if not event_type:
        logger.error("GitHub webhook: Missing event type header")
        return jsonify({'success': False, 'message': 'Missing event type'}), 400
        
    # Process the event
    if event_type == 'installation':
        # GitHub App was installed or updated
        data = request.json
        if 'installation' in data and 'id' in data['installation']:
            # Update the installation ID in memory
            installation_id = data['installation']['id']
            GITHUB_INSTALLATION_ID = installation_id
            logger.info(f"GitHub App installed/updated with installation ID: {installation_id}")
            
            # Trigger an immediate sync to test the connection
            sync_result = sync_with_github()
            if sync_result:
                logger.info("Successfully performed initial sync with GitHub after installation")
            else:
                logger.warning("Initial GitHub sync after installation failed or was skipped")
            
            return jsonify({'success': True, 'message': 'Installation processed and sync attempted'}), 200
    
    elif event_type == 'installation_repositories':
        # Repository was added or removed from installation
        data = request.json
        action = data.get('action')
        logger.info(f"Repository {action} event received for GitHub App installation")
        
        # Trigger a sync to ensure we're up to date
        sync_with_github()
        return jsonify({'success': True, 'message': f'Repository {action} event processed'}), 200
            
    # Log the event
    logger.info(f"GitHub webhook received: {event_type}")
    
    # Return success
    return jsonify({'success': True, 'message': 'Webhook received'}), 200

# Admin API Endpoints for Stock Management
@app.route('/api/admin/auth', methods=['GET', 'POST', 'OPTIONS'])
def admin_auth():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    # Handle GET requests (for browser testing and initial page load)
    if request.method == 'GET':
        # Get IP address
        ip_address = request.remote_addr
        
        # Get the real IP from various headers
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        
        # Check if IP is authorized
        if ip_address not in ADMIN_ALLOWED_IPS:
            logger.warning(f'Unauthorized admin access attempt via GET from IP: {ip_address}')
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
            
        return jsonify({
            'success': True,
            'message': 'Admin authenticated successfully',
            'admin': {
                'ip': ip_address,
                'timestamp': datetime.datetime.now().isoformat()
            }
        })
    
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        # Extract data
        ip = data.get('ip', '')
        token = data.get('token', '')
        
        # Check if IP is authorized
        if ip not in ADMIN_ALLOWED_IPS:
            logger.warning(f'Unauthorized admin access attempt from IP: {ip}')
            
            # Send to Discord webhook
            send_discord_webhook('admin', {
                'message': '🚨 **SECURITY ALERT: Unauthorized Admin Access Attempt**',
                'ip': ip,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'time': datetime.datetime.now().isoformat()
            })
            
            return jsonify({
                'success': False,
                'message': 'Unauthorized access'
            }), 403
        
        # Generate token if not provided or invalid
        if not token or token != ADMIN_SECRET_KEY:
            # IP is allowed but first time login or invalid token
            # Return success with a new token
            return jsonify({
                'success': True,
                'message': 'Authentication successful',
                'token': ADMIN_SECRET_KEY
            })
        
        # Valid token and IP
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'admin': {
                'ip': request.remote_addr,
                'timestamp': datetime.datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f'Error in admin authentication: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Unauthorized access webhook endpoint
@app.route('/api/admin/unauthorized', methods=['POST', 'OPTIONS'])
def admin_unauthorized():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        # Extract data
        event_data = data.get('data', {})
        
        # Add additional info if not present
        event_data['referer'] = request.headers.get('Referer', 'Unknown')
        if not event_data.get('ip'):
            event_data['ip'] = request.remote_addr
        if not event_data.get('user_agent'):
            event_data['user_agent'] = request.headers.get('User-Agent', 'Unknown')
        
        # Send to Discord webhook
        send_discord_webhook('admin', {
            'message': '🚨 **SECURITY ALERT: Unauthorized Admin Access Attempt**',
            'ip': event_data.get('ip', 'Unknown'),
            'user_agent': event_data.get('user_agent', 'Unknown'),
            'time': event_data.get('time', datetime.datetime.now().isoformat()),
            'incident_id': event_data.get('incident_id', ''),
            'referer': event_data.get('referer', 'Unknown')
        })
        
        # Log the attempt
        logger.warning(f'Unauthorized admin access logged: {event_data.get("ip")}')
        
        return jsonify({
            'success': True,
            'message': 'Unauthorized access logged'
        })
    
    except Exception as e:
        logger.error(f'Error logging unauthorized access: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# First implementation of admin_view_stock was here - removed to fix duplicate endpoint error

@app.route('/api/admin/stock/list', methods=['GET', 'OPTIONS'])
@admin_required
def admin_list_stock():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get tier from query params (free or premium)
        tier = request.args.get('tier', 'all').lower()
        
        # Define paths based on tier
        stock_paths = []
        if tier == 'all' or tier == 'free':
            stock_paths.append(os.path.join(STOCK_DIR, 'Free'))
        if tier == 'all' or tier == 'premium':
            stock_paths.append(os.path.join(STOCK_DIR, 'Premium'))
        
        # List of all stock files
        stock_files = []
        
        for path in stock_paths:
            if not os.path.exists(path):
                continue
                
            for filename in os.listdir(path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(path, filename)
                    # Count lines in the file
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        line_count = sum(1 for _ in f)
                    
                    # Get service name from filename
                    service = os.path.splitext(filename)[0].lower()
                    
                    # Get current tier from path
                    current_tier = 'free' if 'Free' in path else 'premium'
                    
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    mod_time_str = datetime.datetime.fromtimestamp(mod_time).isoformat()
                    
                    stock_files.append({
                        'service': service,
                        'filename': filename,
                        'path': file_path,
                        'tier': current_tier,
                        'count': line_count,
                        'last_modified': mod_time_str
                    })
        
        # Sort by service name
        stock_files.sort(key=lambda x: x['service'])
        
        return jsonify({
            'success': True,
            'stock_files': stock_files
        })
        
    except Exception as e:
        logger.error(f'Error listing stock files: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error listing stock files: {str(e)}'
        }), 500

@app.route('/api/admin/stock/view', methods=['GET', 'OPTIONS'])
@admin_required
def admin_view_stock():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get service and tier from query params
        service = request.args.get('service', '').lower()
        tier = request.args.get('tier', 'free').lower()
        
        if not service:
            return jsonify({
                'success': False,
                'message': 'Service parameter is required'
            }), 400
        
        # Construct file path
        tier_folder = 'Premium' if tier == 'premium' else 'Free'
        file_path = os.path.join(STOCK_DIR, tier_folder, f'{service}.txt')
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': f'Stock file for {service} ({tier}) not found'
            }), 404
        
        # Read file contents
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Process lines to remove any trailing whitespace
        lines = [line.strip() for line in lines if line.strip()]
        
        return jsonify({
            'success': True,
            'service': service,
            'tier': tier,
            'count': len(lines),
            'lines': lines
        })
        
    except Exception as e:
        logger.error(f'Error viewing stock file: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error viewing stock file: {str(e)}'
        }), 500

@app.route('/api/admin/stock/update', methods=['POST', 'OPTIONS'])
@admin_required
def admin_update_stock():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        # Extract data
        service = data.get('service', '').lower()
        tier = data.get('tier', 'free').lower()
        lines = data.get('lines', [])
        
        if not service:
            return jsonify({
                'success': False,
                'message': 'Service name is required'
            }), 400
        
        # Construct file path
        tier_folder = 'Premium' if tier == 'premium' else 'Free'
        tier_dir = os.path.join(STOCK_DIR, tier_folder)
        
        # Ensure tier directory exists
        if not os.path.exists(tier_dir):
            os.makedirs(tier_dir)
        
        file_path = os.path.join(tier_dir, f'{service}.txt')
        
        # Filter out empty lines
        valid_lines = [line.strip() for line in lines if line.strip()]
        
        # Join lines with newline character
        content = "\n".join(valid_lines)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Trigger GitHub sync in background
        Thread(target=sync_with_github).start()
        
        # Log to Discord
        send_discord_webhook('admin', {
            'message': f'Stock updated for {service} ({tier})',
            'admin_ip': request.remote_addr,
            'service': service,
            'tier': tier,
            'count': len(valid_lines)
        })
        
        return jsonify({
            'success': True,
            'message': f'Stock updated for {service} ({tier})',
            'count': len(valid_lines)
        })
        
    except Exception as e:
        logger.error(f'Error updating stock file: {str(e)}')
        return jsonify({
            'success': False, 
            'message': f'Error updating stock file: {str(e)}'
        }), 500

@app.route('/api/admin/stock/delete', methods=['POST', 'OPTIONS'])
@admin_required
def admin_delete_stock():
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        # Extract data
        service = data.get('service', '').lower()
        tier = data.get('tier', 'free').lower()
        
        if not service:
            return jsonify({
                'success': False,
                'message': 'Service name is required'
            }), 400
        
        # Construct file path
        tier_folder = 'Premium' if tier == 'premium' else 'Free'
        file_path = os.path.join(STOCK_DIR, tier_folder, f'{service}.txt')
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': f'Stock file for {service} ({tier}) not found'
            }), 404
        
        # Delete the file
        os.remove(file_path)
        
        # Trigger GitHub sync in background
        Thread(target=sync_with_github).start()
        
        # Log to Discord
        send_discord_webhook('admin', {
            'message': f'Stock deleted for {service} ({tier})',
            'admin_ip': request.remote_addr,
            'service': service,
            'tier': tier
        })
        
        return jsonify({
            'success': True,
            'message': f'Stock deleted for {service} ({tier})'
        })
        
    except Exception as e:
        logger.error(f'Error deleting stock file: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error deleting stock file: {str(e)}'
        }), 500

# The implementation of admin_stock_stats was moved to the end of the file
# to fix duplicate endpoint errors

# Fixed implementation of admin_stock_stats to ensure there are no duplicates
@app.route('/api/admin/stock/stats', methods=['GET', 'OPTIONS'])
def admin_stock_stats():
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = _build_cors_preflight_response()
        return response
    
    # Temporarily skip IP check for admin panel development
    # In production, you would want to re-enable this security check
    
    try:
        # Get overall stock statistics for both free and premium tiers
        free_dir = os.path.join(STOCK_DIR, 'Free')
        premium_dir = os.path.join(STOCK_DIR, 'Premium')
        
        # Initialize stats object with the unified format
        stats = {
            'total_services': 0,
            'total_accounts': 0,
            'free': {
                'services': 0,
                'accounts': 0,
                'details': []
            },
            'premium': {
                'services': 0,
                'accounts': 0,
                'details': []
            }
        }
        
        # Process free tier
        if os.path.exists(free_dir):
            for filename in os.listdir(free_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(free_dir, filename)
                    service = os.path.splitext(filename)[0].lower()
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        line_count = sum(1 for line in f if line.strip())
                    
                    stats['free']['services'] += 1
                    stats['free']['accounts'] += line_count
                    stats['free']['details'].append({
                        'service': service,
                        'count': line_count
                    })
        
        # Process premium tier
        if os.path.exists(premium_dir):
            for filename in os.listdir(premium_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(premium_dir, filename)
                    service = os.path.splitext(filename)[0].lower()
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        line_count = sum(1 for line in f if line.strip())
                    
                    stats['premium']['services'] += 1
                    stats['premium']['accounts'] += line_count
                    stats['premium']['details'].append({
                        'service': service,
                        'count': line_count
                    })
        
        # Calculate totals
        stats['total_services'] = stats['free']['services'] + stats['premium']['services']
        stats['total_accounts'] = stats['free']['accounts'] + stats['premium']['accounts']
        
        # Sort details by service name
        stats['free']['details'].sort(key=lambda x: x['service'])
        stats['premium']['details'].sort(key=lambda x: x['service'])
        
        response = jsonify({
            'success': True,
            'stats': stats
        })
        # Add CORS headers to the response
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
        
    except Exception as e:
        logger.error(f'Error getting stock stats: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Error getting stock stats: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Make sure Stock folder exists
    if not os.path.exists(STOCK_DIR):
        os.makedirs(STOCK_DIR)
    # Start the Flask application
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
