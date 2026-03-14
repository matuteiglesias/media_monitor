const statusEl = document.getElementById('status');
const metricsEl = document.getElementById('metrics');
const actionsEl = document.getElementById('actions');
const draftsEl = document.getElementById('drafts');
const metaEl = document.getElementById('meta');

const metricConfig = [
  ['Seed ideas', 'seed_ideas_emitted'],
  ['Briefs', 'briefs_emitted'],
  ['Drafts', 'drafts_emitted'],
  ['Fallback', 'fallback_legacy_count'],
];

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function addListItems(container, values, emptyMessage) {
  clearChildren(container);
  if (!Array.isArray(values) || values.length === 0) {
    const li = document.createElement('li');
    li.textContent = emptyMessage;
    container.appendChild(li);
    return;
  }

  values.forEach((value) => {
    const li = document.createElement('li');
    li.textContent = value;
    container.appendChild(li);
  });
}

function setStatus(data, handoff) {
  clearChildren(statusEl);
  statusEl.classList.remove('error');

  const digestNode = document.createElement('span');
  digestNode.append('Digest ');
  const digestCode = document.createElement('code');
  digestCode.textContent = data.digest_at || '-';
  digestNode.appendChild(digestCode);

  const separator1 = document.createTextNode(' · estado ');
  const statusStrong = document.createElement('strong');
  const state = data.status || 'unknown';
  statusStrong.className = state === 'ok' ? 'ok' : 'warn';
  statusStrong.textContent = state;

  const separator2 = document.createTextNode(' · handoff ');
  const handoffStrong = document.createElement('strong');
  handoffStrong.textContent = handoff.status || 'unknown';

  statusEl.append(digestNode, separator1, statusStrong, separator2, handoffStrong);
}

function setMetrics(metrics) {
  clearChildren(metricsEl);
  metricConfig.forEach(([label, key]) => {
    const card = document.createElement('article');
    card.className = 'card';

    const labelDiv = document.createElement('div');
    labelDiv.className = 'label';
    labelDiv.textContent = label;

    const valueDiv = document.createElement('div');
    valueDiv.className = 'value';
    valueDiv.textContent = String(metrics[key] ?? 0);

    card.append(labelDiv, valueDiv);
    metricsEl.appendChild(card);
  });
}

function normalizeActions(candidates) {
  if (!Array.isArray(candidates)) return [];
  return candidates.map((candidate) => {
    if (typeof candidate === 'string') return candidate;
    const priority = candidate?.priority ?? '-';
    const title = candidate?.title ?? candidate?.index_id ?? 'sin título';
    const kind = candidate?.kind ?? candidate?.target_format ?? 'n/a';
    return `[p${priority}] ${kind} — ${title}`;
  });
}

function normalizeDrafts(handoff) {
  const articleDrafts = Array.isArray(handoff?.latest_article_drafts)
    ? handoff.latest_article_drafts.map((draft) => `Artículo: ${draft?.title ?? draft?.index_id ?? 'sin título'}`)
    : [];

  const ytDrafts = Array.isArray(handoff?.latest_yt_script_drafts)
    ? handoff.latest_yt_script_drafts.map((draft) => `YouTube: ${draft?.title ?? draft?.index_id ?? 'sin título'}`)
    : [];

  return [...articleDrafts, ...ytDrafts];
}

function validateShape(data) {
  if (!data || typeof data !== 'object') throw new Error('JSON inválido');
  if (!('human_handoff' in data)) throw new Error('missing human_handoff');
  if (!('metrics' in data)) throw new Error('missing metrics');
}

async function fetchWithTimeout(url, timeoutMs = 6000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(id);
  }
}

async function loadData() {
  const candidates = ['/web/data/editorial_latest.json', '/storage/indexes/editorial_latest.json'];
  let lastError = null;

  for (const url of candidates) {
    try {
      const data = await fetchWithTimeout(url);
      validateShape(data);
      return { data, source: url };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error('No data source available');
}

function renderError(error) {
  clearChildren(statusEl);
  statusEl.classList.add('error');
  statusEl.textContent = `No pude cargar editorial_latest.json: ${error.message}`;
  metaEl.textContent = 'Tip: ejecuta make publish-last-mile-snapshot y vuelve a cargar.';
}

async function bootstrap() {
  try {
    const { data, source } = await loadData();
    const handoff = data.human_handoff || {};
    const metrics = data.metrics || {};

    setStatus(data, handoff);
    setMetrics(metrics);
    addListItems(actionsEl, normalizeActions(handoff.action_candidates), 'Sin candidatos por ahora.');
    addListItems(draftsEl, normalizeDrafts(handoff), 'No hay drafts listos todavía.');

    metaEl.textContent = `Fuente: ${source} · built_at: ${data.built_at ?? 'n/a'}`;
  } catch (error) {
    renderError(error);
  }
}

bootstrap();
