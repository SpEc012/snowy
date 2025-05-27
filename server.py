from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from urllib.error import URLError
import ssl
import os
import random
import sys
import time
import hashlib

# Security check - prevent direct access to this file
if __name__ == '__main__' and len(sys.argv) == 1:
    # Only run the server when properly executed from the command line
    pass
elif __name__ == '__main__' and sys.argv[1] != hashlib.sha256(b'snowygen_auth_token').hexdigest():
    print('Unauthorized access attempt blocked')
    sys.exit(1)

# Log access attempts for security
def log_access(ip, path, method):
    try:
        with open('access_log.txt', 'a') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - IP: {ip} - {method} {path}\n')
    except Exception as e:
        print(f'Error logging access: {e}')

# KeyAuth credentials for both tiers
KEYAUTH_CONFIG = {
    "premium": {
        "name": "SnowyMarkeyPrem",
        "ownerid": "HgQcPwtKnr",
        "secret": "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    },
    "free": {
        "name": "SnowyMarketFree",
        "ownerid": "HgQcPwtKnr",
        "secret": "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    }
}

class KeyAuthHandler(SimpleHTTPRequestHandler):
    # List of restricted files and directories that should not be directly accessible
    RESTRICTED_FILES = [
        'server.py', 'server.js', '.htaccess', 'access_log.txt',
        'keyauth.json', '.git', '.env', 'config.json'
    ]
    
    # List of restricted file extensions
    RESTRICTED_EXTENSIONS = ['.py', '.env', '.git', '.json', '.log', '.md', '.sh', '.bat']
    
    # Security token used for API access validation
    API_TOKEN = hashlib.sha256(b'snowygen_secure_api_key').hexdigest()
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        # Add security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
    
    def is_restricted_path(self, path):
        # Remove leading slash and normalize
        path = path.lstrip('/').replace('\\', '/')
        
        # Check for restricted files
        for restricted in self.RESTRICTED_FILES:
            if path == restricted or path.startswith(restricted + '/') or '/' + restricted + '/' in path:
                return True
        
        # Check for restricted extensions
        for ext in self.RESTRICTED_EXTENSIONS:
            if path.endswith(ext):
                return True
                
        # Check for Stock directory access
        if path.startswith('Stock/'):
            return True
            
        return False
    
    def do_OPTIONS(self):
        # Log access
        client_ip = self.client_address[0]
        log_access(client_ip, self.path, 'OPTIONS')
        
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    # Helper function to get account from the appropriate tier folder
    def get_account(self, service, tier='free'):
        folder = 'Premium' if tier.lower() == 'premium' else 'Free'
        file_path = os.path.join(os.getcwd(), 'Stock', folder, f'{service}.txt')
        
        try:
            if not os.path.exists(file_path):
                return json.dumps({
                    'success': False,
                    'message': f'Service {service} not available'
                }).encode()
            
            # Read account file
            with open(file_path, 'r') as f:
                accounts = f.read().splitlines()
            
            # Filter out comments and empty lines
            accounts = [line for line in accounts if line and not line.startswith('#')]
            
            if not accounts:
                return json.dumps({
                    'success': False,
                    'message': f'No accounts available for {service}'
                }).encode()
            
            # Return a random account
            random_account = random.choice(accounts)
            return json.dumps({
                'success': True,
                'account': random_account
            }).encode()
        except Exception as e:
            print(f'Error getting {tier} account for {service}: {e}')
            return json.dumps({
                'success': False,
                'message': 'Failed to retrieve account'
            }).encode()
    
    def handle_keyauth_request(self, request_data):
        try:
            # Get request type and tier
            auth_type = request_data.get('type')
            tier = request_data.get('tier', 'premium')
            
            # Get the correct KeyAuth config based on tier
            config_key = tier.lower()
            if config_key not in KEYAUTH_CONFIG:
                return json.dumps({
                    'success': False,
                    'message': 'Invalid tier specified'
                }).encode()
            if not auth_type:
                raise ValueError('Missing request type')

            print(f"Processing KeyAuth request type: {auth_type}")
            print(f"Request data: {request_data}")

            # Build parameters using the appropriate tier config
            config = KEYAUTH_CONFIG[config_key]
            params = {
                'type': auth_type,
                'name': config['name'],
                'ownerid': config['ownerid'],
                'secret': config['secret']
            }

            # Add other parameters based on request type
            if auth_type == 'init':
                params['ver'] = request_data.get('version', '1.0')
            elif auth_type == 'login':
                params.update({
                    'username': request_data.get('username'),
                    'pass': request_data.get('password'),
                    'sessionid': request_data.get('sessionid')
                })
            elif auth_type == 'register':
                params.update({
                    'username': request_data.get('username'),
                    'pass': request_data.get('password'),
                    'key': request_data.get('key'),
                    'sessionid': request_data.get('sessionid')
                })
            elif auth_type == 'logout':
                params['sessionid'] = request_data.get('sessionid')
            else:
                raise ValueError(f'Invalid request type: {auth_type}')

            # Create KeyAuth API URL
            url = f'https://keyauth.win/api/1.2/?{urllib.parse.urlencode(params)}'
            print(f"Making request to KeyAuth: {url}")

            # Create a context that doesn't verify SSL certificates
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Make request to KeyAuth
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx) as response:
                response_data = response.read()
                print(f"KeyAuth response: {response_data}")
                return response_data

        except Exception as e:
            print(f"Error processing KeyAuth request: {e}")
            return json.dumps({
                'success': False,
                'message': str(e)
            }).encode()

    def do_GET(self):
        # Log the access attempt
        client_ip = self.client_address[0]
        log_access(client_ip, self.path, 'GET')
        print(f"Received GET request from {client_ip} for path: {self.path}")
        
        # Check if the path is restricted
        if self.is_restricted_path(self.path):
            print(f"BLOCKED: Attempted direct access to restricted path: {self.path} from IP: {client_ip}")
            self.send_response(403)  # Forbidden
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><head><title>403 Forbidden</title></head><body><h1>403 Forbidden</h1><p>Access denied.</p></body></html>')
            return
        
        # Handle services listing request
        if self.path.startswith('/api/services'):
            # Validate API access with token check if needed
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer ') and '/api/' in self.path:
                # Allow for development but log it
                print(f"Warning: API access without token from {client_ip}")
            
            self.handle_get_services()
            return
            
        # Handle favicon.ico request
        if self.path == '/favicon.ico':
            self.send_response(204)  # No content
            self.end_headers()
            return
            
    def handle_get_services(self):
        try:
            # Parse query parameters
            query_params = {}
            if '?' in self.path:
                query_string = self.path.split('?', 1)[1]
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value
            
            # Get tier parameter (default to free)
            tier = query_params.get('tier', 'free')
            folder = 'Premium' if tier.lower() == 'premium' else 'Free'
            folder_path = os.path.join(os.getcwd(), 'Stock', folder)
            
            # Get available services
            services = []
            if os.path.exists(folder_path):
                services = [file.replace('.txt', '') for file in os.listdir(folder_path) 
                            if file.endswith('.txt')]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'services': services
            }).encode())
            
        except Exception as e:
            print(f"Error listing services: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())

        # Serve static files
        try:
            return SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            print(f"Error serving static file: {e}")
            self.send_error(500, str(e))

    def do_POST(self):
        # Log the access attempt
        client_ip = self.client_address[0]
        log_access(client_ip, self.path, 'POST')
        print(f"Received POST request from {client_ip} for path: {self.path}")
        
        # Check if the path is restricted
        if self.is_restricted_path(self.path):
            print(f"BLOCKED: Attempted direct access to restricted path: {self.path} from IP: {client_ip}")
            self.send_response(403)  # Forbidden
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><head><title>403 Forbidden</title></head><body><h1>403 Forbidden</h1><p>Access denied.</p></body></html>')
            return
        
        # Validate API access with token if needed
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') and '/api/' in self.path:
            # For development, we'll allow it but log it
            print(f"Warning: API access without token from {client_ip}")
            
            # In production, you might want to require token authentication
            # self.send_response(401)  # Unauthorized
            # self.send_header('Content-type', 'application/json')
            # self.end_headers()
            # self.wfile.write(json.dumps({'success': False, 'error': 'Authentication required'}).encode())
            # return
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            json_data = json.loads(post_data)
        except json.JSONDecodeError:
            json_data = {}
            
        print(f"Received data: {json_data}")
        
        # Handle KeyAuth requests
        if self.path.startswith('/api/keyauth/'):
            self.handle_post_keyauth(json_data)
            return
            
        # Handle account generation request
        if self.path.startswith('/api/generate/'):
            service = self.path.split('/')[-1]
            tier = json_data.get('tier', 'free')
            self.handle_generate_account(service, tier)
            return
            
        # Handle any other unknown POST requests
        self.send_error(404)
        return
        
    def handle_post_generate(self):
        try:
            # Get the service name from the path
            service = self.path.split('/')[-1]
            
            # Read request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Get tier from request data (default to free)
            tier = request_data.get('tier', 'free')
            
            # Get an account for this service and tier
            response_data = self.get_account(service, tier)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(response_data)
            
        except Exception as e:
            print(f"Error processing account generation request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())
    
    def handle_post_keyauth(self):

        try:
            # Read and parse request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))

            # Process KeyAuth request
            response_data = self.handle_keyauth_request(request_data)

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(response_data)

        except Exception as e:
            print(f"Error processing POST request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'message': str(e)
            }).encode())

def run(server_class=HTTPServer, handler_class=KeyAuthHandler, port=3000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on http://localhost:{port}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Available stock files: {os.listdir(os.path.join(os.getcwd(), 'Stock'))}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
