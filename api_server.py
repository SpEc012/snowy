from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import random
import os
import logging
import json
import datetime
import requests
import uuid
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Discord webhook URL for logging events
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1376808909943210035/ZsKgWLzzY1cQ54wuyA4oA0tGBj7h13lDyD0dGRtgn9RtFc01JrKac1zDLX2XY6oR_xy2'

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
        "origins": ["https://spec012.github.io"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "X-API-Key"],
        "expose_headers": ["X-API-Key"]
    }
})

# KeyAuth credentials
KEYAUTH_CONFIG = {
    "name": "Raven",
    "ownerid": "HgQcPwtKnr",
    "secret": "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
}

# API Security - Super simple for now
API_KEY = "rvn_sec"

def handle_keyauth_request(request_data, endpoint):
    try:
        # Add KeyAuth credentials to request
        data = {
            'type': endpoint,
            'name': KEYAUTH_CONFIG['name'],
            'ownerid': KEYAUTH_CONFIG['ownerid'],
            'secret': KEYAUTH_CONFIG['secret']
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

@app.route('/api/keyauth/<endpoint>', methods=['POST'])
def keyauth_proxy(endpoint):
    try:
        request_data = request.get_json()
        result = handle_keyauth_request(request_data, endpoint)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
                
                # Write the remaining accounts back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(accounts))
                
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

@app.route('/api/auth/webhook', methods=['POST', 'OPTIONS'])
def auth_webhook():
    """Endpoint to receive auth events (login/register) for Discord webhook"""
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
    
    try:
        # Get data from request
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        # Required fields
        if 'event_type' not in data:
            return jsonify({'success': False, 'message': 'Event type is required'}), 400
            
        # Validate event type
        event_type = data.get('event_type')
        if event_type not in ['login', 'register', 'logout']:
            return jsonify({'success': False, 'message': 'Invalid event type'}), 400
        
        # Add IP address if not provided
        if 'ip' not in data:
            data['ip'] = request.remote_addr
            
        # Send to Discord webhook
        send_discord_webhook(event_type, data)
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f'Error processing auth webhook: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stock/<service>', methods=['GET', 'OPTIONS'])
def generate_account(service):
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200

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

if __name__ == '__main__':
    # Make sure Stock folder exists
    if not os.path.exists(STOCK_DIR):
        os.makedirs(STOCK_DIR)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
