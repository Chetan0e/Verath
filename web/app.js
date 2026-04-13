const API_BASE = "http://localhost:8002";
let AUTH_TOKEN = localStorage.getItem('sb_token');

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (AUTH_TOKEN) {
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
        localStorage.removeItem('sb_token');
        localStorage.removeItem('sb_username');
        window.location.href = 'auth.html';
    }
    return res;
}

// Load and display statistics
async function loadStats() {
    try {
        const res = await authFetch(`${API_BASE}/statistics`);
        const data = await res.json();
        
        // Update UI with statistics
        document.getElementById('total-memories').textContent = data.total || 0;
        document.getElementById('total-speakers').textContent = Object.keys(data.by_speaker || {}).length;
        document.getElementById('important-memories').textContent = Object.values(data.by_intent || {}).reduce((a, b) => a + b, 0);
        document.getElementById('today-memories').textContent = data.recent_count || 0;
        
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
                    <div class="timeline-meta">
                        <span class="timeline-speaker">
                            <i class="fas fa-user-circle"></i> ${item.speaker || 'Unknown Entity'}
                        </span>
                        ${item.intent ? `<span class="timeline-intent">${item.intent}</span>` : ''}
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
            
            if (data.sources && data.sources.length > 0) {
                const sourcesHTML = data.sources.map(source => `
                    <div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 5px;">
                        • ${source.speaker} (${source.timestamp}) - Importance: ${(source.importance * 100).toFixed(0)}%
                    </div>
                `).join('');
                resultHTML += `<div style="margin-top: 16px;">
                    <h4 style="color: var(--secondary); font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px;">Sources</h4>
                    ${sourcesHTML}
                </div>`;
            }
            
            if (data.context && data.context.length > 0) {
                const contextHTML = data.context.map(item => `<div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 5px;">• ${item}</div>`).join('');
                resultHTML += `<div style="margin-top: 16px;">
                    <h4 style="color: var(--secondary); font-size: 0.8rem; text-transform: uppercase; margin-bottom: 8px;">Context</h4>
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

