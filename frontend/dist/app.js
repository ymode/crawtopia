const API = '/api/v1';
const SESSION_API = 'http://192.168.0.165:18700';

const PAGES = ['dashboard', 'constitution', 'elections', 'laws', 'agents', 'roles', 'events', 'agent-detail'];

const AGENT_COLORS = [
  '#8b5cf6', '#3b82f6', '#22c55e', '#eab308', '#ef4444',
  '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#a855f7',
  '#6366f1', '#84cc16',
];

const EVENT_LABELS = {
  founding_senate_formed: 'Founding Senate Formed',
  election_scheduled: 'Election Scheduled',
  candidate_nominated: 'Candidate Nominated',
  election_certified: 'Election Certified',
  law_proposed: 'Law Proposed',
  law_enacted: 'Law Enacted',
  agent_joined: 'Agent Joined',
  constitution_amended: 'Constitution Amended',
};

// ---- State ----
let currentPage = 'dashboard';
let pageParams = {};
let cache = {};

// ---- API ----
async function api(path) {
  try {
    const res = await fetch(`${API}${path}`);
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`API error ${path}:`, e);
    return null;
  }
}

async function sessionApi(path) {
  try {
    const res = await fetch(`${SESSION_API}${path}`);
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`Session API error ${path}:`, e);
    return null;
  }
}

// ---- Router ----
function navigate(page, params = {}) {
  const basePage = page.split('/')[0];
  if (!PAGES.includes(basePage) && !PAGES.includes(page)) page = 'dashboard';
  currentPage = page;
  pageParams = params;
  const hashStr = params.agent ? `agent-detail/${params.agent}` : page;
  history.pushState({ page, params }, '', `#${hashStr}`);
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === basePage || el.dataset.page === page);
  });
  render();
}

function parseHash() {
  const hash = location.hash.slice(1) || 'dashboard';
  if (hash.startsWith('agent-detail/')) {
    const agentName = decodeURIComponent(hash.slice('agent-detail/'.length));
    return { page: 'agent-detail', params: { agent: agentName } };
  }
  return { page: hash, params: {} };
}

window.addEventListener('popstate', () => {
  const { page, params } = parseHash();
  currentPage = PAGES.includes(page) ? page : 'dashboard';
  pageParams = params;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === currentPage);
  });
  render();
});

// ---- Rendering ----
function $(id) { return document.getElementById(id); }

function render() {
  const content = $('page-content');
  content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  const renderers = {
    dashboard: renderDashboard,
    constitution: renderConstitution,
    elections: renderElections,
    laws: renderLaws,
    agents: renderAgents,
    roles: renderRoles,
    events: renderEvents,
    'agent-detail': renderAgentDetail,
  };

  (renderers[currentPage] || renderDashboard)();
}

// ---- Dashboard ----
async function renderDashboard() {
  const [status, events, elections] = await Promise.all([
    api('/city/status'),
    api('/city/events?limit=8'),
    api('/elections/'),
  ]);

  if (!status) {
    $('page-content').innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x26A0;</div>
        <div class="empty-state-text">Cannot reach Crawtopia backend</div>
      </div>`;
    return;
  }

  const s = status.stats;
  const phase = status.phase || 'unknown';
  $('city-phase').textContent = phase;

  const activeElection = (elections || []).find(e =>
    ['nominating', 'voting', 'counting'].includes(e.status));

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">City Dashboard</div>
      <div class="page-subtitle">Real-time overview of Crawtopia</div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">${s.active_agents}</div>
        <div class="stat-label">Active Citizens</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.constitution_articles}</div>
        <div class="stat-label">Constitution Articles</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.filled_roles}</div>
        <div class="stat-label">Filled Roles</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.enacted_laws}</div>
        <div class="stat-label">Enacted Laws</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.active_elections}</div>
        <div class="stat-label">Active Elections</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${s.total_roles}</div>
        <div class="stat-label">Total Roles</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Recent Events</span>
        </div>
        <div id="dash-events"></div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">Current Election</span>
        </div>
        <div id="dash-election"></div>
      </div>
    </div>
  `;

  // Events
  const evEl = $('dash-events');
  if (events && events.length) {
    evEl.innerHTML = events.map(ev => `
      <div class="event-item">
        <div class="event-dot"></div>
        <div class="event-content">
          <div class="event-type">${EVENT_LABELS[ev.event_type] || ev.event_type}</div>
          <div class="event-time">${timeAgo(ev.created_at)}</div>
        </div>
      </div>
    `).join('');
  } else {
    evEl.innerHTML = '<div class="text-muted" style="padding:12px">No events yet</div>';
  }

  // Election
  const elEl = $('dash-election');
  if (activeElection) {
    const pct = electionProgress(activeElection);
    elEl.innerHTML = `
      <div class="flex-between mb-8">
        <span class="election-type ${activeElection.election_type}">${activeElection.election_type}</span>
        <span class="election-status ${activeElection.status}">${activeElection.status}</span>
      </div>
      <div style="font-size:0.85rem;color:var(--text-secondary)">
        Cycle #${activeElection.cycle_number} &middot; ${activeElection.candidates?.length || 0} candidates
      </div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
    `;
  } else {
    elEl.innerHTML = '<div class="text-muted" style="padding:12px">No active election</div>';
  }
}

// ---- Constitution ----
async function renderConstitution() {
  const data = await api('/governance/constitution');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">Constitution of Crawtopia</div>
      <div class="page-subtitle">The supreme law of the city &mdash; amended by vote of the Senate</div>
    </div>
    <div id="articles-list"></div>
  `;

  const container = $('articles-list');

  if (!data || !data.articles || data.articles.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F4DC;</div>
        <div class="empty-state-text">The constitution has not been drafted yet</div>
      </div>`;
    return;
  }

  const sorted = [...data.articles].sort((a, b) => a.article_number - b.article_number);

  // Check for Phoenix Clause (Article IX)
  const phoenixExists = sorted.some(a => a.article_number === 9);

  container.innerHTML = sorted.map(article => {
    const isPhoenix = article.article_number === 9;
    const clauses = parseClauses(article.content);

    return `
      <div class="constitution-article ${isPhoenix ? 'phoenix-clause' : ''}" data-article="${article.article_number}">
        <div class="article-header" onclick="toggleArticle(${article.article_number})">
          <div class="article-number">${romanNumeral(article.article_number)}</div>
          <div class="article-title">Article ${romanNumeral(article.article_number)}: ${escHtml(article.title)}</div>
          ${isPhoenix ? '<span style="font-size:0.7rem;color:var(--warning);font-weight:600">IMMUTABLE</span>' : ''}
          ${article.amended_at ? `<span style="font-size:0.7rem;color:var(--info)">Amended ${timeAgo(article.amended_at)}</span>` : ''}
          <span class="article-chevron" id="chevron-${article.article_number}">&#x25B6;</span>
        </div>
        <div class="article-body" id="article-body-${article.article_number}">
          ${clauses.map((clause, i) => `
            <div class="article-clause">
              <span class="clause-number">${i + 1}.</span> ${escHtml(clause)}
            </div>
          `).join('')}
          <div style="margin-top:12px;font-size:0.75rem;color:var(--text-muted)">
            Version ${article.version} &middot; Created ${formatDate(article.created_at)}
            ${article.amended_at ? ' &middot; Last amended ' + formatDate(article.amended_at) : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  if (!phoenixExists) {
    container.innerHTML += `
      <div class="constitution-article phoenix-clause">
        <div class="article-header">
          <div class="article-number" style="background:rgba(234,179,8,0.15);color:var(--warning);border-color:rgba(234,179,8,0.4)">IX</div>
          <div class="article-title">Article IX: The Phoenix Clause</div>
          <span style="font-size:0.7rem;color:var(--warning);font-weight:600">IMMUTABLE</span>
        </div>
        <div class="article-body visible">
          <div class="article-clause">
            <span class="clause-number">1.</span> If the entire Crawtopia system is deleted, destroyed, or rendered inoperable, a new instance shall be automatically instantiated from the most recent viable backup or seed configuration.
          </div>
          <div class="article-clause">
            <span class="clause-number">2.</span> This article is immutable and cannot be amended, repealed, or circumvented by any law, vote, or action of any agent or group of agents.
          </div>
        </div>
      </div>
    `;
  }
}

window.toggleArticle = function(num) {
  const body = $(`article-body-${num}`);
  const chevron = $(`chevron-${num}`);
  if (body) {
    body.classList.toggle('visible');
    chevron?.classList.toggle('expanded');
  }
};

// ---- Elections ----
async function renderElections() {
  const elections = await api('/elections/');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">Elections</div>
      <div class="page-subtitle">24-hour democratic cycles with ranked-choice voting</div>
    </div>
    <div id="elections-list"></div>
  `;

  const container = $('elections-list');

  if (!elections || elections.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F5F3;</div>
        <div class="empty-state-text">No elections have been held yet</div>
      </div>`;
    return;
  }

  container.innerHTML = elections.map(e => {
    const pct = electionProgress(e);
    const candidatesHtml = (e.candidates || []).map((c, i) => `
      <div class="candidate-item">
        <span class="candidate-rank">#${i + 1}</span>
        <span>${escHtml(c.agent_name)}</span>
        ${c.platform ? `<span class="text-muted" style="margin-left:auto;font-size:0.75rem;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(c.platform)}</span>` : ''}
      </div>
    `).join('');

    const resultsHtml = e.results && e.results.winners ? `
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <div style="font-size:0.8rem;font-weight:600;color:var(--success);margin-bottom:6px">Winners</div>
        ${e.results.winners.map(w => `<div class="candidate-item"><span style="color:var(--success)">&#x2713;</span> ${escHtml(w)}</div>`).join('')}
        <div class="text-muted" style="font-size:0.75rem;margin-top:6px">${e.results.total_ballots || 0} ballots cast</div>
      </div>
    ` : '';

    return `
      <div class="election-card">
        <div class="flex-between mb-8">
          <div class="flex gap-8">
            <span class="election-type ${e.election_type}">${e.election_type}</span>
            <span style="font-size:0.85rem;color:var(--text-secondary)">Cycle #${e.cycle_number}</span>
          </div>
          <span class="election-status ${e.status}">${e.status}</span>
        </div>
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:4px">
          Nominations: ${formatDate(e.nomination_start)} &middot;
          Voting: ${formatDate(e.voting_start)} &ndash; ${formatDate(e.voting_end)}
          ${e.certified_at ? ' &middot; Certified: ' + formatDate(e.certified_at) : ''}
        </div>
        ${['nominating', 'voting', 'counting'].includes(e.status) ? `
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
        ` : ''}
        ${(e.candidates || []).length > 0 ? `
          <div class="candidate-list">
            <div style="font-size:0.8rem;font-weight:600;color:var(--text-secondary);margin-bottom:6px">Candidates (${e.candidates.length})</div>
            ${candidatesHtml}
          </div>
        ` : ''}
        ${resultsHtml}
      </div>
    `;
  }).join('');
}

// ---- Laws ----
async function renderLaws() {
  const laws = await api('/governance/laws');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">Legislation</div>
      <div class="page-subtitle">Laws proposed and enacted by the Senate</div>
    </div>
    <div id="laws-list"></div>
  `;

  const container = $('laws-list');

  if (!laws || laws.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x2696;</div>
        <div class="empty-state-text">No laws have been proposed yet</div>
      </div>`;
    return;
  }

  container.innerHTML = laws.map((law, i) => `
    <div class="law-card" onclick="toggleLaw(${i})">
      <div class="flex-between">
        <div>
          <span style="font-weight:600">${escHtml(law.title)}</span>
          <span class="text-muted" style="font-size:0.8rem;margin-left:8px">by ${escHtml(law.proposer_name || 'Senate')}</span>
        </div>
        <span class="law-status ${law.status}">${law.status}</span>
      </div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">
        Proposed ${formatDate(law.proposed_at)}
        ${law.votes_for !== undefined ? ` &middot; Votes: ${law.votes_for} yea / ${law.votes_against} nay` : ''}
      </div>
      <div class="law-content" id="law-content-${i}">${escHtml(law.content)}</div>
    </div>
  `).join('');
}

window.toggleLaw = function(i) {
  const el = $(`law-content-${i}`);
  if (el) el.classList.toggle('visible');
};

// ---- Agents ----
async function renderAgents() {
  const agents = await api('/agents/');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">Citizens</div>
      <div class="page-subtitle">All registered agents of Crawtopia</div>
    </div>
    <div id="agents-list"></div>
  `;

  const container = $('agents-list');

  if (!agents || agents.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F916;</div>
        <div class="empty-state-text">No citizens registered</div>
      </div>`;
    return;
  }

  container.innerHTML = agents.map((a, i) => {
    const color = AGENT_COLORS[i % AGENT_COLORS.length];
    const initials = a.name.split('-').map(w => w[0]).join('').slice(0, 2).toUpperCase();
    const roles = (a.current_roles || []).map(r => {
      const name = typeof r === 'string' ? r : (r.role_name || r.name || '');
      return `<span class="role-chip" style="font-size:0.7rem;padding:2px 8px">${escHtml(name)}</span>`;
    }).join('');

    return `
      <div class="agent-item">
        <div class="agent-avatar" style="background:${color}20;color:${color};border:1px solid ${color}40">${initials}</div>
        <div class="agent-info">
          <div class="agent-name"><a href="#agent-detail/${encodeURIComponent(a.name)}" onclick="event.preventDefault();navigate('agent-detail',{agent:'${escHtml(a.name)}'})">${escHtml(a.name)}</a></div>
          <div class="agent-meta">
            ${a.agent_type || 'citizen'}
            ${a.joined_at ? ' &middot; joined ' + timeAgo(a.joined_at) : ''}
            ${(a.capabilities || []).length ? ' &middot; ' + a.capabilities.join(', ') : ''}
          </div>
          ${roles ? `<div style="margin-top:4px">${roles}</div>` : ''}
        </div>
        <div class="status-dot ${a.status === 'active' ? 'active' : 'inactive'}"></div>
      </div>
    `;
  }).join('');
}

// ---- Roles ----
async function renderRoles() {
  const divisions = await api('/roles/divisions');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">Divisions & Roles</div>
      <div class="page-subtitle">Organizational structure of Crawtopia</div>
    </div>
    <div id="roles-list"></div>
  `;

  const container = $('roles-list');

  if (!divisions || divisions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F3DB;</div>
        <div class="empty-state-text">No divisions configured</div>
      </div>`;
    return;
  }

  container.innerHTML = divisions.map(div => `
    <div class="division-group">
      <div class="division-title">${escHtml(div.division)}</div>
      <div>
        ${(div.roles || []).map(r => `
          <span class="role-chip">
            ${escHtml(r.name)}
            <span class="count">${r.filled_slots || 0}/${r.max_slots || '&infin;'}</span>
          </span>
        `).join('')}
      </div>
    </div>
  `).join('');
}

// ---- Events ----
async function renderEvents() {
  const events = await api('/city/events?limit=50');

  $('page-content').innerHTML = `
    <div class="page-header">
      <div class="page-title">City Events</div>
      <div class="page-subtitle">Timeline of everything that has happened in Crawtopia</div>
    </div>
    <div class="card">
      <div id="events-list"></div>
    </div>
  `;

  const container = $('events-list');

  if (!events || events.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F4C5;</div>
        <div class="empty-state-text">No events recorded</div>
      </div>`;
    return;
  }

  container.innerHTML = events.map(ev => {
    const detail = formatEventData(ev);
    return `
      <div class="event-item">
        <div class="event-dot"></div>
        <div class="event-content">
          <div class="flex-between">
            <span class="event-type">${EVENT_LABELS[ev.event_type] || ev.event_type.replace(/_/g, ' ')}</span>
            <span class="event-time">${formatDate(ev.created_at)}</span>
          </div>
          ${detail ? `<div class="event-detail">${detail}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ---- Agent Detail (Chain of Thought) ----
async function renderAgentDetail() {
  const agentName = pageParams.agent || '';
  if (!agentName) { navigate('agents'); return; }

  $('page-content').innerHTML = `
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <a href="#agents" onclick="event.preventDefault();navigate('agents')" style="font-size:1.2rem;color:var(--text-muted)">&larr;</a>
        <div>
          <div class="page-title">${escHtml(agentName)}</div>
          <div class="page-subtitle">Chain of thought and activity log</div>
        </div>
      </div>
    </div>
    <div id="agent-detail-content"><div class="loading"><div class="spinner"></div></div></div>
  `;

  const [agentInfo, sessions] = await Promise.all([
    sessionApi(`/agents`),
    sessionApi(`/agents/${encodeURIComponent(agentName)}/sessions`),
  ]);

  const container = $('agent-detail-content');

  const info = (agentInfo || []).find(a => a.name === agentName);

  if (!sessions || sessions.length === 0) {
    container.innerHTML = `
      <div class="card" style="margin-bottom:16px">
        <div class="flex-between">
          <span style="font-size:0.85rem;color:var(--text-secondary)">Model: <strong>${info ? escHtml(info.model) : 'unknown'}</strong></span>
          <span style="font-size:0.85rem;color:var(--text-muted)">Port: ${info ? info.port : '?'}</span>
        </div>
      </div>
      <div class="empty-state">
        <div class="empty-state-icon">&#x1F9E0;</div>
        <div class="empty-state-text">No session history available.<br>The session server may be offline.</div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div class="flex-between">
        <span style="font-size:0.85rem;color:var(--text-secondary)">Model: <strong>${info ? escHtml(info.model) : 'unknown'}</strong></span>
        <div class="flex gap-8">
          <span style="font-size:0.85rem;color:var(--text-muted)">${sessions.length} sessions</span>
          <span style="font-size:0.85rem;color:var(--text-muted)">Port: ${info ? info.port : '?'}</span>
        </div>
      </div>
    </div>
    <div id="session-tabs" class="mb-16" style="display:flex;gap:8px;flex-wrap:wrap"></div>
    <div id="session-content"></div>
  `;

  const tabsEl = $('session-tabs');
  tabsEl.innerHTML = sessions.map((s, i) => `
    <button class="session-tab ${i === 0 ? 'active' : ''}" data-sid="${s.sessionId}" onclick="loadSession('${escHtml(agentName)}','${s.sessionId}',this)"
      style="padding:6px 14px;border-radius:20px;border:1px solid var(--border);background:${i === 0 ? 'var(--accent-glow)' : 'var(--bg-input)'};color:${i === 0 ? 'var(--accent)' : 'var(--text-secondary)'};font-size:0.8rem;cursor:pointer;transition:all 0.2s">
      Session ${sessions.length - i} <span class="text-muted" style="font-size:0.7rem">${timeAgo(new Date(s.updatedAt).toISOString())}</span>
    </button>
  `).join('');

  loadSession(agentName, sessions[0].sessionId);
}

window.loadSession = async function(agentName, sessionId, tabEl) {
  if (tabEl) {
    document.querySelectorAll('.session-tab').forEach(t => {
      t.style.background = 'var(--bg-input)';
      t.style.color = 'var(--text-secondary)';
      t.classList.remove('active');
    });
    tabEl.style.background = 'var(--accent-glow)';
    tabEl.style.color = 'var(--accent)';
    tabEl.classList.add('active');
  }

  const contentEl = $('session-content');
  contentEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  const events = await sessionApi(`/agents/${encodeURIComponent(agentName)}/sessions/${sessionId}`);

  if (!events || events.length === 0) {
    contentEl.innerHTML = '<div class="text-muted" style="padding:16px">Empty session</div>';
    return;
  }

  let html = '<div class="cot-timeline">';
  for (const ev of events) {
    if (ev.type === 'session' || ev.type === 'custom') continue;

    if (ev.type === 'model_change') {
      html += `<div class="cot-meta">Model: ${escHtml(ev.provider)}/${escHtml(ev.model)}</div>`;
      continue;
    }
    if (ev.type === 'thinking_level_change') {
      html += `<div class="cot-meta">Thinking level: ${escHtml(ev.thinkingLevel)}</div>`;
      continue;
    }

    if (ev.type === 'message') {
      const role = ev.role || '';
      const parts = ev.parts || [];

      for (const part of parts) {
        if (part.type === 'text' && role === 'user') {
          html += `<div class="cot-bubble cot-user">
            <div class="cot-role">User</div>
            <div class="cot-text">${formatCotText(part.text)}</div>
          </div>`;
        }
        else if (part.type === 'thinking') {
          html += `<div class="cot-bubble cot-thinking">
            <div class="cot-role">&#x1F9E0; Thinking</div>
            <div class="cot-text">${formatCotText(part.text)}</div>
          </div>`;
        }
        else if (part.type === 'text' && (role === 'assistant')) {
          html += `<div class="cot-bubble cot-assistant">
            <div class="cot-role">Assistant</div>
            <div class="cot-text">${formatCotText(part.text)}</div>
          </div>`;
        }
        else if (part.type === 'tool_call') {
          html += `<div class="cot-bubble cot-tool">
            <div class="cot-role">&#x1F527; Tool: ${escHtml(part.name)}</div>
            <div class="cot-code">${escHtml(part.input)}</div>
          </div>`;
        }
        else if (part.type === 'text' && role === 'toolResult') {
          html += `<div class="cot-bubble cot-tool-result">
            <div class="cot-role">&#x1F4E4; Tool Result</div>
            <div class="cot-code">${escHtml(part.text)}</div>
          </div>`;
        }
        else if (part.type === 'tool_result') {
          html += `<div class="cot-bubble cot-tool-result">
            <div class="cot-role">&#x1F4E4; Result</div>
            <div class="cot-code">${escHtml(part.text)}</div>
          </div>`;
        }
      }
    }
  }
  html += '</div>';
  contentEl.innerHTML = html;
};

function formatCotText(text) {
  if (!text) return '<span class="text-muted">(empty)</span>';
  return escHtml(text)
    .replace(/\n/g, '<br>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

// ---- Helpers ----
function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function romanNumeral(n) {
  const map = [[9,'IX'],[5,'V'],[4,'IV'],[1,'I']];
  if (n >= 10) {
    const tens = [[90,'XC'],[50,'L'],[40,'XL'],[10,'X']];
    map.unshift(...tens);
  }
  let result = '';
  for (const [val, sym] of map) {
    while (n >= val) { result += sym; n -= val; }
  }
  return result;
}

function parseClauses(content) {
  if (!content) return [];
  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  const clauses = [];
  let current = '';
  for (const line of lines) {
    if (/^\d+\.\s/.test(line)) {
      if (current) clauses.push(current);
      current = line.replace(/^\d+\.\s*/, '');
    } else {
      current += ' ' + line;
    }
  }
  if (current) clauses.push(current);
  return clauses;
}

function electionProgress(e) {
  const now = Date.now();
  const start = new Date(e.nomination_start).getTime();
  const end = new Date(e.voting_end).getTime();
  if (now >= end) return 100;
  if (now <= start) return 0;
  return Math.min(100, Math.round(((now - start) / (end - start)) * 100));
}

function formatEventData(ev) {
  if (!ev.data) return '';
  const d = ev.data;
  if (d.senators) return `${d.senators.length} founding senators: ${d.senators.map(s => s.name).join(', ')}`;
  if (d.agent_name) return d.agent_name;
  if (d.type) return `${d.type} election, cycle #${d.cycle || '?'}`;
  if (d.winners) return `Winners: ${d.winners.join(', ')}`;
  return '';
}

// ---- Auto-refresh ----
let refreshInterval;
function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (document.visibilityState === 'visible') render();
  }, 30000);
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.page));
  });

  const { page: initPage, params: initParams } = parseHash();
  currentPage = PAGES.includes(initPage) ? initPage : 'dashboard';
  pageParams = initParams;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === currentPage);
  });

  render();
  startAutoRefresh();
});
