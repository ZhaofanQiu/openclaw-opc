/**
 * Authentication module for OpenClaw OPC Dashboard
 * Handles API Key login, storage, and automatic header injection
 */

// Configuration
const AUTH_CONFIG = {
    STORAGE_KEY: 'opc_api_key',
    LOGIN_PATH: '/login',
    PUBLIC_PATHS: ['/login', '/health'],
};

/**
 * Get stored API Key from localStorage
 */
function getStoredApiKey() {
    return localStorage.getItem(AUTH_CONFIG.STORAGE_KEY);
}

/**
 * Store API Key to localStorage
 */
function storeApiKey(apiKey) {
    localStorage.setItem(AUTH_CONFIG.STORAGE_KEY, apiKey);
}

/**
 * Clear stored API Key (logout)
 */
function clearApiKey() {
    localStorage.removeItem(AUTH_CONFIG.STORAGE_KEY);
}

/**
 * Check if user is logged in
 */
function isLoggedIn() {
    return !!getStoredApiKey();
}

/**
 * Get API base URL
 */
function getApiBase() {
    return window.location.hostname === 'localhost' 
        ? 'http://localhost:8080'  // Development
        : '';  // Production (same origin via nginx proxy)
}

/**
 * Validate API Key with backend
 */
async function validateApiKey(apiKey) {
    try {
        // Use a simple endpoint that requires authentication but not admin
        const response = await fetch(`${getApiBase()}/api/agents?limit=1`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            }
        });
        return response.ok;
    } catch (error) {
        console.error('API Key validation error:', error);
        return false;
    }
}

/**
 * Perform login
 */
async function login(apiKey) {
    const isValid = await validateApiKey(apiKey);
    if (isValid) {
        storeApiKey(apiKey);
        return { success: true };
    }
    return { success: false, error: 'API Key 无效或已过期' };
}

/**
 * Perform logout
 */
function logout() {
    clearApiKey();
    window.location.href = AUTH_CONFIG.LOGIN_PATH;
}

/**
 * Check authentication and redirect if needed
 */
function checkAuth() {
    const currentPath = window.location.pathname;
    
    // Skip auth check for public paths
    if (AUTH_CONFIG.PUBLIC_PATHS.some(path => currentPath.endsWith(path))) {
        return true;
    }
    
    if (!isLoggedIn()) {
        showLoginModal();
        return false;
    }
    return true;
}

/**
 * Get fetch options with Authorization header
 */
function getAuthHeaders(additionalHeaders = {}) {
    const apiKey = getStoredApiKey();
    return {
        ...additionalHeaders,
        'Authorization': apiKey ? `Bearer ${apiKey}` : '',
        'Content-Type': 'application/json'
    };
}

/**
 * Authenticated fetch wrapper
 */
async function authFetch(url, options = {}) {
    const apiKey = getStoredApiKey();
    
    if (!apiKey) {
        showLoginModal();
        throw new Error('Not authenticated');
    }
    
    const authOptions = {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${apiKey}`
        }
    };
    
    const response = await fetch(url, authOptions);
    
    // Handle 401 Unauthorized - redirect to login
    if (response.status === 401) {
        clearApiKey();
        showLoginModal();
        throw new Error('Session expired. Please login again.');
    }
    
    return response;
}

/**
 * Show login modal
 */
function showLoginModal() {
    // Check if login overlay already exists
    if (document.getElementById('auth-login-overlay')) {
        return;
    }
    
    // Create login overlay
    const overlay = document.createElement('div');
    overlay.id = 'auth-login-overlay';
    overlay.innerHTML = `
        <div id="auth-login-container">
            <div id="auth-login-box">
                <h2>🔐 登录 Dashboard</h2>
                <p style="color: #888; margin-bottom: 20px;">请输入您的 API Key</p>
                <div id="auth-error" style="display: none;"></div>
                <div class="auth-input-group">
                    <input 
                        type="password" 
                        id="auth-api-key-input" 
                        placeholder="输入 API Key..." 
                        autocomplete="off"
                    />
                </div>
                <button id="auth-login-btn" onclick="handleLogin()">登录</button>
                <p style="color: #666; font-size: 12px; margin-top: 16px;">
                    提示：API Key 可以通过后端管理命令创建
                </p>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    
    // Add styles
    if (!document.getElementById('auth-styles')) {
        const styles = document.createElement('style');
        styles.id = 'auth-styles';
        styles.textContent = `
            #auth-login-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(15, 15, 26, 0.95);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #auth-login-container {
                width: 100%;
                max-width: 400px;
                padding: 20px;
            }
            #auth-login-box {
                background: #1a1a2e;
                border: 1px solid #2a2a4a;
                border-radius: 16px;
                padding: 32px;
                text-align: center;
            }
            #auth-login-box h2 {
                margin: 0 0 8px 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .auth-input-group {
                margin-bottom: 16px;
            }
            #auth-api-key-input {
                width: 100%;
                background: #252542;
                border: 1px solid #2a2a4a;
                color: #fff;
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 14px;
                font-family: monospace;
            }
            #auth-api-key-input:focus {
                outline: none;
                border-color: #667eea;
            }
            #auth-login-btn {
                width: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                color: #fff;
                padding: 12px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: opacity 0.2s;
            }
            #auth-login-btn:hover {
                opacity: 0.9;
            }
            #auth-login-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            #auth-error {
                background: rgba(248, 113, 113, 0.1);
                border: 1px solid rgba(248, 113, 113, 0.3);
                color: #f87171;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 16px;
                font-size: 14px;
            }
            #auth-logout-btn {
                background: #2a2a4a;
                border: none;
                color: #888;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }
            #auth-logout-btn:hover {
                background: #f87171;
                color: #fff;
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Focus on input
    setTimeout(() => {
        const input = document.getElementById('auth-api-key-input');
        if (input) input.focus();
    }, 100);
    
    // Add enter key handler
    const input = document.getElementById('auth-api-key-input');
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleLogin();
        }
    });
}

/**
 * Hide login modal
 */
function hideLoginModal() {
    const overlay = document.getElementById('auth-login-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * Show error message
 */
function showAuthError(message) {
    const errorDiv = document.getElementById('auth-error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

/**
 * Handle login button click
 */
async function handleLogin() {
    const input = document.getElementById('auth-api-key-input');
    const btn = document.getElementById('auth-login-btn');
    const apiKey = input.value.trim();
    
    if (!apiKey) {
        showAuthError('请输入 API Key');
        return;
    }
    
    btn.disabled = true;
    btn.textContent = '验证中...';
    
    const result = await login(apiKey);
    
    if (result.success) {
        hideLoginModal();
        // Reload page to initialize with auth
        window.location.reload();
    } else {
        showAuthError(result.error);
        btn.disabled = false;
        btn.textContent = '登录';
    }
}

/**
 * Add logout button to header
 */
function addLogoutButton(container) {
    // Check if button already exists
    if (document.getElementById('auth-logout-btn')) {
        return;
    }
    
    const btn = document.createElement('button');
    btn.id = 'auth-logout-btn';
    btn.textContent = '登出';
    btn.onclick = logout;
    
    container.appendChild(btn);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
});

// Export functions for use in other scripts
window.Auth = {
    isLoggedIn,
    login,
    logout,
    getApiKey: getStoredApiKey,
    getAuthHeaders,
    authFetch,
    checkAuth,
    showLoginModal,
    hideLoginModal,
    addLogoutButton
};
