const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const helmet = require('helmet');

// Security check - prevent direct access to this file through browser
if (process.env.NODE_ENV !== 'production' && process.env.BYPASS_SECURITY !== 'true') {
    const args = process.argv.slice(2);
    const validToken = crypto.createHash('sha256').update('snowygen_auth_token').digest('hex');
    
    if (args.length === 0 || args[0] !== validToken) {
        console.error('Unauthorized access attempt blocked');
        process.exit(1);
    }
}

// Log access attempts for security
function logAccess(ip, path, method) {
    try {
        const timestamp = new Date().toISOString();
        const logEntry = `${timestamp} - IP: ${ip} - ${method} ${path}\n`;
        fs.appendFileSync('access_log.txt', logEntry);
    } catch (error) {
        console.error(`Error logging access: ${error.message}`);
    }
}

const app = express();
const port = 3000;

// KeyAuth credentials - Updated for dual tier system
const KEYAUTH_CONFIG = {
    premium: {
        name: "SnowyMarkeyPrem",
        ownerid: "HgQcPwtKnr",
        secret: "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    },
    free: {
        name: "SnowyMarketFree",
        ownerid: "HgQcPwtKnr",
        secret: "a706db146e62b9179060d63d88c8e692fbaf7a4e6ae53c0bebca48b934dbf623"
    }
};

// List of restricted files and directories that should never be directly accessed
const RESTRICTED_FILES = [
    'server.py', 'server.js', '.htaccess', 'access_log.txt',
    'keyauth.json', '.git', '.env', 'config.json'
];

// List of restricted file extensions
const RESTRICTED_EXTENSIONS = ['.py', '.env', '.git', '.json', '.log', '.md', '.sh', '.bat'];

// Security token used for API access validation
const API_TOKEN = crypto.createHash('sha256').update('snowygen_secure_api_key').digest('hex');

// Apply security middleware
app.use(helmet()); // Adds various HTTP headers for security

// Setup basic CORS with restrictions
app.use(cors({
    origin: ['https://snowygen.online', 'http://localhost:3000', 'http://127.0.0.1:3000'],
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());

// Logging middleware
app.use((req, res, next) => {
    const ip = req.ip || req.connection.remoteAddress;
    logAccess(ip, req.path, req.method);
    next();
});

// Security middleware to block direct access to sensitive files
app.use((req, res, next) => {
    // Clean the path for security checks - avoid regex issues
    const path = req.path.startsWith('/') ? req.path.substring(1) : req.path;
    
    // Check for restricted files
    for (const restricted of RESTRICTED_FILES) {
        if (path === restricted || path.startsWith(restricted + '/') || path.includes('/' + restricted + '/')) {
            console.log(`BLOCKED: Access to restricted path: ${path} from IP: ${req.ip}`);
            return res.status(403).send('Access denied');
        }
    }
    
    // Check for restricted extensions
    for (const ext of RESTRICTED_EXTENSIONS) {
        if (path.endsWith(ext)) {
            console.log(`BLOCKED: Access to restricted extension: ${path} from IP: ${req.ip}`);
            return res.status(403).send('Access denied');
        }
    }
    
    // Check for Stock directory access
    if (path.startsWith('Stock/')) {
        console.log(`BLOCKED: Direct access to Stock directory: ${path} from IP: ${req.ip}`);
        return res.status(403).send('Access denied');
    }
    
    next();
});

// Serve static files - but only after security checks
app.use(express.static('.', {
    setHeaders: (res, path) => {
        // Add security headers to all static responses
        res.setHeader('X-Content-Type-Options', 'nosniff');
        res.setHeader('X-Frame-Options', 'SAMEORIGIN');
        res.setHeader('X-XSS-Protection', '1; mode=block');
    }
}));

// Rate limiting for API endpoints
const apiRequestCounts = {};
app.use('/api/', (req, res, next) => {
    const ip = req.ip || req.connection.remoteAddress;
    const now = Date.now();
    
    if (!apiRequestCounts[ip]) {
        apiRequestCounts[ip] = { count: 1, resetTime: now + 60000 }; // 1 minute window
    } else {
        if (now > apiRequestCounts[ip].resetTime) {
            // Reset counter if window expired
            apiRequestCounts[ip] = { count: 1, resetTime: now + 60000 };
        } else {
            // Increment counter
            apiRequestCounts[ip].count++;
            
            // Check if rate limit exceeded (e.g., 60 requests per minute)
            if (apiRequestCounts[ip].count > 60) {
                console.log(`Rate limit exceeded for IP: ${ip}`);
                return res.status(429).json({ success: false, error: 'Too many requests' });
            }
        }
    }
    
    next();
});

// API authentication middleware for secured endpoints
const authenticateApiRequest = (req, res, next) => {
    // Skip auth for development if flag is set
    if (process.env.NODE_ENV === 'development' && process.env.SKIP_API_AUTH === 'true') {
        return next();
    }
    
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        // For now, we'll allow requests without tokens but log them
        console.log(`Warning: API request without token from ${req.ip}`);
        return next();
        
        // In production, you might want to uncomment this:
        // return res.status(401).json({ success: false, error: 'Authentication required' });
    }
    
    const token = authHeader.split(' ')[1];
    if (token !== API_TOKEN) {
        console.log(`Invalid API token from ${req.ip}`);
        return res.status(403).json({ success: false, error: 'Invalid authentication token' });
    }
    
    next();
};

async function makeKeyAuthRequest(endpoint, params, tier = 'premium') {
    // Use the appropriate KeyAuth credentials based on tier
    const config = KEYAUTH_CONFIG[tier.toLowerCase()];
    if (!config) {
        return { success: false, message: 'Invalid tier specified' };
    }
    
    const url = `https://keyauth.win/api/1.2/?${new URLSearchParams(params)}`;
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`KeyAuth ${tier} request failed:`, error);
        return { success: false, message: 'Request failed' };
    }
}

// Helper function to get account from the appropriate tier folder
async function getAccount(service, tier = 'free') {
    const folder = tier.toLowerCase() === 'premium' ? 'Premium' : 'Free';
    const filePath = path.join(__dirname, 'Stock', folder, `${service}.txt`);
    
    try {
        if (!fs.existsSync(filePath)) {
            return { success: false, message: `Service ${service} not available` };
        }
        
        // Read account file
        const accounts = fs.readFileSync(filePath, 'utf8').split('\n')
            .filter(line => line && !line.startsWith('#'));
        
        if (accounts.length === 0) {
            return { success: false, message: `No accounts available for ${service}` };
        }
        
        // Return a random account
        const randomAccount = accounts[Math.floor(Math.random() * accounts.length)];
        return { success: true, account: randomAccount };
    } catch (error) {
        console.error(`Error getting ${tier} account for ${service}:`, error);
        return { success: false, message: 'Failed to retrieve account' };
    }
}

app.post('/api/keyauth/:type', async (req, res) => {
    const { type } = req.params;
    const { username, password, key, email, sessionid, version, tier = 'premium' } = req.body;

    // Get the correct KeyAuth config based on tier
    const configKey = tier.toLowerCase();
    const config = KEYAUTH_CONFIG[configKey];
    if (!config) {
        return res.status(400).json({ success: false, message: 'Invalid tier specified' });
    }

    let params = {
        type,
        name: config.name,
        ownerid: config.ownerid
    };

    switch (type) {
        case 'init':
            params.ver = version || '1.0';
            break;

        case 'login':
            params = {
                ...params,
                username,
                pass: password,
                sessionid
            };
            break;

        case 'register':
            params = {
                ...params,
                username,
                pass: password,
                key,
                email,
                sessionid
            };
            break;

        case 'logout':
            params.sessionid = sessionid;
            break;

        default:
            return res.status(400).json({ success: false, message: 'Invalid request type' });
    }

    try {
        const response = await makeKeyAuthRequest('', params, tier);
        res.json(response);
    } catch (error) {
        console.error(`${tier} Request failed:`, error);
        res.status(500).json({ success: false, message: 'Internal server error' });
    }
});

// Add a new endpoint for account generation that considers user tier
app.post('/api/generate/:service', async (req, res) => {
    const { service } = req.params;
    const { tier = 'free' } = req.body;
    
    try {
        // Validate user tier from session or JWT token (simplified for demo)
        // In a real app, you'd verify the user's tier through authentication
        
        // Get an account based on the user's tier
        const result = await getAccount(service, tier);
        
        if (!result.success) {
            return res.status(404).json({ success: false, message: result.message });
        }
        
        // Return the account
        res.json({ success: true, account: result.account });
    } catch (error) {
        console.error('Account generation failed:', error);
        res.status(500).json({ success: false, message: 'Failed to generate account' });
    }
});

// Add a new endpoint to list available services based on tier
app.get('/api/services', (req, res) => {
    const { tier = 'free' } = req.query;
    const folder = tier.toLowerCase() === 'premium' ? 'Premium' : 'Free';
    const folderPath = path.join(__dirname, 'Stock', folder);
    
    try {
        // Get available services
        const services = fs.readdirSync(folderPath)
            .filter(file => file.endsWith('.txt'))
            .map(file => file.replace('.txt', ''));
            
        res.json({ success: true, services });
    } catch (error) {
        console.error('Failed to list services:', error);
        res.status(500).json({ success: false, message: 'Failed to list available services' });
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
