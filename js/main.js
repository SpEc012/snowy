// Service configuration
const services = {
    roblox: { name: 'Roblox', icon: 'gamepad' },
    epic: { name: 'Epic Games', icon: 'gamepad' },
    riot: { name: 'Riot', icon: 'gamepad' },
    eldorado: { name: 'Eldorado', icon: 'store' },
    ubisoft: { name: 'Ubisoft', icon: 'gamepad' },
    netflix: { name: 'Netflix', icon: 'film' },
    tiktok: { name: 'TikTok', icon: 'video' },
    disney: { name: 'Disney+', icon: 'play' }
};

// Achievement definitions
const achievements = {
    first_gen: { 
        id: 'first_gen',
        title: 'First Steps',
        description: 'Generate your first account',
        icon: 'star'
    },
    collector_10: {
        id: 'collector_10',
        title: 'Collector',
        description: 'Generate 10 accounts',
        icon: 'trophy'
    },
    variety_master: {
        id: 'variety_master',
        title: 'Variety Master',
        description: 'Generate accounts from 5 different services',
        icon: 'crown'
    }
};

// Theme definitions
const themes = {
    default: {
        name: 'Default',
        gradient: 'linear-gradient(135deg, #9b4dff 0%, #4da6ff 100%)'
    },
    sunset: {
        name: 'Sunset',
        gradient: 'linear-gradient(135deg, #ff4d4d 0%, #ff9b4d 100%)'
    },
    forest: {
        name: 'Forest',
        gradient: 'linear-gradient(135deg, #4dff4d 0%, #4dff9b 100%)'
    },
    ocean: {
        name: 'Ocean',
        gradient: 'linear-gradient(135deg, #4d4dff 0%, #4dffff 100%)'
    }
};

// User stats and preferences
let userStats = JSON.parse(localStorage.getItem('userStats')) || {
    totalGenerated: 0,
    serviceStats: {},
    achievements: [],
    theme: 'default',
    avatar: null
};

// DOM Elements
const modal = document.getElementById('generatorModal');
const closeBtn = document.querySelector('.close-btn');
const accountDetails = document.getElementById('accountDetails');
const generateBtn = document.getElementById('generateBtn');
const serviceSelect = document.getElementById('serviceSelect');
const historyContent = document.getElementById('historyContent');
const historySearch = document.getElementById('historySearch');
const serviceFilter = document.getElementById('serviceFilter');
const statsContainer = document.getElementById('statsContainer');
const stockStatus = document.getElementById('stockStatus');

// Load services and stock status on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize based on user tier
    const userTier = localStorage.getItem('snowyMarketTier') || 'free';
    console.log(`Initializing for ${userTier} tier user`);
    
    // Update the cooldown time display based on tier
    const cooldownDisplay = document.querySelector('.cooldown-time');
    if (cooldownDisplay) {
        cooldownDisplay.textContent = userTier === 'premium' ? '15' : '45';
    }
    
    // Load available services for this tier
    loadAvailableServices();
    
    // Update stock status
    updateStockStatus();
    
    // Other initializations...
    // Load account history if we're on the history page
    if (document.getElementById('historyList')) {
        loadAccountHistory();
    }
    updateStatsDisplay();
    
    // Start cooldown timer if on the generator page
    if (document.getElementById('generateBtn')) {
        startCooldownTimer();
    }
});

// Initialize stats display
function updateStatsDisplay() {
    if (!statsContainer) return;
    
    statsContainer.innerHTML = `
        <div class="stats-card">
            <i class="fas fa-chart-bar"></i>
            <h3>Total Generated</h3>
            <p>${userStats.totalGenerated}</p>
        </div>
        ${Object.entries(userStats.serviceStats).map(([service, count]) => `
            <div class="stats-card">
                <i class="fas fa-${services[service]?.icon || 'star'}"></i>
                <h3>${services[service]?.name || service}</h3>
                <p>${count} generated</p>
            </div>
        `).join('')}
    `;
}

// Achievement system
function checkAchievements() {
    const newAchievements = [];
    
    // Check First Steps
    if (userStats.totalGenerated === 1 && !userStats.achievements.includes('first_gen')) {
        newAchievements.push(achievements.first_gen);
    }
    
    // Check Collector
    if (userStats.totalGenerated >= 10 && !userStats.achievements.includes('collector_10')) {
        newAchievements.push(achievements.collector_10);
    }
    
    // Check Variety Master
    const uniqueServices = Object.keys(userStats.serviceStats).length;
    if (uniqueServices >= 5 && !userStats.achievements.includes('variety_master')) {
        newAchievements.push(achievements.variety_master);
    }
    
    // Award new achievements
    newAchievements.forEach(achievement => {
        userStats.achievements.push(achievement.id);
        showAchievementNotification(achievement);
    });
    
    localStorage.setItem('userStats', JSON.stringify(userStats));
}

// Show achievement notification
function showAchievementNotification(achievement) {
    const notification = document.createElement('div');
    notification.className = 'achievement-notification';
    notification.innerHTML = `
        <i class="fas fa-${achievement.icon}"></i>
        <div class="achievement-text">
            <h4>${achievement.title}</h4>
            <p>${achievement.description}</p>
        </div>
    `;
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Remove after animation
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// Apply theme
function applyTheme(themeName) {
    const theme = themes[themeName] || themes.default;
    document.documentElement.style.setProperty('--theme-gradient', theme.gradient);
    userStats.theme = themeName;
    localStorage.setItem('userStats', JSON.stringify(userStats));
}

// Load available services based on user tier
async function loadAvailableServices() {
    const serviceSelect = document.getElementById('serviceSelect');
    if (!serviceSelect) return;
    
    try {
        // Determine user tier
        const userTier = localStorage.getItem('snowyMarketTier') || 'free';
        
        // Clear existing options except the first placeholder
        while (serviceSelect.options.length > 1) {
            serviceSelect.remove(1);
        }
        
        // Add loading option
        const loadingOption = document.createElement('option');
        loadingOption.text = 'Loading services...';
        loadingOption.disabled = true;
        serviceSelect.add(loadingOption);
        serviceSelect.selectedIndex = 1;
        
        // Fetch available services from our API server
        const response = await fetch(`https://gen-u8pm.onrender.com/api/stock/status?tier=${userTier}`, {
            method: 'GET',
            headers: {
                'X-API-Key': 'rvn_sec',
                'Accept': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        });
        
        if (!response.ok) throw new Error('Failed to load services');
        
        const data = await response.json();
        
        // Remove loading option
        serviceSelect.remove(1);
        
        // Process the services from the stock status data
        if (data.success && data.status) {
            // Get all services with stock count > 0
            const availableServices = Object.keys(data.status).filter(service => 
                data.status[service] > 0
            );
            
            if (availableServices.length > 0) {
                // Add options for each available service
                availableServices.forEach(service => {
                    const option = document.createElement('option');
                    option.value = service.toLowerCase();
                    option.text = services[service.toLowerCase()]?.name || service;
                    serviceSelect.add(option);
                });
            } else {
                // Add a no services option if no services are available
                const noServicesOption = document.createElement('option');
                noServicesOption.text = 'No services with stock available';
                noServicesOption.disabled = true;
                serviceSelect.add(noServicesOption);
            }
        } else {
            // Add a no services option if none available
            const noServicesOption = document.createElement('option');
            noServicesOption.text = 'No services available';
            noServicesOption.disabled = true;
            serviceSelect.add(noServicesOption);
        }
    } catch (error) {
        console.error('Failed to load services:', error);
        // Add error option
        const errorOption = document.createElement('option');
        errorOption.text = 'Error loading services';
        errorOption.disabled = true;
        serviceSelect.add(errorOption);
    }
}

// Update stock status
async function updateStockStatus() {
    const stockStatusElement = document.getElementById('stockStatus');
    if (!stockStatusElement) return;
    
    try {
        // Show loading state
        stockStatusElement.innerHTML = '<div class="stock-loading">Loading stock...</div>';
        
        // Determine if user is premium or free
        const userTier = localStorage.getItem('snowyMarketTier') || 'free';
        const isPremium = userTier === 'premium';
        
        // Load available services based on tier
        loadAvailableServices();
        
        // Fetch the stock status from our API
        const response = await fetch(`https://gen-u8pm.onrender.com/api/stock/status?tier=${userTier}`, {
            method: 'GET',
            headers: {
                'X-API-Key': 'rvn_sec',
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch stock status');
        }
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.message || 'Failed to get stock data');
        }
        
        // Process the stock data
        const stockData = {};
        const statusData = data.status || {};
        
        // Convert API response to our format
        Object.keys(statusData).forEach(service => {
            stockData[service] = {
                count: statusData[service],
                status: statusData[service] > 0 ? 'in-stock' : 'out-of-stock'
            };
        });
        
        // Clear loading state
        stockStatusElement.innerHTML = '';
        
        // Sort services by count (highest first)
        const sortedServices = Object.keys(stockData).sort((a, b) => 
            stockData[b].count - stockData[a].count
        );
        
        // Create HTML for each stock item
        sortedServices.forEach(service => {
            const { count, status } = stockData[service];
            const serviceKey = service.toLowerCase();
            const serviceName = services[serviceKey]?.name || service;
            const icon = services[serviceKey]?.icon || 'gamepad';
            
            const stockItem = document.createElement('div');
            stockItem.className = `stock-item ${status}`;
            stockItem.dataset.service = serviceKey;
            stockItem.innerHTML = `
                <div class="stock-item-name">
                    <i class="fas fa-${icon}"></i> ${serviceName}
                </div>
                <div class="stock-item-count">${count}</div>
            `;
            
            // Add click event to select this service
            stockItem.addEventListener('click', () => {
                const serviceSelect = document.getElementById('serviceSelect');
                if (serviceSelect) {
                    // Find the option with the matching value (case insensitive)
                    const options = Array.from(serviceSelect.options);
                    const option = options.find(opt => opt.value.toLowerCase() === serviceKey.toLowerCase());
                    
                    if (option) {
                        serviceSelect.value = option.value;
                        // Trigger change event
                        const event = new Event('change');
                        serviceSelect.dispatchEvent(event);
                    }
                }
            });
            
            stockStatusElement.appendChild(stockItem);
        });
        
        // No tooltip - removed as requested
        
        console.log('Stock updated successfully');
    } catch (error) {
        console.error('Failed to update stock status:', error);
        stockStatusElement.innerHTML = '<div class="stock-error">Failed to load stock status</div>';
    }
}

// Start cooldown timer
let cooldownInterval;
function startCooldownTimer() {
    const generateBtn = document.getElementById('generateBtn');
    if (!generateBtn) return;
    
    // Clear any existing interval
    if (cooldownInterval) clearInterval(cooldownInterval);
    
    // Determine user tier and set cooldown time accordingly
    const userTier = localStorage.getItem('snowyMarketTier') || 'free';
    const isPremium = userTier === 'premium';
    const cooldownTime = isPremium ? 15000 : 45000; // 15 seconds for premium, 45 for free
    
    // Get the generation time (or 0 if none)
    const lastGenerateTime = parseInt(localStorage.getItem('lastGenerateTime')) || 0;
    
    // If there's no last generation time or it's over a day old, enable the button immediately
    if (lastGenerateTime === 0 || (Date.now() - lastGenerateTime > 86400000)) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-bolt"></i> Generate Account';
        return; // Exit early - no need for a timer
    }
    
    // Check if we're still in cooldown
    const currentTime = Date.now();
    const timeElapsed = currentTime - lastGenerateTime;
    
    if (timeElapsed >= cooldownTime) {
        // Cooldown already complete
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-bolt"></i> Generate Account';
        return; // Exit early - no need for a timer
    }
    
    // Still in cooldown - start the countdown
    const updateButton = () => {
        const now = Date.now();
        const elapsed = now - lastGenerateTime;
        
        if (elapsed >= cooldownTime) {
            // Cooldown complete
            clearInterval(cooldownInterval);
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-bolt"></i> Generate Account';
        } else {
            // Still in cooldown
            const remainingTime = Math.ceil((cooldownTime - elapsed) / 1000);
            generateBtn.disabled = true;
            generateBtn.innerHTML = `<i class="fas fa-hourglass-half"></i> Wait ${remainingTime}s`;
        }
    };
    
    // Update immediately, then set interval
    updateButton();
    cooldownInterval = setInterval(updateButton, 1000);
}

// Generate account with updated functionality
async function generateAccount() {
    // COOLDOWN SYSTEM COMPLETELY DISABLED
    // Determine user tier for API calls
    const userTier = localStorage.getItem('snowyMarketTier') || 'free';
    const isPremium = userTier === 'premium';
    
    // Reset any cooldown state and enable the button
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-bolt"></i> Generate Account';
    }

    const service = document.getElementById('serviceSelect').value;
    if (!service) {
        RavenAnimations.notification('Please select a service', 'error');
        return;
    }
    
    // Show modal with loader
    modal.style.display = 'flex';
    RavenAnimations.modal.open();
    
    // Start generation animation
    const genAnimation = RavenAnimations.account.generating();
    
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    
    try {
        // Use our API server endpoint with tier-specific account generation
        const response = await fetch(`https://gen-u8pm.onrender.com/api/stock/${service.toLowerCase()}?tier=${userTier}`, {
            method: 'GET',
            headers: {
                'X-API-Key': 'rvn_sec',
                'Accept': 'application/json',
                'X-Username': localStorage.getItem('username') || 'unknown',
                'X-HWID': localStorage.getItem('hwid') || 'unknown'
            }
        });
        if (!response.ok) throw new Error('Failed to generate account');
        
        let data;
        const contentType = response.headers.get('content-type');
        let accountValue = '';
        let email = 'Unknown';
        let password = 'Unknown';
        
        if (contentType && contentType.includes('application/json')) {
            // Handle JSON response
            data = await response.json();
            
            if (!data.success) throw new Error(data.message || 'Failed to generate account');
            
            // Extract account details
            if (data.account) {
                if (typeof data.account === 'string') {
                    // Handle string format (likely email:password)
                    accountValue = data.account;
                    
                    // Try to extract email and password for saving
                    const parts = data.account.split(':');
                    if (parts.length === 2) {
                        email = parts[0];
                        password = parts[1];
                    }
                } else if (typeof data.account === 'object') {
                    // Handle object format with email and password properties
                    email = data.account.email || 'Unknown';
                    password = data.account.password || 'Unknown';
                    accountValue = `${email}:${password}`;
                }
            } else if (data.email && data.password) {
                // Handle separate email and password properties
                email = data.email;
                password = data.password;
                accountValue = `${email}:${password}`;
            }
        } else {
            // Handle plain text response
            const text = await response.text();
            
            try {
                // Try to parse as JSON first in case content-type is wrong
                data = JSON.parse(text);
                
                // Extract account details (same logic as above)
                if (data.account) {
                    if (typeof data.account === 'string') {
                        accountValue = data.account;
                        
                        const parts = data.account.split(':');
                        if (parts.length === 2) {
                            email = parts[0];
                            password = parts[1];
                        }
                    } else if (typeof data.account === 'object') {
                        email = data.account.email || 'Unknown';
                        password = data.account.password || 'Unknown';
                        accountValue = `${email}:${password}`;
                    }
                } else if (data.email && data.password) {
                    email = data.email;
                    password = data.password;
                    accountValue = `${email}:${password}`;
                }
            } catch (e) {
                // If not JSON, assume it's a plain text account in email:password format
                accountValue = text;
                
                // Try to extract email and password
                const parts = text.split(':');
                if (parts.length === 2) {
                    email = parts[0];
                    password = parts[1];
                }
            }
        }
        
        // Save to history
        const history = JSON.parse(localStorage.getItem('accountHistory') || '[]');
        history.unshift({
            service: service,
            email: email,
            password: password,
            account_string: accountValue,
            time: Date.now(),
            tier: userTier
        });
        localStorage.setItem('accountHistory', JSON.stringify(history.slice(0, 100)));
        
        // Add missing stats functions
        // Update user statistics for the generated account
        if (!userStats.serviceStats[service]) {
            userStats.serviceStats[service] = 0;
        }
        userStats.serviceStats[service]++;
        userStats.totalGenerated++;
        localStorage.setItem('userStats', JSON.stringify(userStats));

        // Check for achievements
        checkAchievements();
        
        // Set account details in the input field
        const accountDetails = document.getElementById('accountDetails');
        if (accountDetails) {
            accountDetails.value = accountValue;
        }
        
        // Update service icon in modal
        const serviceIconLarge = document.getElementById('serviceIconLarge');
        if (serviceIconLarge) {
            serviceIconLarge.className = `fas fa-${services[service]?.icon || 'gamepad'}`;
        }
        
        // Show account info with animation after a short delay
        setTimeout(() => {
            const accountInfo = document.querySelector('.account-info');
            if (accountInfo) {
                // Make sure it's visible before animation
                accountInfo.style.display = 'block';
                accountInfo.style.opacity = '1';
            }
            
            // Hide loader
            const loader = document.querySelector('.loader');
            if (loader) {
                loader.style.display = 'none';
            }
            
            // Run animation
            RavenAnimations.account.display();
        }, 500);
        
        // Update user stats
        userStats.totalGenerated++;
        userStats.serviceStats[service] = (userStats.serviceStats[service] || 0) + 1;
        localStorage.setItem('userStats', JSON.stringify(userStats));
        
        // Check achievements
        checkAchievements();
        
        // Show success notification
        RavenAnimations.notification(`${services[service].name} account generated successfully!`, 'success');
        
        // Update last generate time
        localStorage.setItem('lastGenerateTime', Date.now());
        
        // Update stats display
        updateStatsDisplay();
        
        // Update stock status
        updateStockStatus();
        
    } catch (error) {
        console.error('Generation failed:', error);
        RavenAnimations.modal.close();
        RavenAnimations.notification('Failed to generate account. Please try again later.', 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-bolt"></i> Generate';
    }
}

// Save to history
function saveToHistory(service, email, password) {
    let accountHistory = JSON.parse(localStorage.getItem('accountHistory')) || [];
    
    // Get service name safely
    let serviceName = 'Unknown';
    if (service && services[service] && services[service].name) {
        serviceName = services[service].name;
    } else if (service === 'disney') {
        serviceName = 'Disney+';
    } else if (service) {
        // Capitalize first letter as fallback
        serviceName = service.charAt(0).toUpperCase() + service.slice(1);
    }
    
    accountHistory.unshift({
        service: serviceName,
        email: email,
        password: password,
        time: new Date().toISOString()
    });

    // Keep only last 10 accounts
    if (accountHistory.length > 10) {
        accountHistory = accountHistory.slice(0, 10);
    }

    // Save to localStorage
    localStorage.setItem('accountHistory', JSON.stringify(accountHistory));
    
    // Update the history display
    loadAccountHistory();
}

// Load account history
function loadAccountHistory() {
    const historyContent = document.getElementById('historyContent');
    if (!historyContent) return;
    
    // Clear any existing content
    historyContent.innerHTML = '';
    
    // Get account history from localStorage
    let accountHistory = JSON.parse(localStorage.getItem('accountHistory')) || [];
    
    // Add View Full History button at the top
    const viewAllButtonTop = document.createElement('div');
    viewAllButtonTop.className = 'view-all-history-top';
    viewAllButtonTop.innerHTML = '<a href="history.html" class="view-all-btn-top"><i class="fas fa-history"></i> View Full History</a>';
    historyContent.appendChild(viewAllButtonTop);
    
    // Limit to 5 most recent items
    const historyToDisplay = accountHistory.slice(0, 5);
    
    if (historyToDisplay.length === 0) {
        historyContent.innerHTML = '<div class="view-all-history-top"><a href="history.html" class="view-all-btn-top"><i class="fas fa-history"></i> View Full History</a></div><p class="no-history">No accounts generated yet</p>';
        return;
    }
    
    // Create and append each history item
    historyToDisplay.forEach(account => {
        // Create the history item container
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        // Get the service icon
        const serviceKey = account.service?.toLowerCase();
        const serviceIcon = services[serviceKey]?.icon || 'star';
        
        // Build the item HTML
        historyItem.innerHTML = `
            <div class="history-icon">
                <i class="fas fa-${serviceIcon}"></i>
            </div>
            <div class="history-details">
                <div class="service-name">${account.service || 'Unknown'}</div>
                <div class="account-text">${account.email || ''}:${account.password || ''}</div>
                <div class="account-type">${account.service || 'Unknown'} Account</div>
            </div>
            <div class="history-actions">
                <button class="copy-history-btn" onclick="copyHistoryItem(this, '${account.email || ''}:${account.password || ''}')">
                    <i class="fas fa-copy"></i>
                </button>
            </div>
        `;
        
        // Add the item to the history content
        historyContent.appendChild(historyItem);
    });
    
    // Add a view full history button
    const viewAllButton = document.createElement('div');
    viewAllButton.className = 'view-all-history';
    viewAllButton.innerHTML = '<a href="history.html" class="view-all-btn"><i class="fas fa-external-link-alt"></i> View Full History</a>';
    historyContent.appendChild(viewAllButton);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize GSAP animations
    if (window.RavenAnimations && typeof window.RavenAnimations.init === 'function') {
        window.RavenAnimations.init();
    }
    // Apply saved theme
    applyTheme(userStats.theme);
    
    // Initialize displays
    updateStatsDisplay();
    updateStockStatus();
    
    // Load account history
    loadAccountHistory();
    
    // Set up event listeners
    if (generateBtn) {
        generateBtn.addEventListener('click', generateAccount);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            RavenAnimations.modal.close();
        });
    }

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            RavenAnimations.modal.close();
        }
    });

    // Update stock status periodically
    setInterval(updateStockStatus, 30000); // Every 30 seconds
});

// Filter history based on search and service
function filterHistory() {
    const searchTerm = historySearch ? historySearch.value.toLowerCase() : '';
    const serviceFilter = document.getElementById('serviceFilter');
    const selectedService = serviceFilter ? serviceFilter.value : '';
    
    // Get history from localStorage
    const history = JSON.parse(localStorage.getItem('accountHistory')) || [];
    
    // Filter history
    const filteredHistory = history.filter(item => {
        const matchesSearch = 
            item.email.toLowerCase().includes(searchTerm) || 
            item.password.toLowerCase().includes(searchTerm);
        
        const matchesService = 
            !selectedService || 
            item.service.toLowerCase() === selectedService.toLowerCase();
        
        return matchesSearch && matchesService;
    });
    
    // Update history display
    if (historyContent) {
        if (filteredHistory.length === 0) {
            historyContent.innerHTML = '<p class="no-history">No matching accounts found</p>';
            return;
        }
        
        historyContent.innerHTML = filteredHistory.map(item => `
            <div class="history-item">
                <div class="history-icon">
                    <i class="fas fa-${services[item.service.toLowerCase()]?.icon || 'star'}"></i>
                </div>
                <div class="history-details">
                    <div class="service-name">${item.service}</div>
                    <div class="account-text">${item.email}:${item.password}</div>
                </div>
                <div class="history-actions">
                    <button class="copy-history-btn" onclick="copyHistoryItem(this, '${item.email}:${item.password}')">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
        // Animate history items
        if (window.RavenAnimations && typeof window.RavenAnimations.historyItems === 'function') {
            window.RavenAnimations.historyItems();
        }
    }
}

// Copy account details to clipboard
function copyToClipboard() {
    accountDetails.select();
    document.execCommand('copy');
    
    const copyBtn = document.querySelector('.copy-btn');
    const originalText = copyBtn.innerHTML;
    
    // Animate copy button
    RavenAnimations.copyButton(copyBtn);
    
    copyBtn.innerHTML = '<i class="fas fa-check"></i>';
    setTimeout(() => {
        copyBtn.innerHTML = originalText;
    }, 2000);
    
    // Show notification
    RavenAnimations.notification('Account details copied to clipboard!', 'success');
}

// Copy history item to clipboard
function copyHistoryItem(element, account) {
    navigator.clipboard.writeText(account).then(() => {
        const icon = element.querySelector('i');
        icon.className = 'fas fa-check';
        setTimeout(() => {
            icon.className = 'fas fa-copy';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}
historySearch.addEventListener('input', filterHistory);
serviceFilter.addEventListener('change', filterHistory);
