let clientData = {};
let charts = {};

function secondsAgo(ts) {
  return Math.floor((Date.now() / 1000 - ts));
}

function formatTime(seconds) {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusClass(percent) {
  if (percent > 90) return 'critical';
  if (percent > 75) return 'warning';
  return 'normal';
}

function updateStats() {
  const clients = Object.values(clientData);
  const totalClients = clients.length;
  const onlineClients = clients.filter(c => secondsAgo(c.last_seen) < 30).length;

  let totalCpu = 0;
  let cpuCount = 0;

  clients.forEach(client => {
    const cpuPercent = client.cpu?.percent ?? 0;
    if (cpuPercent > 0) {
      totalCpu += cpuPercent;
      cpuCount++;
    }
  });

  const avgCpu = cpuCount > 0 ? Math.round(totalCpu / cpuCount) : 0;

  document.getElementById('totalClients').textContent = totalClients;
  document.getElementById('onlineClients').textContent = onlineClients;
  document.getElementById('avgCpu').textContent = `${avgCpu}%`;
}

function openModal() {
  document.getElementById('clientDetailsModal').style.display = 'block';
  document.body.style.overflow = 'hidden'; // Prevent background scroll
}

function closeModal() {
  document.getElementById('clientDetailsModal').style.display = 'none';
  document.body.style.overflow = 'auto'; // Restore scroll
}

function renderRecommendations(recommendations) {
  if (!recommendations || recommendations.length === 0) {
    return '<div class="no-recommendations">✅ System running optimally</div>';
  }

  return recommendations.map(rec =>
    `<div class="recommendation">⚠️ ${rec}</div>`
  ).join('');
}

function renderProcessList(processes) {
  if (!processes || processes.length === 0) {
    return '<div>No process data available</div>';
  }

  return '<ul class="process-list">' + processes.map(proc =>
    `<li>${proc.name} - ${proc.cpu}% CPU</li>`
  ).join('') + '</ul>';
}

function renderProgramList(programs) {
  if (!programs || programs.length === 0) {
    return '<div>No installed programs found</div>';
  }

  return '<ul class="process-list">' + programs.map(p =>
    `<li>${p.name} - ${p.version}</li>`
  ).join('') + '</ul>';
}

function renderClientDetails(client) {
  const ago = secondsAgo(client.last_seen);
  const cpuPercent = client.cpu?.percent ?? 0;
  const ramPercent = client.memory?.percent ?? 0;

  let diskDetails = '';
  let primaryDiskPercent = 0;

  if (client.disk && typeof client.disk === 'object') {
    diskDetails = '<ul class="disk-list">';
    const diskEntries = Object.entries(client.disk);
    diskEntries.forEach(([drive, info], index) => {
      if (index === 0) primaryDiskPercent = info.percent;
      const statusClass = getStatusClass(info.percent);
      diskDetails += `
        <li class="disk-item ${statusClass}">
          <strong>${drive}</strong>: ${info.percent.toFixed(1)}% 
          (${formatBytes(info.used)} / ${formatBytes(info.total)})
          <span class="filesystem">${info.fstype}</span>
        </li>`;
    });
    diskDetails += '</ul>';
  }

  let networkDetails = '';
  if (client.network && client.network.interfaces) {
    networkDetails = '<ul class="network-list">';
    Object.entries(client.network.interfaces).forEach(([iface, stats]) => {
      networkDetails += `
        <li class="network-item">
          <strong>${iface}</strong>: 
          ↑ ${formatBytes(stats.bytes_sent)} / ↓ ${formatBytes(stats.bytes_recv)}
        </li>`;
    });
    networkDetails += '</ul>';
  }

  let cpuDetails = '';
  if (client.cpu && typeof client.cpu === 'object') {
    cpuDetails = `
      <div class="cpu-details">
        <div>Cores: ${client.cpu.count || 'N/A'}</div>
        ${client.cpu.frequency ? `<div>Frequency: ${client.cpu.frequency.current?.toFixed(0) || 'N/A'} MHz</div>` : ''}
      </div>
    `;
  }

  let memoryDetails = '';
  if (client.memory && typeof client.memory === 'object') {
    memoryDetails = `
      <div class="memory-details">
        <div>Total: ${formatBytes(client.memory.total || 0)}</div>
        <div>Used: ${formatBytes(client.memory.used || 0)}</div>
        <div>Available: ${formatBytes(client.memory.available || 0)}</div>
      </div>
    `;
  }

  const html = `
    <h2>🖥️ ${client.hostname}</h2>

    <div class="detail-section">
      <h3>System Information</h3>
      <div class="info-grid">
        <div><strong>IP Address:</strong> ${client.ip || 'N/A'}</div>
        <div><strong>Operating System:</strong> ${client.os || 'N/A'}</div>
        <div><strong>Architecture:</strong> ${client.architecture || 'N/A'}</div>
        <div><strong>Process Count:</strong> ${client.process_count || 'N/A'}</div>
        <div><strong>Agent Version:</strong> ${client.agent_version || 'N/A'}</div>
        <div><strong>Last Seen:</strong> ${formatTime(ago)} ago</div>
      </div>
    </div>

    <div class="detail-section">
      <h3>Performance Metrics</h3>
      <div class="metrics-grid">
        <div class="metric-card ${getStatusClass(cpuPercent)}">
          <div class="metric-title">CPU Usage</div>
          <div class="metric-value">${cpuPercent.toFixed(1)}%</div>
          ${cpuDetails}
        </div>
        <div class="metric-card ${getStatusClass(ramPercent)}">
          <div class="metric-title">Memory Usage</div>
          <div class="metric-value">${ramPercent.toFixed(1)}%</div>
          ${memoryDetails}
        </div>
        <div class="metric-card ${getStatusClass(primaryDiskPercent)}">
          <div class="metric-title">Disk Usage</div>
          <div class="metric-value">${primaryDiskPercent.toFixed(1)}%</div>
        </div>
      </div>
    </div>

    <div class="detail-section">
      <h3>Storage Details</h3>
      ${diskDetails || '<div>No disk data available</div>'}
    </div>

    <div class="detail-section">
      <h3>Network Interfaces</h3>
      ${networkDetails || '<div>No network data available</div>'}
    </div>

    <div class="detail-section">
      <h3>Top Processes</h3>
      ${renderProcessList(client.top_processes)}
    </div>

    <div class="detail-section">
      <h3>Installed Programs</h3>
      ${renderProgramList(client.installed_programs)}
    </div>

    <div class="detail-section">
      <h3>Recommendations</h3>
      ${renderRecommendations(client.recommendations)}
    </div>
  `;

  document.getElementById('clientDetailsContent').innerHTML = html;
  openModal();
}

async function loadClients() {
  try {
    const res = await fetch("/api/clients");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    
    clientData = await res.json();
    const container = document.getElementById("clientGrid");
    container.innerHTML = "";

    if (Object.keys(clientData).length === 0) {
      container.innerHTML = '<div class="loading">No clients found</div>';
      updateStats();
      return;
    }

    Object.values(clientData).forEach(client => {
      const ago = secondsAgo(client.last_seen);
      const status = ago < 30 ? "online" : "offline";
      const statusText = status === "online" ? "Online" : "Offline";

      const cpuPercent = client.cpu?.percent ?? 0;
      const ramPercent = client.memory?.percent ?? 0;
      
      // Get primary disk usage
      let diskPercent = 0;
      if (client.disk && typeof client.disk === 'object') {
        const diskInfo = Object.values(client.disk);
        if (diskInfo.length > 0) {
          diskPercent = diskInfo[0].percent || 0;
        }
      }

      const card = document.createElement("div");
      card.className = "card";
      card.style.cursor = "pointer";
      
      // Add click handler for modal
      card.addEventListener('click', () => renderClientDetails(client));
      
      card.innerHTML = `
        <div class="card-header">
          <h2><span class="hostname-icon">🖥️</span>${client.hostname}</h2>
          <div class="status ${status}">${statusText}</div>
        </div>

        <div class="meta-info">
          <div class="meta-item">
            <div class="meta-label">IP Address</div>
            <div class="meta-value">${client.ip || 'N/A'}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Operating System</div>
            <div class="meta-value">${(client.os || 'Unknown').substring(0, 20)}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Last Seen</div>
            <div class="meta-value">${formatTime(ago)} ago</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Processes</div>
            <div class="meta-value">${client.process_count || 'N/A'}</div>
          </div>
        </div>

        <div class="metrics">
          <div class="metric">
            <div class="metric-header">
              <div class="metric-label">💻 CPU</div>
              <div class="metric-value">${cpuPercent.toFixed(1)}%</div>
            </div>
            <div class="progress-bar">
              <div class="progress-fill cpu-bar" style="width: ${cpuPercent}%"></div>
            </div>
          </div>
          
          <div class="metric">
            <div class="metric-header">
              <div class="metric-label">🧠 RAM</div>
              <div class="metric-value">${ramPercent.toFixed(1)}%</div>
            </div>
            <div class="progress-bar">
              <div class="progress-fill ram-bar" style="width: ${ramPercent}%"></div>
            </div>
          </div>
          
          <div class="metric">
            <div class="metric-header">
              <div class="metric-label">💾 Disk</div>
              <div class="metric-value">${diskPercent.toFixed(1)}%</div>
            </div>
            <div class="progress-bar">
              <div class="progress-fill disk-bar" style="width: ${diskPercent}%"></div>
            </div>
          </div>
        </div>

        ${client.recommendations && client.recommendations.length > 0 ? `
          <div class="recommendations-preview">
            <div class="recommendation-indicator">⚠️ ${client.recommendations.length} recommendation(s)</div>
          </div>
        ` : ''}
      `;
      
      container.appendChild(card);
    });

    updateStats();
    document.getElementById('lastUpdated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    
  } catch (error) {
    console.error('Failed to load clients:', error);
    document.getElementById("clientGrid").innerHTML = `
      <div class="loading error">
        Failed to load clients: ${error.message}
        <br><small>Check console for details</small>
      </div>
    `;
  }
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
  const modal = document.getElementById('clientDetailsModal');
  if (e.target === modal) {
    closeModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
  }
});

// Auto-refresh functionality
let autoRefresh = true;
let refreshInterval;

function toggleAutoRefresh() {
  autoRefresh = !autoRefresh;
  const button = document.getElementById('autoRefreshBtn');
  if (button) {
    button.textContent = autoRefresh ? 'Auto-refresh: ON' : 'Auto-refresh: OFF';
    button.className = autoRefresh ? 'auto-refresh on' : 'auto-refresh off';
  }
  
  if (autoRefresh) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
}

function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (autoRefresh) {
      loadClients();
    }
  }, 5000);
}

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
  // Add auto-refresh toggle button
  const header = document.querySelector('.header');
  if (header) {
    const controls = document.createElement('div');
    controls.className = 'dashboard-controls';
    controls.style.display = 'flex';
    controls.style.gap = '10px';
    controls.style.flexWrap = 'wrap';
    controls.style.justifyContent = 'center';
    controls.style.alignItems = 'center';
    controls.style.marginTop = '15px';

    controls.innerHTML = `
      <button id="autoRefreshBtn" onclick="toggleAutoRefresh()" class="auto-refresh on">
        Auto-refresh: ON
      </button>
      <button onclick="loadClients()" class="refresh-btn">
        🔄 Refresh Now
      </button>
      <a href="/reports" class="nav-btn">
        📊 View Reports
      </a>
    `;

    header.appendChild(controls);
  }

  // Initial load
  loadClients();
  startAutoRefresh();
});

// Handle page visibility changes (pause refresh when tab is not active)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopAutoRefresh();
  } else if (autoRefresh) {
    loadClients(); // Immediate refresh when returning to tab
    startAutoRefresh();
  }
});