class KeyAuth {
    constructor(name, ownerid, secret, version) {
        this.name = name;
        this.ownerid = ownerid;
        this.secret = secret;
        this.version = version;
        this.sessionid = null;
        this.baseUrl = 'https://keyauth.win/api/1.2/';
    }

    async init() {
        try {
            console.log('Initializing KeyAuth...');
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    type: 'init',
                    name: this.name,
                    ownerid: this.ownerid,
                    ver: this.version
                }).toString()
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Init response:', data);

            if (!data.success) {
                throw new Error(data.message || 'Failed to initialize');
            }

            this.sessionid = data.sessionid;
            return true;
        } catch (error) {
            console.error('KeyAuth initialization failed:', error);
            return false;
        }
    }

    async login(username, password) {
        try {
            if (!this.sessionid) {
                throw new Error('Not initialized. Call init() first.');
            }

            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    type: 'login',
                    username,
                    pass: password,
                    name: this.name,
                    ownerid: this.ownerid,
                    sessionid: this.sessionid
                }).toString()
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Login response:', data);
            
            // If login was successful, send webhook
            if (data.success) {
                try {
                    // Get HWID from KeyAuth response or generate a temporary one
                    const hwid = data.info?.hwid || this.generateTemporaryHWID();
                    
                    // Determine user tier from the app name
                    const tier = this.name.toLowerCase().includes('prem') ? 'premium' : 'free';
                    
                    // Send auth webhook
                    await fetch('/api/auth/webhook', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            event_type: 'login',
                            username: username,
                            tier: tier,
                            hwid: hwid,
                            subscription: data.info?.subscription || 'Unknown',
                            expiry: data.info?.expiry || 'Unknown'
                        })
                    });
                } catch (webhookError) {
                    console.error('Failed to send login webhook:', webhookError);
                    // Non-blocking error - continue even if webhook fails
                }
            }
            
            return data;
        } catch (error) {
            console.error('Login failed:', error);
            return { success: false, message: error.message };
        }
    }

    // Generate a temporary HWID based on browser and device info
    generateTemporaryHWID() {
        try {
            // Collect browser information
            const navigatorInfo = [
                navigator.userAgent,
                navigator.language,
                navigator.platform,
                navigator.vendor,
                screen.width,
                screen.height,
                screen.colorDepth
            ].join('-');
            
            // Create a simple hash of the collected info
            let hash = 0;
            for (let i = 0; i < navigatorInfo.length; i++) {
                const char = navigatorInfo.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash; // Convert to 32bit integer
            }
            
            // Return a hex string representation prefixed with 'HW-'
            return 'HW-' + Math.abs(hash).toString(16).padStart(8, '0');
        } catch (e) {
            // Fallback to random ID if anything fails
            return 'HW-' + Math.random().toString(36).substring(2, 10);
        }
    }
    
    async register(username, password, key) {
        try {
            if (!this.sessionid) {
                throw new Error('Not initialized. Call init() first.');
            }

            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    type: 'register',
                    username,
                    pass: password,
                    key,
                    name: this.name,
                    ownerid: this.ownerid,
                    sessionid: this.sessionid
                }).toString()
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Registration response:', data);
            
            // If registration was successful, send webhook
            if (data.success) {
                try {
                    // Get HWID from KeyAuth response or generate a temporary one
                    const hwid = data.info?.hwid || this.generateTemporaryHWID();
                    
                    // Determine user tier from the app name
                    const tier = this.name.toLowerCase().includes('prem') ? 'premium' : 'free';
                    
                    // Send auth webhook
                    await fetch('/api/auth/webhook', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            event_type: 'register',
                            username: username,
                            tier: tier,
                            hwid: hwid,
                            key_used: key,
                            subscription: data.info?.subscription || 'Unknown',
                            expiry: data.info?.expiry || 'Unknown'
                        })
                    });
                } catch (webhookError) {
                    console.error('Failed to send registration webhook:', webhookError);
                    // Non-blocking error - continue even if webhook fails
                }
            }
            
            return data;
        } catch (error) {
            console.error('Registration failed:', error);
            return { success: false, message: error.message };
        }
    }

    async logout() {
        try {
            if (!this.sessionid) {
                throw new Error('Not initialized or already logged out');
            }
            
            // Get username from localStorage if available
            const username = localStorage.getItem('username') || 'unknown';
            const tier = localStorage.getItem('userTier') || (this.name.toLowerCase().includes('prem') ? 'premium' : 'free');
            const hwid = this.generateTemporaryHWID();
            
            // Send logout webhook before clearing session
            try {
                await fetch('/api/auth/webhook', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        event_type: 'logout',
                        username: username,
                        tier: tier,
                        hwid: hwid
                    })
                });
            } catch (webhookError) {
                console.error('Failed to send logout webhook:', webhookError);
                // Continue with logout even if webhook fails
            }

            // Clear sessionid
            this.sessionid = null;
            
            // No need to call KeyAuth API for logout as it's done client-side
            return { success: true, message: 'Logged out successfully' };
        } catch (error) {
            console.error('Logout failed:', error);
            return { success: false, message: error.message };
        }
    }
}