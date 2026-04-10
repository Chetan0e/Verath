const API_BASE = "http://localhost:8000";
let AUTH_TOKEN = localStorage.getItem('secondbrain_token');

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (!AUTH_TOKEN) {
        showLoginModal();
    } else {
        initDashboard();
    }
});

function initDashboard() {
    loadStats();
    loadSummary();
    loadTimeline();
    setInterval(loadStats, 30000);
}

// Helper for authenticated fetches
async function authFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    
    const res = await fetch(url, options);
    if (res.status === 401) {
        localStorage.removeItem('secondbrain_token');
        location.reload();
    }
    return res;
}

// Load and display statistics
async function loadStats() {
    try {
        // Get timeline to calculate stats
        const timelineRes = await authFetch(`${API_BASE}/timeline`);
        const timelineData = await timelineRes.json();
        
        // Get all memories for speaker count
        const queryRes = await authFetch(`${API_BASE}/query?q=*&limit=1000`);
        const queryData = await queryRes.json();
        
        // Calculate stats
        const totalMemories = timelineData.timeline ? timelineData.timeline.length : 0;
        const speakers = new Set();
        let importantCount = 0;
        let todayCount = 0;
        
        if (timelineData.timeline) {
            const today = new Date().toDateString();
            timelineData.timeline.forEach(item => {
                if (item.speaker) speakers.add(item.speaker);
                if (item.importance >= 0.6) importantCount++;
                if (new Date(item.timestamp * 1000).toDateString() === today) {
                    todayCount++;
                }
            });
        }
        
        // Update UI
        document.getElementById('total-memories').textContent = totalMemories;
        document.getElementById('total-speakers').textContent = speakers.size;
        document.getElementById('important-memories').textContent = importantCount;
        document.getElementById('today-memories').textContent = todayCount;
        
        // Update status
        updateStatus(true);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        updateStatus(false);
    }
}

// Update connection status
function updateStatus(connected) {
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');
    
    if (connected) {
        indicator.classList.add('active');
        text.textContent = 'Live System Connected';
        text.style.color = '#10b981';
    } else {
        indicator.classList.remove('active');
        text.textContent = 'Connection Interrupted';
        text.style.color = '#ef4444';
    }
}

// Load daily summary
async function loadSummary() {
    const summaryContent = document.getElementById('summary-content');
    const btn = document.getElementById('btn-refresh-summary');
    
    try {
        if (btn) btn.disabled = true;
        summaryContent.style.opacity = '0.5';
        
        const res = await authFetch(`${API_BASE}/summary`);
        const data = await res.json();
        
        summaryContent.style.opacity = '1';
        if (data.summary) {
            summaryContent.innerHTML = `<p>${data.summary}</p>`;
        } else {
            summaryContent.innerHTML = '<p class="placeholder-text">No summary available for today.</p>';
        }
    } catch (error) {
        console.error('Error loading summary:', error);
        summaryContent.innerHTML = '<p class="error-text">Error synthesizing data stream.</p>';
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Load timeline
async function loadTimeline() {
    const timelineContent = document.getElementById('timeline-content');
    try {
        const res = await authFetch(`${API_BASE}/timeline`);
        const data = await res.json();
        
        if (data.timeline && data.timeline.length > 0) {
            const timelineHTML = data.timeline.map(item => `
                <div class="timeline-item">
                    <div class="timeline-time">${item.time || 'NOW'}</div>
                    <div class="timeline-text">${item.text || '...'}</div>
                    <div class="timeline-speaker">
                        <i class="fas fa-user-circle"></i> ${item.speaker || 'Unknown Entity'}
                    </div>
                </div>
            `).join('');
            timelineContent.innerHTML = timelineHTML;
        } else {
            timelineContent.innerHTML = '<p class="placeholder-text">Historical timeline is currently empty.</p>';
        }
    } catch (error) {
        console.error('Error loading timeline:', error);
        timelineContent.innerHTML = '<p class="error-text">Failed to fetch historical stream.</p>';
    }
}

// Load insights
async function loadInsights() {
    const insightsContent = document.getElementById('insights-content');
    try {
        const res = await authFetch(`${API_BASE}/insights`);
        const data = await res.json();
        
        if (data.insights && data.insights.length > 0) {
            const insightsHTML = `
                <ul class="insights-list">
                    ${data.insights.map(insight => `
                        <li>
                            <i class="fas fa-microchip" style="margin-right: 10px; color: var(--primary);"></i>
                            ${insight}
                        </li>
                    `).join('')}
                </ul>
            `;
            insightsContent.innerHTML = insightsHTML;
        } else {
            insightsContent.innerHTML = '<p class="placeholder-text">Analyze patterns to uncover connections.</p>';
        }
    } catch (error) {
        console.error('Error loading insights:', error);
        insightsContent.innerHTML = '<p class="error-text">Pattern analysis failed.</p>';
    }
}

// Ask query
async function askQuery() {
    const queryInput = document.getElementById('query-input');
    const queryResult = document.getElementById('query-result');
    const btn = document.getElementById('btn-ask');
    const query = queryInput.value.trim();
    
    if (!query) return;
    
    queryResult.style.display = 'block';
    queryResult.innerHTML = '<div class="loading-dots">Analyzing neural pathways...<span>.</span><span>.</span><span>.</span></div>';
    btn.disabled = true;
    
    try {
        const res = await authFetch(`${API_BASE}/query?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        
        if (data.answer) {
            let resultHTML = `<div style="margin-bottom: 12px; border-left: 2px solid var(--primary); padding-left: 15px;">
                <h4 style="color: var(--primary); font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px;">Response</h4>
                <p>${data.answer}</p>
            </div>`;
            
            if (data.context && data.context.length > 0) {
                const contextHTML = data.context.map(item => `<div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 5px;">• ${item}</div>`).join('');
                resultHTML += `<div style="margin-top: 16px;">
                    <h4 style="color: var(--secondary); font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px;">Source Context</h4>
                    ${contextHTML}
                </div>`;
            }
            queryResult.innerHTML = resultHTML;
        } else {
            queryResult.innerHTML = '<p>No matching clusters found in memory.</p>';
        }
    } catch (error) {
        console.error('Error asking query:', error);
        queryResult.innerHTML = '<p class="error-text">Neural query execution failed.</p>';
    } finally {
        btn.disabled = false;
    }
}

// Legacy functions for backward compatibility
// ... keep others ...

function showLoginModal() {
    document.getElementById('login-overlay').style.display = 'flex';
}

async function handleLogin() {
    const user = document.getElementById('login-username').value;
    const pass = document.getElementById('login-password').value;
    
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        
        if (data.access_token) {
            localStorage.setItem('secondbrain_token', data.access_token);
            AUTH_TOKEN = data.access_token;
            document.getElementById('login-overlay').style.display = 'none';
            initDashboard();
        } else {
            alert(data.detail || 'Login failed');
        }
    } catch (e) {
        alert('Connection error');
    }
}

async function handleSignup() {
    const user = document.getElementById('login-username').value;
    const pass = document.getElementById('login-password').value;
    
    try {
        const res = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert('Signup successful! Please login.');
        } else {
            alert(data.detail || 'Signup failed');
        }
    } catch (e) {
        alert('Connection error');
    }
}
