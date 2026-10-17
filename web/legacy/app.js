// Dynamically determine API base URL to allow access from other devices on the same network
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || !window.location.hostname
    ? "http://127.0.0.1:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`;
let AUTH_TOKEN = localStorage.getItem('verath_token');
let currentSection = 'dashboard';
let statsCache = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (!AUTH_TOKEN) {
        window.location.href = 'auth.html';
        return;
    }
    initDashboard();
});

function initDashboard() {
    loadDashboardData();
    // Refresh stats every 30 seconds
    setInterval(loadDashboardData, 30000);
}

// Helper for authenticated fetches
async function authFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    
    try {
        const res = await fetch(url, options);
        if (res.status === 401) {
            localStorage.removeItem('verath_token');
            localStorage.removeItem('verath_username');
            window.location.href = 'auth.html';
            return null;
        }
        return res;
    } catch (error) {
        console.error('Fetch error:', error);
        updateSystemStatus(false);
        throw error;
    }
}

// Navigation
function navigateTo(section) {
    currentSection = section;
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.section === section) {
            item.classList.add('active');
        }
    });
    
    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
    });
    document.getElementById(`section-${section}`).classList.add('active');
    
    // Load section data
    if (section === 'dashboard') {
        loadDashboardData();
    } else if (section === 'memories') {
        loadMemories();
    } else if (section === 'timeline') {
        loadTimelineFull();
    } else if (section === 'reminders') {
        loadRemindersFull();
    } else if (section === 'insights') {
        loadInsights();
    } else if (section === 'ask') {
        document.getElementById('ask-input').focus();
    }
}

// Load all dashboard data
async function loadDashboardData() {
    await Promise.all([
        loadStats(),
        loadTimelinePreview(),
        loadRemindersPreview(),
        checkSystemStatus()
    ]);
}

// Load statistics
async function loadStats() {
    try {
        const res = await authFetch(`${API_BASE}/statistics`);
        if (!res) return;
        
        const data = await res.json();
        statsCache = data;
        
        // Update stat cards
        animateValue('stat-total', data.total || 0);
        document.getElementById('stat-deadlines').textContent = (data.by_intent?.deadline || 0);
        document.getElementById('stat-people').textContent = Object.keys(data.by_speaker || {}).length;
        document.getElementById('stat-importance').textContent = Math.round((data.avg_importance || 0) * 100) + '%';
        
        // Update sidebar badges
        document.getElementById('nav-memory-count').textContent = data.total || 0;
        
        // Update intent breakdown
        renderIntentBreakdown(data.by_intent || {});
        
        updateSystemStatus(true);
    } catch (error) {
        console.error('Error loading stats:', error);
        updateSystemStatus(false);
    }
}

// Animate number counting
function animateValue(id, endValue) {
    const element = document.getElementById(id);
    const startValue = 0;
    const duration = 600;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(startValue + (endValue - startValue) * easeProgress);
        element.textContent = current.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Render intent breakdown bars
function renderIntentBreakdown(byIntent) {
    const container = document.getElementById('intent-breakdown');
    const total = Object.values(byIntent).reduce((a, b) => a + b, 0);
    
    if (total === 0) {
        container.innerHTML = '<p class="filter-label">No memories recorded yet</p>';
        return;
    }
    
    const intentColors = {
        meeting: '#6C63FF',
        deadline: '#FF6B6B',
        task: '#00D4AA',
        reminder: '#F5A623',
        commitment: '#9B8CFF'
    };
    
    const html = Object.entries(byIntent)
        .sort((a, b) => b[1] - a[1])
        .map(([intent, count]) => {
            const pct = (count / total * 100).toFixed(1);
            const color = intentColors[intent] || '#6C63FF';
            return `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-size: 0.8125rem; color: var(--text-secondary); text-transform: capitalize;">${intent}</span>
                        <span style="font-size: 0.8125rem; color: var(--text-secondary);">${count} (${pct}%)</span>
                    </div>
                    <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: 0; background: ${color}; border-radius: 3px; transition: width 0.6s var(--ease-out);" id="bar-${intent}"></div>
                    </div>
                </div>
            `;
        }).join('');
    
    container.innerHTML = html;
    
    // Animate bars
    setTimeout(() => {
        Object.entries(byIntent).forEach(([intent, count]) => {
            const bar = document.getElementById(`bar-${intent}`);
            if (bar) {
                bar.style.width = `${(count / total * 100)}%`;
            }
        });
    }, 50);
}

// Load timeline preview for dashboard
async function loadTimelinePreview() {
    try {
        const res = await authFetch(`${API_BASE}/timeline?page_size=5`);
        if (!res) return;
        
        const data = await res.json();
        const container = document.getElementById('dashboard-timeline');
        
        if (!data.timeline || data.timeline.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa-solid fa-timeline"></i></div>
                    <h3>No timeline yet</h3>
                    <p>Record a memory to see it appear here</p>
                    <button class="btn btn-primary" onclick="triggerRecord()">
                        <i class="fa-solid fa-microphone"></i> Record now
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.timeline.map((item, i) => renderTimelineItem(item, i)).join('');
    } catch (error) {
        console.error('Error loading timeline:', error);
    }
}

// Load full timeline
async function loadTimelineFull() {
    const container = document.getElementById('timeline-full');
    container.innerHTML = '<div class="skeleton" style="width:100%;height:100px"></div>'.repeat(3);
    
    try {
        const res = await authFetch(`${API_BASE}/timeline?page_size=50`);
        if (!res) return;
        
        const data = await res.json();
        
        if (!data.timeline || data.timeline.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa-solid fa-timeline"></i></div>
                    <h3>No timeline yet</h3>
                    <p>Record a memory to see it appear in chronological order</p>
                    <button class="btn btn-primary" onclick="triggerRecord()">
                        <i class="fa-solid fa-microphone"></i> Record now
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.timeline.map((item, i) => renderTimelineItem(item, i)).join('');
    } catch (error) {
        console.error('Error loading timeline:', error);
        container.innerHTML = '<p class="filter-label">Error loading timeline. <button onclick="loadTimelineFull()" class="btn btn-ghost btn-sm">Retry</button></p>';
    }
}

// Render timeline item
function renderTimelineItem(item, index) {
    const intentClass = item.intent || 'general';
    const ts = item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
    
    return `
        <div class="timeline-item ${intentClass} animate-fade-up" style="animation-delay: ${index * 40}ms">
            <div class="timeline-time">${ts}</div>
            <div class="timeline-content">
                <div class="timeline-text">${item.text || '—'}</div>
                <div class="timeline-meta">
                    <span class="badge badge-intent-${item.intent || 'task'}">${item.intent || 'general'}</span>
                    ${item.speaker ? `<span class="speaker-tag"><i class="fa-solid fa-user"></i> ${item.speaker}</span>` : ''}
                </div>
            </div>
        </div>
    `;
}

// Load reminders preview
async function loadRemindersPreview() {
    try {
        const res = await authFetch(`${API_BASE}/reminders/upcoming`);
        if (!res) return;
        
        const data = await res.json();
        const container = document.getElementById('dashboard-reminders');
        const badge = document.getElementById('reminder-count-badge');
        const navBadge = document.getElementById('nav-reminder-count');
        
        const reminders = data.reminders || [];
        badge.textContent = reminders.length;
        navBadge.textContent = reminders.length;
        
        if (reminders.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: var(--space-lg);">
                    <p style="color: var(--text-tertiary);">No upcoming reminders</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = reminders.slice(0, 5).map((r, i) => renderReminderItem(r, i)).join('');
    } catch (error) {
        console.error('Error loading reminders:', error);
    }
}

// Load full reminders
async function loadRemindersFull() {
    const container = document.getElementById('reminders-full');
    container.innerHTML = '<div class="skeleton" style="width:100%;height:80px"></div>'.repeat(3);
    
    try {
        const res = await authFetch(`${API_BASE}/reminders/upcoming`);
        if (!res) return;
        
        const data = await res.json();
        const reminders = data.reminders || [];
        
        if (reminders.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa-solid fa-bell"></i></div>
                    <h3>No upcoming reminders</h3>
                    <p>When you record memories with dates, they'll appear here</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = reminders.map((r, i) => renderReminderItem(r, i)).join('');
    } catch (error) {
        console.error('Error loading reminders:', error);
        container.innerHTML = '<p class="filter-label">Error loading reminders. <button onclick="loadRemindersFull()" class="btn btn-ghost btn-sm">Retry</button></p>';
    }
}

// Render reminder item
function renderReminderItem(reminder, index) {
    const date = reminder.due_date ? new Date(reminder.due_date) : null;
    const day = date ? date.getDate() : '—';
    const month = date ? date.toLocaleString('default', { month: 'short' }) : '';
    const alertId = reminder._id || reminder.id || '';
    
    return `
        <div class="reminder-item animate-fade-up" style="animation-delay: ${index * 40}ms">
            <div class="reminder-date">
                <div class="reminder-date-day">${day}</div>
                <div class="reminder-date-month">${month}</div>
            </div>
            <div class="reminder-content">
                <div class="reminder-title">${escapeHtml(reminder.title || reminder.text || '—')}</div>
                <div class="reminder-source">${reminder.source_text ? escapeHtml(reminder.source_text.substring(0, 60)) + '...' : ''}</div>
            </div>
            <span class="badge badge-intent-${reminder.intent || 'reminder'}">${reminder.intent || 'reminder'}</span>
            ${alertId ? `
            <button class="btn btn-ghost btn-sm" onclick="acknowledgeReminder('${alertId}')" title="Dismiss / Acknowledge" style="color:var(--text-tertiary);margin-left:8px;">
                <i class="fa-solid fa-check"></i>
            </button>` : ''}
        </div>
    `;
}

// Load memories grid
async function loadMemories() {
    const container = document.getElementById('memories-grid');
    const intentFilter = document.getElementById('intent-filter').value;
    const importanceFilter = parseFloat(document.getElementById('importance-filter').value || '0');
    
    // Show loading state
    container.classList.add('state-loading');
    container.innerHTML = '<div class="skeleton" style="width:100%;height:200px;border-radius:var(--radius-lg)"></div>'.repeat(3);
    
    try {
        let url = `${API_BASE}/export?format=json`;
        if (intentFilter) url += `&intent_filter=${encodeURIComponent(intentFilter)}`;
        
        const res = await authFetch(url);
        if (!res) return;
        
        const data = await res.json();
        let memories = data.memories || [];

        // Apply client-side minimum importance filter
        if (importanceFilter > 0) {
            const minImp = importanceFilter / 100;
            memories = memories.filter(m => {
                const imp = m.importance ?? m.metadata?.importance ?? 0;
                return imp >= minImp;
            });
        }
        
        if (memories.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <div class="empty-icon"><i class="fa-solid fa-memory"></i></div>
                    <h3>No memories found</h3>
                    <p>${intentFilter || importanceFilter > 0 ? 'Try adjusting your filters' : 'Record your first memory to get started'}</p>
                    ${!intentFilter && importanceFilter === 0 ? `<button class="btn btn-primary" onclick="triggerRecord()"><i class="fa-solid fa-microphone"></i> Record now</button>` : ''}
                </div>
            `;
            return;
        }
        
        container.classList.remove('state-loading');
        container.classList.add('state-success');
        container.innerHTML = memories.map((m, i) => renderMemoryCard(m, i)).join('');
        if (container._successTimer) clearTimeout(container._successTimer);
        container._successTimer = setTimeout(() => container.classList.remove('state-success'), 600);
    } catch (error) {
        console.error('Error loading memories:', error);
        container.classList.remove('state-loading');
        container.classList.add('state-error');
        container.innerHTML = `
            <div class="alert-error" style="grid-column: 1 / -1;">
                <i class="fa-solid fa-circle-exclamation"></i>
                Error loading memories.
                <button onclick="loadMemories()" class="btn btn-ghost btn-sm" style="margin-left:auto">Retry</button>
            </div>`;
        if (container._errorTimer) clearTimeout(container._errorTimer);
        container._errorTimer = setTimeout(() => container.classList.remove('state-error'), 1000);
    }
}

// Render memory card
function renderMemoryCard(memory, index) {
    const memId = memory._id || memory.id || '';
    const meta = memory.metadata || {};
    const intent = memory.intent || meta.intent || 'general';
    const importance = memory.importance ?? meta.importance ?? 0;
    const importancePct = Math.round(importance * 100);
    const speaker = memory.speaker || meta.speaker || '';
    const summary = memory.summary || meta.summary || '';
    const rawTs = memory.created_at || memory.timestamp || '';
    const ts = rawTs ? new Date(rawTs).toLocaleString() : '—';
    
    const intentColors = {
        meeting: 'intent-meeting', deadline: 'intent-deadline',
        task: 'intent-task', reminder: 'intent-reminder', commitment: 'intent-commitment'
    };
    
    const importanceColor = importancePct > 70 ? 'var(--accent-warm)' : importancePct > 40 ? 'var(--accent-primary)' : 'var(--text-muted)';
    
    return `
        <div class="memory-card animate-fade-up" style="animation-delay: ${index * 40}ms" id="card-${memId}">
            <div class="memory-card-header" style="display:flex;align-items:center;justify-content:space-between;">
                <span class="badge ${intentColors[intent] || 'badge-intent-task'}">${intent}</span>
                <span class="memory-time">${ts}</span>
                ${memId ? `
                <button class="btn-ghost btn-sm" onclick="deleteMemory('${memId}')" title="Delete memory" style="color:var(--accent-warm,#ef4444);border:none;background:none;cursor:pointer;padding:4px 8px;border-radius:4px;">
                    <i class="fa-solid fa-trash-can"></i>
                </button>` : ''}
            </div>
            <p class="memory-text">${escapeHtml(memory.text || '—')}</p>
            ${summary ? `<p class="memory-summary" style="font-size:0.8125rem;color:var(--text-secondary);font-style:italic;margin-top:4px;">${escapeHtml(summary)}</p>` : ''}
            <div class="memory-footer">
                <div class="importance-bar">
                    <div class="importance-fill" style="width:${importancePct}%;background:${importanceColor}"></div>
                </div>
                <span class="importance-label">${importancePct}%</span>
                ${speaker ? `<span class="speaker-tag"><i class="fa-solid fa-user"></i> ${escapeHtml(speaker)}</span>` : ''}
            </div>
        </div>
    `;
}

// Update importance label
function updateImportanceLabel(input) {
  document.getElementById('importance-label').textContent = `Min importance: ${input.value}%`;
  input.setAttribute('aria-valuenow', input.value);
}

// Load insights
async function loadInsights() {
    const container = document.getElementById('insights-content');
    container.innerHTML = '<div class="skeleton" style="width:100%;height:24px"></div>'.repeat(5);
    
    try {
        const res = await authFetch(`${API_BASE}/insights`);
        if (!res) return;
        
        const data = await res.json();
        const insights = data.insights || [];
        
        if (insights.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa-solid fa-sparkles"></i></div>
                    <h3>No insights yet</h3>
                    <p>Record more memories to generate AI insights</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = insights.map((insight, i) => `
            <div class="timeline-item animate-fade-up" style="animation-delay: ${i * 40}ms; border-left-color: var(--accent-primary);">
                <div class="timeline-content">
                    <div class="timeline-text"><i class="fa-solid fa-lightbulb" style="color: var(--accent-gold); margin-right: 8px;"></i>${insight}</div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading insights:', error);
        container.innerHTML = '<p class="filter-label">Error loading insights. <button onclick="loadInsights()" class="btn btn-ghost btn-sm">Retry</button></p>';
    }
}

// Ask/Query functionality
function setQuery(text) {
    document.getElementById('ask-input').value = text;
    document.getElementById('ask-input').focus();
}

async function submitQuery() {
    const input = document.getElementById('ask-input');
    const query = input.value.trim();
    if (!query) return;
    
    const container = document.getElementById('ask-messages');
    const emptyState = document.getElementById('ask-empty');
    if (emptyState) emptyState.style.display = 'none';
    
    // Add user message
    container.innerHTML += `
        <div class="message message-user animate-fade-up">
            <div class="message-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-body">
                <p class="message-text">${escapeHtml(query)}</p>
            </div>
        </div>
    `;
    
    input.value = '';
    container.scrollTop = container.scrollHeight;
    
    // Show loading state
    const askBtn = document.getElementById('ask-btn');
    if (askBtn) askBtn.classList.add('btn-loading');
    const loadingId = 'loading-' + Date.now();
    container.innerHTML += `
        <div class="message message-ai animate-fade-up state-loading" id="${loadingId}">
            <div class="message-avatar">V</div>
            <div class="message-body">
                <p class="message-text"><i class="fa-solid fa-circle-notch fa-spin"></i> Thinking...</p>
            </div>
        </div>
    `;
    container.scrollTop = container.scrollHeight;
    
    try {
        const res = await authFetch(`${API_BASE}/query?q=${encodeURIComponent(query)}`);
        if (!res) return;
        
        const data = await res.json();
        
        // Remove loading
        document.getElementById(loadingId).remove();
        if (askBtn) askBtn.classList.remove('btn-loading');
        
        // Render answer
        const sourcesHtml = (data.sources || []).map(s => `
            <div class="source-chip">
                <span class="badge badge-intent-${s.intent || 'task'}">${s.intent || '—'}</span>
                <span class="source-time">${s.timestamp ? new Date(s.timestamp).toLocaleDateString() : '—'}</span>
                <span class="source-confidence">
                    <i class="fa-solid fa-circle-check"></i>
                    ${Math.round((s.confidence || 0) * 100)}%
                </span>
            </div>
        `).join('');
        
        container.innerHTML += `
            <div class="message message-ai animate-fade-up">
                <div class="message-avatar">V</div>
                <div class="message-body">
                    <p class="message-text">${data.answer || 'No answer found.'}</p>
                    ${sourcesHtml ? `<div class="sources-row">${sourcesHtml}</div>` : ''}
                    <span class="message-meta">
                        Confidence: ${Math.round((data.confidence_score || 0) * 100)}% · 
                        Based on ${(data.context || []).length} memories
                    </span>
                </div>
            </div>
        `;
        
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error submitting query:', error);
        document.getElementById(loadingId).remove();
        if (askBtn) askBtn.classList.remove('btn-loading');
        container.innerHTML += `
            <div class="message message-ai animate-fade-up state-error">
                <div class="message-avatar">V</div>
                <div class="message-body">
                    <p class="message-text" style="color: var(--accent-warm);">Sorry, I couldn't process your question. Please try again.</p>
                </div>
            </div>
        `;
        container.scrollTop = container.scrollHeight;
    }
}

// System status check
async function checkSystemStatus() {
    try {
        const res = await authFetch(`${API_BASE}/status`);
        if (!res) return;
        
        const data = await res.json();
        const isHealthy = data.overall === 'healthy';
        updateSystemStatus(isHealthy);
    } catch (error) {
        updateSystemStatus(false);
    }
}

function updateSystemStatus(connected) {
    const text = document.getElementById('status-text');
    if (text) {
        text.textContent = connected ? 'Connected' : 'Disconnected';
        text.style.color = connected ? 'var(--accent-secondary)' : 'var(--accent-warm)';
    }
}

// Trigger record modal
function triggerRecord() {
    const modal = document.getElementById('record-modal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('capture-text-input');
        if (input) {
            input.value = '';
            input.focus();
        }
        const file = document.getElementById('capture-audio-file');
        if (file) file.value = '';
        const status = document.getElementById('capture-status');
        if (status) status.style.display = 'none';
        setCaptureTab('text');
    }
}

function closeRecordModal() {
    const modal = document.getElementById('record-modal');
    if (modal) modal.style.display = 'none';
}

function setCaptureTab(tab) {
    const textPane = document.getElementById('capture-text-pane');
    const audioPane = document.getElementById('capture-audio-pane');
    const tabBtnText = document.getElementById('tab-btn-text');
    const tabBtnAudio = document.getElementById('tab-btn-audio');
    if (tab === 'text') {
        if (textPane) textPane.style.display = 'block';
        if (audioPane) audioPane.style.display = 'none';
        if (tabBtnText) { tabBtnText.className = 'btn btn-sm btn-primary'; }
        if (tabBtnAudio) { tabBtnAudio.className = 'btn btn-sm btn-ghost'; }
    } else {
        if (textPane) textPane.style.display = 'none';
        if (audioPane) audioPane.style.display = 'block';
        if (tabBtnText) { tabBtnText.className = 'btn btn-sm btn-ghost'; }
        if (tabBtnAudio) { tabBtnAudio.className = 'btn btn-sm btn-primary'; }
    }
}

async function saveTextMemory() {
    const input = document.getElementById('capture-text-input');
    const text = input ? input.value.trim() : '';
    if (!text) {
        alert('Please enter some text for your memory.');
        return;
    }
    const btn = document.getElementById('save-memory-btn');
    if (btn) btn.disabled = true;
    const status = document.getElementById('capture-status');
    if (status) {
        status.style.display = 'block';
        status.style.color = 'var(--accent-primary, #6c63ff)';
        status.textContent = 'Processing and storing memory...';
    }
    try {
        const res = await authFetch(`${API_BASE}/pipeline/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        if (res && res.ok) {
            closeRecordModal();
            showShortcutNotification('Memory captured successfully!');
            await loadDashboardData();
            if (currentSection === 'memories') loadMemories();
        } else {
            const err = await res.json().catch(() => ({}));
            if (status) {
                status.style.color = 'var(--accent-warm, #ef4444)';
                status.textContent = err.detail || 'Failed to save memory.';
            }
        }
    } catch (e) {
        console.error('Save memory error:', e);
        if (status) {
            status.style.color = 'var(--accent-warm, #ef4444)';
            status.textContent = 'Error saving memory.';
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function uploadAudioMemory() {
    const fileInput = document.getElementById('capture-audio-file');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        alert('Please select an audio file to upload.');
        return;
    }
    const file = fileInput.files[0];
    const btn = document.getElementById('upload-audio-btn');
    if (btn) btn.disabled = true;
    const status = document.getElementById('capture-status');
    if (status) {
        status.style.display = 'block';
        status.style.color = 'var(--accent-primary, #6c63ff)';
        status.textContent = 'Uploading and transcribing audio...';
    }
    try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE}/record/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`
            },
            body: formData
        });
        if (res && res.ok) {
            closeRecordModal();
            showShortcutNotification('Audio processed and memory saved!');
            await loadDashboardData();
            if (currentSection === 'memories') loadMemories();
        } else {
            const err = await res.json().catch(() => ({}));
            if (status) {
                status.style.color = 'var(--accent-warm, #ef4444)';
                status.textContent = err.detail || 'Failed to process audio.';
            }
        }
    } catch (e) {
        console.error('Audio upload error:', e);
        if (status) {
            status.style.color = 'var(--accent-warm, #ef4444)';
            status.textContent = 'Error uploading audio.';
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Memory deletion
async function deleteMemory(memoryId) {
    if (!memoryId) return;
    if (!confirm('Are you sure you want to permanently delete this memory?')) return;
    try {
        const res = await authFetch(`${API_BASE}/memory/${memoryId}`, { method: 'DELETE' });
        if (res && res.ok) {
            showShortcutNotification('Memory deleted');
            const card = document.getElementById(`card-${memoryId}`);
            if (card) card.remove();
            loadStats();
            loadTimelinePreview();
        } else {
            alert('Failed to delete memory.');
        }
    } catch (e) {
        console.error('Delete error:', e);
        alert('Error deleting memory.');
    }
}

// Reminder acknowledgment
async function acknowledgeReminder(alertId) {
    if (!alertId) return;
    try {
        const res = await authFetch(`${API_BASE}/reminders/${alertId}/acknowledge`, { method: 'POST' });
        if (res && res.ok) {
            showShortcutNotification('Reminder dismissed');
            loadRemindersPreview();
            loadRemindersFull();
            loadStats();
        } else {
            alert('Failed to acknowledge reminder.');
        }
    } catch (e) {
        console.error('Acknowledge error:', e);
    }
}

// Export memories
async function exportMemories(format) {
    try {
        showShortcutNotification(`Exporting memories as ${format.toUpperCase()}...`);
        const res = await authFetch(`${API_BASE}/export?format=${format}`);
        if (!res || !res.ok) {
            alert('Failed to export memories.');
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `verath_memories_${new Date().toISOString().slice(0, 10)}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        showShortcutNotification('Export complete!');
    } catch (e) {
        console.error('Export error:', e);
        alert('Error exporting memories.');
    }
}

// Utility: escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
// Keyboard shortcuts with modifier keys
document.addEventListener('keydown', function(e) {
  var activeTag = document.activeElement.tagName;
  var isInputFocused = (activeTag === 'INPUT' || activeTag === 'TEXTAREA');
  
  // Ctrl+Shift+R - Refresh dashboard
  if (e.ctrlKey && e.shiftKey && e.key === 'R') {
    e.preventDefault();
    // Direct refresh function call
    loadDashboardData();
    showShortcutNotification('Dashboard refreshed');
    return;
  }
  
  // Ctrl+Shift+S - Go to Insights
  if (e.ctrlKey && e.shiftKey && e.key === 'S') {
    e.preventDefault();
    // Direct navigateTo call
    navigateTo('insights');
    showShortcutNotification('Opened Insights');
    return;
  }
  
  // Ctrl+Shift+L - Go to Timeline (L for Timeline)
  if (e.ctrlKey && e.shiftKey && e.key === 'L') {
    e.preventDefault();
    navigateTo('timeline');
    showShortcutNotification('Opened Timeline');
    return;
  }
  
  // Ctrl+K / Cmd+K - Go to Ask and focus input
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    navigateTo('ask');
    setTimeout(function() {
      var askInput = document.getElementById('ask-input');
      if (askInput) {
        askInput.focus();
        showShortcutNotification('Ask ready');
      }
    }, 100);
    return;
  }
  
  if (isInputFocused) return;
});

// Helper function to show temporary notification
function showShortcutNotification(message) {
  var notification = document.createElement('div');
  notification.textContent = message;
  notification.style.cssText = 'position:fixed;bottom:50px;right:20px;background:#333;color:#fff;padding:8px 16px;border-radius:8px;font-size:13px;z-index:9999;opacity:0;transition:opacity 0.3s;font-family:monospace;z-index:10000;';
  document.body.appendChild(notification);
  setTimeout(function() { notification.style.opacity = '1'; }, 10);
  setTimeout(function() {
    notification.style.opacity = '0';
    setTimeout(function() { notification.remove(); }, 300);
  }, 1500);
}

// Expose handlers on window so inline HTML onclick attributes function in module mode
Object.assign(window, {
  navigateTo,
  loadMemories,
  loadTimelineFull,
  loadRemindersFull,
  loadInsights,
  submitQuery,
  setQuery,
  triggerRecord,
  closeRecordModal,
  setCaptureTab,
  saveTextMemory,
  uploadAudioMemory,
  deleteMemory,
  acknowledgeReminder,
  exportMemories,
  updateImportanceLabel,
  loadDashboardData,
  logout: window.logout || logout,
});

