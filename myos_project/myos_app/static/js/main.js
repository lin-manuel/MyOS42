const CHECK_ICON_SMALL = '<i class="fas fa-check check-icon-small"></i>';
const CHECK_ICON = '<i class="fas fa-check check-icon-normal"></i>';
const AUTH_STORAGE_KEY = 'myos-authenticated';
const FINANCE_REFRESH_KEY = 'finance-needs-refresh';
const DEFAULT_GREETING_NAME = 'there';
const PAGE_ROUTES = {
  dashboard: '/',
  personal: '/personal/',
  education: '/education/',
  finance: '/finance/',
  media: '/media/',
  bucket: '/bucket/',
  projects: '/projects/',
  diary: '/diary/',
  reminders: '/reminders/',
  calendar: '/calendar/',
  settings: '/settings/',
};
const FORM_SAVE_DEBOUNCE_MS = 700;
const NOTIFICATION_PANEL_LIMIT = 6;

function debounce(fn, delay = 250) {
  let timer;
  function debounced(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  }
  debounced.cancel = () => clearTimeout(timer);
  return debounced;
}

const appState = {
  tasks: [],
  diaryEntries: [],
  profileDisplayName: '',
};

const remindersState = {
  isLoading: false,
  tasks: [],
  reminders: [],
  activeTab: 'tasks',
  taskFilter: 'all',
  selectedDate: '',
  calendarCursor: new Date(),
};

const diaryState = {
  entries: [],
  pagination: {
    page: 1,
    total_pages: 1,
    total_items: 0,
    has_next: false,
    has_prev: false,
  },
  isLoading: false,
};

const financeState = {
  metrics: [],
  ledger: [],
  budgets: [],
  goals: [],
  applicationCosts: [],
  projectBudgets: [],
  recurringForecast: [],
  alerts: [],
  insights: [],
  categories: [],
  charts: {},
  chartInstances: {},
  isSetup: false,
  pagination: {
    page: 1,
    page_size: 12,
    total_pages: 1,
    total_items: 0,
  },
  filters: {
    q: '',
    date_from: '',
    date_to: '',
    category_id: '',
    account: '',
    tx_type: '',
    amount_min: '',
    amount_max: '',
    sort: 'date_desc',
    page: 1,
    page_size: 12,
  },
};

const educationState = {
  levels: [],
  exams: [],
  documents: [],
  scholarships: [],
  deadlineAlerts: [],
  filters: {
    q: '',
    status: '',
  },
  pendingDocumentFile: null,
  isSetup: false,
};

const projectsState = {
  rows: [],
  chartInstances: {},
  isSetup: false,
};

const personalState = {
  identity: {},
  contact: {},
  identityDocuments: {},
  uploadedFiles: [],
  digitalAccounts: [],
  socialProfiles: {},
  passwordReferences: [],
  completionScore: 0,
  stepStatus: [],
  suggestions: [],
  expiryAlerts: [],
  tags: {
    languages: [],
    additionalEmails: [],
    otherPhones: [],
  },
  filters: {
    accountSearch: '',
    accountPlatform: '',
  },
  pendingProfilePhoto: null,
  pendingIdentityFile: null,
  currentStep: 1,
  isSetup: false,
  autosaveTimers: {},
};

let pageFormSaveTimer = null;
let pendingUploadContext = null;
let revealObserver = null;
let numberObserver = null;
let progressObserver = null;
let scrollSpyObserver = null;
let idleTimer = null;
let globalSearchAbortController = null;
const dashboardCalendarState = {
  cursor: new Date(),
  selectedDate: '',
  events: [],
  loadedKey: '',
  isLoading: false,
};
const DASHBOARD_EVENT_DATES = new Set();
const uiState = {
  commandItems: [],
  commandSelection: -1,
  searchItems: [],
  shortcutGroup: '',
  shortcutGroupTimer: null,
};
const scrollSpyMap = new Map();

function isAuthenticated() {
  try {
    return localStorage.getItem(AUTH_STORAGE_KEY) === '1';
  } catch (err) {
    return false;
  }
}

function isAppUnlocked() {
  const app = document.getElementById('app');
  return Boolean(app && app.classList.contains('show'));
}

function setAuthenticatedState(value) {
  try {
    if (value) localStorage.setItem(AUTH_STORAGE_KEY, '1');
    else localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch (err) {
    // Ignore storage issues and continue with session-only behavior.
  }
}

function openApp() {
  const app = document.getElementById('app');
  const overlay = document.getElementById('auth-overlay');
  if (overlay) {
    overlay.classList.add('hide');
    setTimeout(() => {
      overlay.style.display = 'none';
    }, 280);
  }
  if (app) app.classList.add('show');
  closeSidebarDrawer();
  refreshVisualEnhancements();
}

function closeApp() {
  const app = document.getElementById('app');
  const overlay = document.getElementById('auth-overlay');
  if (app) app.classList.remove('show');
  closeSidebarDrawer();
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.classList.remove('hide');
  }
}

function getActivePage() {
  return document.body?.dataset?.page || 'dashboard';
}

function getMainContentSwap() {
  return document.getElementById('main-content-swap');
}

function getCurrentPageRoot(root = document) {
  if (root instanceof Element && root.matches('.page-content[data-page-key]')) return root;
  return root.querySelector?.('.page-content[data-page-key]') || document.querySelector('.page-content[data-page-key]');
}

function normalizeInternalUrl(url) {
  if (!url) return null;
  try {
    const resolved = new URL(url, window.location.origin);
    if (resolved.origin !== window.location.origin) return null;
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch (err) {
    return null;
  }
}

function getRequestPath(url) {
  const normalized = normalizeInternalUrl(url);
  if (!normalized) return null;
  const [requestPath] = normalized.split('#');
  return requestPath || '/';
}

function enhanceInAppNavLinks(root = document) {
  if (!window.htmx) return;
  const links = [];
  if (root instanceof Element && root.matches('a[data-inapp-nav="true"]')) links.push(root);
  root.querySelectorAll?.('a[data-inapp-nav="true"]').forEach((link) => links.push(link));

  links.forEach((link) => {
    const href = link.getAttribute('href');
    const requestPath = getRequestPath(href);
    const pushUrl = normalizeInternalUrl(href);
    if (!href || !requestPath || !pushUrl || link.hasAttribute('download')) return;
    link.setAttribute('hx-get', requestPath);
    link.setAttribute('hx-target', '#main-content-swap');
    link.setAttribute('hx-push-url', pushUrl);
    link.setAttribute('hx-swap', 'innerHTML transition:true');
    link.setAttribute('hx-indicator', '#page-progress-bar');
    if (link.dataset.hxEnhanced === '1') return;
    link.dataset.hxEnhanced = '1';
    window.htmx.process(link);
  });
}

function navigateInApp(url) {
  const normalized = normalizeInternalUrl(url);
  const requestPath = getRequestPath(url);
  const swapTarget = getMainContentSwap();
  if (!normalized || !requestPath || !window.htmx || !swapTarget) {
    if (url) window.location.href = url;
    return;
  }

  const tempLink = document.createElement('a');
  tempLink.href = normalized;
  tempLink.dataset.inappNav = 'true';
  tempLink.hidden = true;
  document.body.appendChild(tempLink);
  enhanceInAppNavLinks(tempLink);
  tempLink.click();
  window.setTimeout(() => tempLink.remove(), 0);
}

function syncActiveNavigation() {
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item[href], .mobile-bottom-link[href], .sidebar-footer-link[href]').forEach((link) => {
    const href = link.getAttribute('href');
    const normalized = normalizeInternalUrl(href);
    if (!href || href === '#' || !normalized) return;
    const hrefPath = normalized.split('#')[0];
    const isActive = currentPath === hrefPath || (hrefPath !== '/' && currentPath.startsWith(hrefPath));
    link.classList.toggle('active', isActive);
  });
}

function updateShellPageState(root = document) {
  const page = getCurrentPageRoot(root);
  if (!page) return;
  const pageKey = page.dataset.pageKey || 'dashboard';
  const pageTitle = page.dataset.pageTitle || pageKey.charAt(0).toUpperCase() + pageKey.slice(1);
  document.body.dataset.page = pageKey;
  const title = document.getElementById('topbar-page-title');
  if (title) title.textContent = pageTitle;
  syncActiveNavigation();
}

function escapeSelectorValue(value) {
  if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(value);
  return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
}

function updateClock() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const dateStr = now.toLocaleDateString('en-KE', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const el = (id) => document.getElementById(id);

  if (el('clock-display')) el('clock-display').textContent = timeStr;
  if (el('clock-date')) el('clock-date').textContent = dateStr;
  if (el('big-clock')) el('big-clock').textContent = timeStr;
  if (el('big-date')) el('big-date').textContent = dateStr;

  const h = now.getHours();
  const greet = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  const displayName = (appState.profileDisplayName || '').trim() || DEFAULT_GREETING_NAME;
  const greetingLine = `${greet}, ${displayName}!`;
  if (el('greeting-text')) el('greeting-text').textContent = greetingLine;
}

function switchAuth(mode) {
  const isLogin = mode === 'login';
  document.querySelectorAll('.auth-tab').forEach((t, i) => {
    t.classList.toggle('active', isLogin ? i === 0 : i === 1);
  });
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const otpSection = document.getElementById('otp-section');
  const tabsBar = document.getElementById('auth-tabs-bar');

  if (loginForm) loginForm.classList.toggle('active', isLogin);
  if (signupForm) signupForm.classList.toggle('active', !isLogin);
  if (otpSection) otpSection.classList.remove('active');
  if (tabsBar) tabsBar.style.display = 'flex';
}

function withButtonLoading(btn, text, cb) {
  if (!btn) {
    cb();
    return;
  }

  const original = btn.innerHTML;
  btn.disabled = true;
  btn.classList.add('is-loading');
  btn.innerHTML = text;

  setTimeout(() => {
    cb();
    btn.disabled = false;
    btn.classList.remove('is-loading');
    btn.innerHTML = original;
  }, 300);
}

function handleSignup() {
  const emailInput = document.getElementById('signup-email');
  const email = emailInput ? emailInput.value.trim() : '';
  if (!email || !email.includes('@')) {
    showToast('Please enter a valid email address');
    if (emailInput) emailInput.focus();
    return;
  }
  const triggerBtn = document.activeElement && document.activeElement.tagName === 'BUTTON'
    ? document.activeElement
    : null;

  withButtonLoading(triggerBtn, 'Sending OTP...', () => {
    const otpEmailDisplay = document.getElementById('otp-email-display');
    const signupForm = document.getElementById('signup-form');
    const otpSection = document.getElementById('otp-section');
    const tabsBar = document.getElementById('auth-tabs-bar');

    if (otpEmailDisplay) otpEmailDisplay.textContent = email;
    if (signupForm) signupForm.classList.remove('active');
    if (otpSection) otpSection.classList.add('active');
    if (tabsBar) tabsBar.style.display = 'none';
    const firstOtp = document.querySelector('.otp-digit');
    if (firstOtp) firstOtp.focus();
    showToast('OTP sent successfully');
  });
}

function otpNext(el) {
  el.value = el.value.replace(/\D/g, '');
  if (el.value.length === 1 && el.nextElementSibling) el.nextElementSibling.focus();
}

function otpVerify(el) {
  el.value = el.value.replace(/\D/g, '');
  if (el.value.length === 1) setTimeout(handleLogin, 300);
}

function getOtpCode() {
  return Array.from(document.querySelectorAll('.otp-digit')).map((d) => d.value).join('');
}

function handleLogin() {
  const code = getOtpCode();
  const otpSection = document.getElementById('otp-section');
  const inOtpMode = otpSection ? otpSection.classList.contains('active') : false;

  if (inOtpMode && code.length !== 6) {
    showToast('Please enter the full 6-digit OTP');
    return;
  }

  setAuthenticatedState(true);
  openApp();
  animateProgressBars();
  if (!isPersonalPage()) {
    setupPageFormPersistence();
  }
  loadUnlockedPageData();
  showToast('Welcome back');
}

function signOut() {
  setAuthenticatedState(false);
  closeApp();
  switchAuth('login');
  document.querySelectorAll('.otp-digit').forEach((d) => {
    d.value = '';
  });
  showToast('Signed out');
}

function showPage(id) {
  const route = PAGE_ROUTES[id];
  if (route) navigateInApp(route);
}

function loadUnlockedPageData() {
  loadBootstrapData();
  if (!isPersonalPage()) {
    loadPageFormData();
  }
  loadUploadedFilesForPage();
  loadDashboardEducationAlerts();
  if (isPersonalPage()) {
    setupPersonalPage();
  } else if (isFinancePage()) {
    setupFinancePage();
  } else if (isDiaryPage()) {
    setupDiaryPage();
  } else if (isRemindersPage()) {
    setupRemindersPage();
  } else if (getActivePage() === 'education') {
    setupEducationPage();
  } else if (getActivePage() === 'projects') {
    setupProjectsPage();
  } else {
    setTimeout(initCharts, 80);
  }
  requestAnimationFrame(() => refreshVisualEnhancements());
}

function goPersonalStep(n) {
  const target = Number(n || 1);
  const clamped = Math.min(6, Math.max(1, target));
  personalState.currentStep = clamped;

  for (let i = 1; i <= 6; i += 1) {
    const panel = document.getElementById(`personal-panel-${i}`);
    if (panel) panel.classList.toggle('active', i === clamped);
  }
  renderPersonalStepStatus();
}

function switchTab(prefix, id) {
  const panel = document.getElementById(`${prefix}-${id}`);
  if (!panel) return;

  const siblings = panel.parentElement.querySelectorAll(':scope > .tab-panel');
  const activePanel = panel.parentElement.querySelector(':scope > .tab-panel.active');
  if (activePanel && activePanel !== panel) {
    activePanel.style.opacity = '0';
    activePanel.style.transform = 'translateX(-8px)';
    setTimeout(() => {
      activePanel.classList.remove('active');
      activePanel.style.opacity = '';
      activePanel.style.transform = '';
    }, 220);
  }

  siblings.forEach((p) => {
    if (p !== panel) p.classList.remove('active');
  });
  panel.classList.add('active');
  panel.style.opacity = '0';
  panel.style.transform = 'translateX(8px)';
  requestAnimationFrame(() => {
    panel.style.opacity = '1';
    panel.style.transform = 'translateX(0)';
  });
  setTimeout(() => {
    panel.style.opacity = '';
    panel.style.transform = '';
  }, 220);

  let prev = panel.previousElementSibling;
  while (prev && !prev.classList.contains('tab-bar')) prev = prev.previousElementSibling;

  if (prev && prev.classList.contains('tab-bar')) {
    prev.querySelectorAll('.tab-btn').forEach((btn) => {
      const onclick = btn.getAttribute('onclick') || '';
      btn.classList.toggle('active', onclick.includes(`'${id}'`));
    });
  }

  setTimeout(setupScrollSpy, 80);

  if (prefix === 'fin') {
    if (id !== 'analytics') return;
    setTimeout(renderFinanceCharts, 40);
    setTimeout(refreshVisualEnhancements, 60);
    return;
  }
  if (prefix === 'prj') {
    if (id !== 'analytics') return;
    setTimeout(() => renderProjectsCharts(projectsState.rows), 40);
    setTimeout(refreshVisualEnhancements, 60);
    return;
  }
  setTimeout(initCharts, 40);
  setTimeout(refreshVisualEnhancements, 60);
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : '';
}

function getCsrfToken() {
  return getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function apiRequest(path, method = 'GET', payload = null) {
  const options = {
    method,
    headers: {
      Accept: 'application/json',
    },
    credentials: 'same-origin',
  };

  if (payload !== null) {
    options.headers['Content-Type'] = 'application/json';
    options.headers['X-CSRFToken'] = getCsrfToken();
    options.body = JSON.stringify(payload);
  }

  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

async function apiRequestForm(path, formData) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: formData,
    credentials: 'same-origin',
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'Upload failed');
  }
  return data;
}

function getPageContainer() {
  const activePage = getActivePage();
  return document.getElementById(`page-${activePage}`) || document.querySelector('.page-content');
}

function collectPageFormData() {
  const container = getPageContainer();
  if (!container) return {};

  const values = {};
  container.querySelectorAll('input, textarea, select').forEach((field) => {
    const key = field.id || field.name;
    if (!key) return;
    if (field.closest('#auth-overlay')) return;
    if (field.type === 'button' || field.type === 'submit' || field.type === 'file') return;

    if (field.type === 'checkbox') {
      values[key] = field.checked;
      return;
    }

    if (field.type === 'radio') {
      if (field.checked) values[key] = field.value;
      return;
    }

    values[key] = field.value;
  });

  return values;
}

function applyPageFormData(data) {
  if (!data || typeof data !== 'object') return;
  const container = getPageContainer();
  if (!container) return;

  Object.entries(data).forEach(([key, value]) => {
    const escapedKey = escapeSelectorValue(key);
    const field = container.querySelector(`#${escapedKey}`) || container.querySelector(`[name="${escapedKey}"]`);
    if (!field) return;
    if (field.type === 'checkbox') {
      field.checked = Boolean(value);
      return;
    }
    if (field.type === 'radio') {
      const group = container.querySelectorAll(`[name="${escapedKey}"]`);
      group.forEach((item) => {
        item.checked = item.value === value;
      });
      return;
    }
    field.value = value ?? '';
  });
}

async function savePageFormData() {
  if (!isAuthenticated()) return;
  const activePage = getActivePage();

  const data = collectPageFormData();
  try {
    await apiRequest(`/api/forms/${activePage}/save/`, 'POST', { data });
  } catch (err) {
    // Quiet autosave failures; critical saves still use explicit actions.
  }
}

async function loadPageFormData() {
  if (!isAuthenticated()) return;
  const activePage = getActivePage();
  try {
    const result = await apiRequest(`/api/forms/${activePage}/`);
    applyPageFormData(result.data);
  } catch (err) {
    // Ignore when no saved state or when page is still locked.
  }
}

function setupPageFormPersistence() {
  const container = getPageContainer();
  if (!container) return;

  const scheduleSave = () => {
    clearTimeout(pageFormSaveTimer);
    pageFormSaveTimer = setTimeout(savePageFormData, FORM_SAVE_DEBOUNCE_MS);
  };

  container.querySelectorAll('input, textarea, select').forEach((field) => {
    if (field.closest('#auth-overlay')) return;
    field.addEventListener('input', scheduleSave);
    field.addEventListener('change', scheduleSave);
  });
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIdx = 0;
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024;
    unitIdx += 1;
  }
  return `${size.toFixed(size >= 10 || unitIdx === 0 ? 0 : 1)} ${units[unitIdx]}`;
}

function renderUploadLists(files) {
  const grouped = {};
  files.forEach((file) => {
    if (!grouped[file.field_key]) grouped[file.field_key] = [];
    grouped[file.field_key].push(file);
  });

  document.querySelectorAll('[data-upload-list-for]').forEach((container) => {
    const fieldKey = container.dataset.uploadListFor;
    const fieldFiles = grouped[fieldKey] || [];
    container.innerHTML = '';

    if (!fieldFiles.length) {
      const empty = document.createElement('div');
      empty.className = 'muted-note';
      empty.textContent = 'No files uploaded yet';
      container.appendChild(empty);
      return;
    }

    fieldFiles.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'upload-file-item';

      const link = document.createElement('a');
      link.href = item.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = item.original_name || 'Uploaded file';

      const meta = document.createElement('span');
      meta.className = 'upload-file-meta';
      meta.textContent = formatBytes(item.file_size);

      row.appendChild(link);
      row.appendChild(meta);
      container.appendChild(row);
    });
  });
}

async function loadUploadedFilesForPage() {
  const uploadTargets = document.querySelectorAll('[data-upload-list-for]');
  if (!uploadTargets.length || !isAuthenticated()) return;

  try {
    const activePage = getActivePage();
    const result = await apiRequest(`/api/uploads/${activePage}/`);
    renderUploadLists(result.files || []);
  } catch (err) {
    showToast(err.message || 'Failed to load uploaded files');
  }
}

async function uploadSelectedFile(file, context) {
  if (!file || !context) return;
  const { page, key, label } = context;
  const payload = new FormData();
  payload.append('file', file);
  payload.append('label', label || '');

  try {
    await apiRequestForm(`/api/uploads/${page}/${key}/`, payload);
    showToast('File uploaded successfully');
    loadUploadedFilesForPage();
  } catch (err) {
    showToast(err.message || 'Upload failed');
  }
}

function setupUploadZones() {
  const uploadInput = document.getElementById('global-upload-input');
  if (!uploadInput) return;

  document.querySelectorAll('.upload-zone[data-upload-key]').forEach((zone) => {
    if (zone.dataset.uploadZoneReady === '1') return;
    zone.dataset.uploadZoneReady = '1';
    zone.addEventListener('click', () => {
      pendingUploadContext = {
        page: getActivePage(),
        key: zone.dataset.uploadKey,
        label: zone.dataset.uploadLabel || '',
      };
      uploadInput.value = '';
      uploadInput.click();
    });
  });

  if (uploadInput.dataset.uploadInputReady === '1') return;
  uploadInput.dataset.uploadInputReady = '1';
  uploadInput.addEventListener('change', () => {
    const [file] = uploadInput.files || [];
    if (!file || !pendingUploadContext) return;
    uploadSelectedFile(file, pendingUploadContext);
    pendingUploadContext = null;
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function sameDateKey(left, right) {
  return Boolean(left && right && String(left) === String(right));
}

function getTodayISO() {
  return toDateKey(new Date());
}

function formatShortDate(value) {
  if (!value) return 'No date';
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-KE', { month: 'short', day: 'numeric' });
}

function taskTag(task = {}) {
  return (task.focus_area || task.tag || 'Personal').trim() || 'Personal';
}

function taskMatchesFilter(task = {}, filter = 'all') {
  if (!filter || filter === 'all') return true;
  return taskTag(task).toLowerCase() === filter.toLowerCase();
}

function priorityClass(task = {}) {
  return `priority-${cssToken(task.priority || 'medium')}`;
}

function taskRowHtml(task, { dashboard = false } = {}) {
  const tag = taskTag(task);
  const dueLabel = task.due_label || formatShortDate(task.due_date);
  return `
    <div class="${dashboard ? 'task-item' : 'reminder-task-row'} ${task.is_done ? 'is-completed' : ''}" data-task-row data-task-date="${escapeHtml(task.due_date || '')}" data-task-tag="${escapeHtml(tag.toLowerCase())}">
      <button class="${dashboard ? 'task-check' : 'reminder-check-btn'} ${task.is_done ? 'done' : ''}" type="button" data-task-id="${task.id}" ${dashboard ? 'onclick="toggleTask(this)"' : `data-reminder-task-toggle="${task.id}"`} aria-label="${task.is_done ? 'Mark task open' : 'Mark task complete'}">
        ${task.is_done ? CHECK_ICON_SMALL : ''}
      </button>
      <div class="task-row-main">
        <div class="${dashboard ? 'task-text' : 'task-title'} ${task.is_done ? 'done' : ''}">${escapeHtml(task.title || 'Untitled task')}</div>
        <div class="task-meta">
          <span class="task-chip">${escapeHtml(tag)}</span>
          <span class="task-chip ${priorityClass(task)}">${escapeHtml(task.priority_label || 'Medium')}</span>
          <span>${escapeHtml(dueLabel)}</span>
        </div>
      </div>
    </div>`;
}

function renderTasks(tasks) {
  appState.tasks = tasks.slice();
  const taskList = document.getElementById('task-list');
  if (!taskList) {
    updateTaskProgress();
    return;
  }

  const selectedDate = dashboardCalendarState.selectedDate;
  const visibleTasks = selectedDate
    ? tasks.filter((task) => sameDateKey(task.due_date, selectedDate))
    : tasks.filter((task) => !task.is_done && ['today', 'overdue'].includes(task.due_state)).slice(0, 5);
  const fallbackTasks = visibleTasks.length ? visibleTasks : tasks.filter((task) => !task.is_done).slice(0, 5);

  taskList.innerHTML = fallbackTasks.length
    ? fallbackTasks.map((task) => taskRowHtml(task, { dashboard: true })).join('')
    : '<div class="table-empty">No tasks created yet.</div>';

  const label = document.getElementById('dashboard-task-filter-label');
  if (label) {
    label.textContent = selectedDate
      ? `Tasks and reminders for ${formatDisplayDate(selectedDate)}.`
      : 'Tasks due today or selected on the calendar.';
  }

  const taskMetric = document.querySelector('.metric-link-card--tasks');
  if (taskMetric) {
    const value = taskMetric.querySelector('.metric-value');
    const trend = taskMetric.querySelector('.metric-trend');
    const done = tasks.filter((task) => task.is_done).length;
    if (value) value.textContent = `${done} task${done === 1 ? '' : 's'}`;
    if (trend) trend.textContent = tasks.length ? `${tasks.length} total tasks tracked` : 'No task history yet';
  }

  updateTaskProgress();
  renderDashboardSelectedDateAgenda();
}

function updateDashboardDiaryMetric(streak = {}) {
  const diaryMetric = document.querySelector('.metric-link-card--diary');
  if (!diaryMetric) return;
  const value = diaryMetric.querySelector('.metric-value');
  const trend = diaryMetric.querySelector('.metric-trend');
  const currentStreak = Number(streak.current_streak || 0);
  const totalEntries = Number(streak.total_entries || 0);
  const longestStreak = Number(streak.longest_streak || 0);
  if (value) value.textContent = `${currentStreak} day${currentStreak === 1 ? '' : 's'}`;
  if (trend) {
    trend.textContent = totalEntries
      ? `${totalEntries} entr${totalEntries === 1 ? 'y' : 'ies'} captured${longestStreak ? ` • longest ${longestStreak} day${longestStreak === 1 ? '' : 's'}` : ''}`
      : 'No entries yet';
  }
}

function updateDashboardDiaryPreview(entries = []) {
  const preview = document.querySelector('.diary-preview');
  if (!preview) return;
  if (!entries.length) {
    preview.innerHTML = '<div class="diary-date">No entries yet</div>Create your first diary entry to see a preview here.';
    return;
  }

  const latest = entries[0];
  const parsedDate = latest.entry_date ? new Date(latest.entry_date) : null;
  const dateLabel = parsedDate && !Number.isNaN(parsedDate.getTime())
    ? parsedDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : (latest.entry_date || 'Recent');
  const previewText = latest.content
    ? `${escapeHtml(latest.content.slice(0, 160))}${latest.content.length > 160 ? '...' : ''}`
    : 'No content yet...';
  preview.innerHTML = `<div class="diary-date">${escapeHtml(dateLabel)}</div>${previewText}`;
}

function updateTaskProgress() {
  const total = appState.tasks.length || 0;
  const done = appState.tasks.filter((t) => t.is_done).length;
  const percent = total ? Math.round((done / total) * 100) : 0;

  const textEl = document.getElementById('task-progress-text');
  const percentEl = document.getElementById('task-progress-percent');
  const fillEl = document.getElementById('task-progress-fill');

  if (textEl) textEl.textContent = `${done} / ${total} tasks done`;
  if (percentEl) percentEl.textContent = `${percent}%`;
  if (fillEl) fillEl.style.width = `${percent}%`;
}

async function toggleTask(el) {
  const taskId = Number(el.dataset.taskId || 0);
  const row = el.closest('[data-task-row]') || el.closest('.task-item');
  const txt = row?.querySelector('.task-text, .task-title') || el.nextElementSibling;

  if (!taskId) {
    el.classList.toggle('done');
    if (txt) txt.classList.toggle('done');
    if (row) row.classList.toggle('is-completed', el.classList.contains('done'));
    el.innerHTML = el.classList.contains('done') ? CHECK_ICON_SMALL : '';
    return;
  }

  try {
    const res = await apiRequest(`/api/tasks/${taskId}/toggle/`, 'POST', {});
    const task = res.task;
    appState.tasks = appState.tasks.map((t) => (t.id === task.id ? task : t));
    el.classList.toggle('done', task.is_done);
    if (txt) txt.classList.toggle('done', task.is_done);
    if (row) row.classList.toggle('is-completed', task.is_done);
    el.innerHTML = task.is_done ? CHECK_ICON_SMALL : '';
    renderTasks(appState.tasks);
    updateTaskProgress();
  } catch (err) {
    showToast(err.message || 'Failed to update task');
  }
}

function cssToken(value) {
  return String(value || 'none').toLowerCase().replace(/[^a-z0-9_-]/g, '-');
}

function serializeForm(form) {
  const payload = {};
  new FormData(form).forEach((value, key) => {
    payload[key] = typeof value === 'string' ? value.trim() : value;
  });
  return payload;
}

function formatDisplayDate(value) {
  if (!value) return 'No date';
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-KE', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function setInputDefaultDate(input) {
  if (input && !input.value) input.value = getTodayISO();
}

function reminderEmpty(message) {
  return `<div class="table-empty">${escapeHtml(message)}</div>`;
}

function updateRemindersSummary(summary = {}) {
  const totalTasks = document.getElementById('reminders-total-tasks');
  const completedCount = document.getElementById('reminders-completed-count');
  const overdueCountEl = document.getElementById('reminders-overdue-count');
  const overdueCopy = document.getElementById('reminders-overdue-copy');
  const focusOpen = document.getElementById('reminders-focus-open');
  const focusCopy = document.getElementById('reminders-focus-copy');
  const completionRate = document.getElementById('reminders-completion-rate');
  const completionCopy = document.getElementById('reminders-completion-copy');
  const weekCopy = document.getElementById('reminders-week-copy');
  const banner = document.getElementById('reminders-overdue-banner');
  const bannerText = document.getElementById('reminders-overdue-banner-text');

  const overdueCount = Number(summary.overdue_count || 0);
  const focusOpenCount = Number(summary.focus_open_count || 0);
  const completedTotal = Number(summary.completed_count || 0);
  const completion = Number(summary.completion_rate || 0);
  const weekCount = Number(summary.this_week_count || 0);

  if (totalTasks) totalTasks.textContent = String(focusOpenCount + completedTotal);
  if (completedCount) completedCount.textContent = String(completedTotal);
  if (overdueCountEl) overdueCountEl.textContent = String(overdueCount);
  if (overdueCopy) overdueCopy.textContent = String(overdueCount);
  if (focusOpen) focusOpen.textContent = String(focusOpenCount);
  if (focusCopy) focusCopy.textContent = String(focusOpenCount);
  if (completionRate) completionRate.textContent = `${completion}%`;
  if (completionCopy) completionCopy.textContent = String(completedTotal);
  if (weekCopy) weekCopy.textContent = String(weekCount);
  if (banner) banner.classList.toggle('hidden', overdueCount === 0);
  if (bannerText) {
    bannerText.textContent = overdueCount
      ? `${overdueCount} reminder or TODO item${overdueCount === 1 ? '' : 's'} slipped past the due date.`
      : 'You are all caught up.';
  }
}

function renderReminderTasks(tasks = []) {
  remindersState.tasks = tasks.slice();
  applyRemindersTaskView();
  renderRemindersCalendar();
}

function filteredReminderTasks() {
  return remindersState.tasks.filter((task) => {
    const matchesFilter = taskMatchesFilter(task, remindersState.taskFilter);
    const matchesDate = remindersState.selectedDate ? sameDateKey(task.due_date, remindersState.selectedDate) : true;
    return matchesFilter && matchesDate;
  });
}

function renderTaskGroup(containerId, tasks = [], emptyText) {
  const list = document.getElementById(containerId);
  if (!list) return;
  list.innerHTML = tasks.length
    ? tasks.map((task) => taskRowHtml(task)).join('')
    : reminderEmpty(emptyText);
}

function applyRemindersTaskView() {
  const tasks = filteredReminderTasks();
  const todayTitle = document.getElementById('reminders-today-title');
  const selectedLabel = document.getElementById('reminders-selected-date-label');
  const selectedDate = remindersState.selectedDate;
  const today = getTodayISO();

  const todayTasks = selectedDate
    ? tasks.filter((task) => sameDateKey(task.due_date, selectedDate) && !task.is_done)
    : tasks.filter((task) => !task.is_done && (task.due_state === 'today' || task.due_state === 'overdue' || sameDateKey(task.due_date, today)));
  const upcomingTasks = selectedDate
    ? []
    : tasks.filter((task) => !task.is_done && !todayTasks.some((todayTask) => todayTask.id === task.id));
  const completedTasks = tasks.filter((task) => task.is_done);

  renderTaskGroup('reminders-today-list', todayTasks, selectedDate ? 'No open tasks on this date.' : 'No tasks due today.');
  renderTaskGroup('reminders-upcoming-list', upcomingTasks, 'No upcoming tasks.');
  renderTaskGroup('reminders-completed-task-list', completedTasks, 'No completed tasks yet.');

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value);
  };
  setText('reminders-today-count', todayTasks.length);
  setText('reminders-upcoming-count', upcomingTasks.length);
  setText('reminders-completed-task-count', completedTasks.length);
  setText('reminders-total-tasks', remindersState.tasks.length);
  setText('reminders-completed-count', remindersState.tasks.filter((task) => task.is_done).length);
  setText('reminders-overdue-count', remindersState.tasks.filter((task) => !task.is_done && task.due_state === 'overdue').length);

  if (todayTitle) todayTitle.textContent = selectedDate ? formatDisplayDate(selectedDate) : 'Today';
  if (selectedLabel) {
    selectedLabel.textContent = selectedDate
      ? `Showing items for ${formatDisplayDate(selectedDate)}.`
      : 'Tasks and reminders by day.';
  }
}

function renderReminderTimeline(reminders = []) {
  const list = document.getElementById('reminders-timeline');
  if (!list) return;

  const visibleReminders = remindersState.selectedDate
    ? reminders.filter((reminder) => sameDateKey(reminder.reminder_date, remindersState.selectedDate))
    : reminders;
  const subtitle = document.getElementById('reminders-timeline-subtitle');
  if (subtitle) {
    subtitle.textContent = remindersState.selectedDate
      ? `Reminders scheduled for ${formatDisplayDate(remindersState.selectedDate)}.`
      : 'Upcoming reminders arranged by urgency.';
  }

  if (!visibleReminders.length) {
    list.innerHTML = reminderEmpty('No reminders scheduled yet. Capture one above to start the flow.');
    return;
  }

  list.innerHTML = visibleReminders.map((reminder) => {
    const state = cssToken(reminder.due_state);
    return `
      <article class="reminder-timeline-item reminder-state-${state}">
        <div class="reminder-status-dot" aria-hidden="true"></div>
        <div class="reminder-item-copy">
          <div class="reminder-item-title">${escapeHtml(reminder.title || 'Scheduled reminder')}</div>
          <div class="reminder-item-meta">
            <span>${escapeHtml(reminder.due_label || reminder.scheduled_label || 'Scheduled')}</span>
            <span>${escapeHtml(reminder.channel_label || 'In App')}</span>
            <span>${escapeHtml(reminder.cadence_label || 'One Time')}</span>
          </div>
          ${reminder.details ? `<p class="reminder-item-details">${escapeHtml(reminder.details)}</p>` : ''}
        </div>
        <div class="reminder-item-actions">
          <button class="icon-action-btn" type="button" data-reminder-toggle="${reminder.id}" title="Mark complete" aria-label="Mark reminder complete"><i class="fas fa-check"></i></button>
          <button class="icon-action-btn danger" type="button" data-reminder-delete="${reminder.id}" title="Delete" aria-label="Delete reminder"><i class="fas fa-trash"></i></button>
        </div>
      </article>`;
  }).join('');
}

function renderCompletedReminders(reminders = []) {
  const list = document.getElementById('reminders-completed-list');
  if (!list) return;

  if (!reminders.length) {
    list.innerHTML = reminderEmpty('No completed reminders yet.');
    return;
  }

  list.innerHTML = reminders.map((reminder) => `
    <article class="reminder-completed-item">
      <div class="reminder-item-copy">
        <div class="reminder-item-title">${escapeHtml(reminder.title || 'Completed reminder')}</div>
        <div class="reminder-item-meta">
          <span>Completed</span>
          <span>${escapeHtml(reminder.scheduled_label || formatDisplayDate(reminder.reminder_date))}</span>
        </div>
      </div>
      <div class="reminder-item-actions">
        <button class="icon-action-btn" type="button" data-reminder-toggle="${reminder.id}" title="Restore" aria-label="Restore reminder"><i class="fas fa-rotate-left"></i></button>
        <button class="icon-action-btn danger" type="button" data-reminder-delete="${reminder.id}" title="Delete" aria-label="Delete reminder"><i class="fas fa-trash"></i></button>
      </div>
    </article>
  `).join('');
}

function renderReminderAgenda(reminders = []) {
  const list = document.getElementById('reminders-agenda-list');
  if (!list) return;
  const visibleReminders = remindersState.selectedDate
    ? reminders.filter((reminder) => sameDateKey(reminder.reminder_date, remindersState.selectedDate))
    : reminders;

  if (!visibleReminders.length) {
    list.innerHTML = reminderEmpty('No agenda items queued.');
    return;
  }

  list.innerHTML = visibleReminders.map((reminder) => `
    <div class="reminders-agenda-item">
      <span class="reminders-agenda-date">${escapeHtml(reminder.scheduled_label || formatDisplayDate(reminder.reminder_date))}</span>
      <span class="reminders-agenda-title">${escapeHtml(reminder.title || 'Scheduled reminder')}</span>
    </div>
  `).join('');
}

function renderReminderBreakdown(containerId, rows = [], emptyText) {
  const list = document.getElementById(containerId);
  if (!list) return;

  if (!rows.length) {
    list.innerHTML = reminderEmpty(emptyText);
    return;
  }

  list.innerHTML = rows.map((row) => `
    <div class="reminders-breakdown-row">
      <span>${escapeHtml(row.label || 'Other')}</span>
      <strong>${Number(row.count || 0)}</strong>
    </div>
  `).join('');
}

function remindersCalendarKey() {
  const focus = remindersState.calendarCursor;
  return `${focus.getFullYear()}-${String(focus.getMonth() + 1).padStart(2, '0')}`;
}

function remindersEventsForDate(dateKey) {
  if (!dateKey) return [];
  const tasks = remindersState.tasks
    .filter((task) => sameDateKey(task.due_date, dateKey))
    .map((task) => ({ type: 'task', title: task.title, is_done: task.is_done }));
  const reminders = remindersState.reminders
    .filter((reminder) => sameDateKey(reminder.reminder_date, dateKey))
    .map((reminder) => ({ type: 'reminder', title: reminder.title, is_done: reminder.is_completed }));
  return [...tasks, ...reminders];
}

function renderRemindersCalendar() {
  const monthLabel = document.getElementById('reminders-calendar-month');
  const grid = document.getElementById('reminders-calendar-grid');
  if (!monthLabel || !grid) return;

  const focus = remindersState.calendarCursor;
  const year = focus.getFullYear();
  const month = focus.getMonth();
  const firstDay = new Date(year, month, 1);
  const startingWeekday = firstDay.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;

  monthLabel.textContent = firstDay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  let html = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
    .map((name) => `<div class="calendar-day-name">${name}</div>`)
    .join('');

  for (let i = 0; i < startingWeekday; i += 1) {
    const dayNum = daysInPrevMonth - startingWeekday + i + 1;
    html += `<div class="calendar-day other-month">${dayNum}</div>`;
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateObj = new Date(year, month, day);
    const dateKey = toDateKey(dateObj);
    const events = remindersEventsForDate(dateKey);
    const classes = ['calendar-day'];
    if (isCurrentMonth && day === today.getDate()) classes.push('today');
    if (events.length) classes.push('has-event');
    if (remindersState.selectedDate === dateKey) classes.push('is-selected');
    html += `<button class="${classes.join(' ')}" type="button" data-date="${dateKey}" data-reminders-calendar-date="${dateKey}" aria-label="Filter reminders for ${dateKey}">${day}</button>`;
  }

  const totalCells = startingWeekday + daysInMonth;
  const trailingDays = (7 - (totalCells % 7)) % 7;
  for (let i = 1; i <= trailingDays; i += 1) {
    html += `<div class="calendar-day other-month">${i}</div>`;
  }

  grid.innerHTML = html;
  grid.querySelectorAll('[data-reminders-calendar-date]').forEach((button) => {
    button.addEventListener('click', () => {
      remindersState.selectedDate = button.dataset.remindersCalendarDate || '';
      applyRemindersTaskView();
      renderReminderTimeline(remindersState.reminders.filter((reminder) => !reminder.is_completed));
      renderReminderAgenda(remindersState.reminders.filter((reminder) => !reminder.is_completed).slice(0, 5));
      renderRemindersCalendar();
    });
  });
}

function renderRemindersHub(data = {}) {
  remindersState.tasks = (data.tasks || data.focus_tasks || []).slice();
  remindersState.reminders = (data.all_reminders || [
    ...(data.upcoming_reminders || []),
    ...(data.completed_reminders || []),
  ]).slice();
  updateRemindersSummary(data.summary || {});
  renderReminderTasks(remindersState.tasks);
  renderReminderTimeline(remindersState.reminders.filter((reminder) => !reminder.is_completed));
  renderCompletedReminders(remindersState.reminders.filter((reminder) => reminder.is_completed));
  renderReminderAgenda((data.agenda || remindersState.reminders.filter((reminder) => !reminder.is_completed)).slice(0, 5));
  renderReminderBreakdown('reminders-channel-list', data.channels || [], 'No delivery channels in use yet.');
  renderReminderBreakdown('reminders-cadence-list', data.cadence || [], 'No recurring cadence configured yet.');
  renderRemindersCalendar();
  refreshVisualEnhancements();
}

async function loadRemindersHub({ silent = false } = {}) {
  if (!isRemindersPage() || remindersState.isLoading) return;
  remindersState.isLoading = true;
  try {
    const data = await apiRequest('/api/reminders/bootstrap/');
    renderRemindersHub(data);
    const page = document.getElementById('page-reminders');
    if (page) page.dataset.remindersLoaded = '1';
  } catch (err) {
    if (!silent) showToast(err.message || 'Could not load reminders');
  } finally {
    remindersState.isLoading = false;
  }
}

async function submitReminderForm(form, endpoint, successMessage) {
  const payload = serializeForm(form);
  try {
    await apiRequest(endpoint, 'POST', payload);
    form.reset();
    setInputDefaultDate(form.querySelector('input[type="date"]'));
    await loadRemindersHub();
    await loadBootstrapData();
    showToast(successMessage, 'success');
  } catch (err) {
    showToast(err.message || 'Could not save item');
  }
}

function setupRemindersPage() {
  if (!isRemindersPage()) return;
  const page = document.getElementById('page-reminders');
  if (!page) return;

  setInputDefaultDate(page.querySelector('#reminder-capture-form input[name="reminder_date"]'));
  setInputDefaultDate(page.querySelector('#reminders-task-form input[name="due_date"]'));

  if (page.dataset.remindersReady !== '1') {
    page.dataset.remindersReady = '1';

    const reminderForm = page.querySelector('#reminder-capture-form');
    if (reminderForm) {
      reminderForm.addEventListener('submit', (event) => {
        event.preventDefault();
        submitReminderForm(reminderForm, '/api/reminders/create/', 'Reminder saved');
      });
    }

    const taskForm = page.querySelector('#reminders-task-form');
    if (taskForm) {
      taskForm.addEventListener('submit', (event) => {
        event.preventDefault();
        submitReminderForm(taskForm, '/api/tasks/create/', 'TODO added');
      });
    }

    page.querySelectorAll('[data-reminders-tab]').forEach((button) => {
      button.addEventListener('click', () => {
        const tab = button.dataset.remindersTab || 'tasks';
        remindersState.activeTab = tab;
        page.querySelectorAll('[data-reminders-tab]').forEach((item) => {
          const isActive = item.dataset.remindersTab === tab;
          item.classList.toggle('active', isActive);
          item.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
        page.querySelectorAll('[data-reminders-panel]').forEach((panel) => {
          panel.classList.toggle('active', panel.dataset.remindersPanel === tab);
        });
      });
    });

    page.querySelectorAll('[data-reminders-tab-jump]').forEach((button) => {
      button.addEventListener('click', () => {
        page.querySelector(`[data-reminders-tab="${button.dataset.remindersTabJump}"]`)?.click();
      });
    });

    page.querySelectorAll('[data-task-filter]').forEach((button) => {
      button.addEventListener('click', () => {
        remindersState.taskFilter = button.dataset.taskFilter || 'all';
        page.querySelectorAll('[data-task-filter]').forEach((item) => {
          item.classList.toggle('active', item === button);
        });
        applyRemindersTaskView();
      });
    });

    page.querySelector('#reminders-calendar-prev')?.addEventListener('click', () => {
      remindersState.calendarCursor = new Date(
        remindersState.calendarCursor.getFullYear(),
        remindersState.calendarCursor.getMonth() - 1,
        1
      );
      renderRemindersCalendar();
    });

    page.querySelector('#reminders-calendar-next')?.addEventListener('click', () => {
      remindersState.calendarCursor = new Date(
        remindersState.calendarCursor.getFullYear(),
        remindersState.calendarCursor.getMonth() + 1,
        1
      );
      renderRemindersCalendar();
    });

    page.querySelector('#reminders-clear-date-filter')?.addEventListener('click', () => {
      remindersState.selectedDate = '';
      applyRemindersTaskView();
      renderReminderTimeline(remindersState.reminders.filter((reminder) => !reminder.is_completed));
      renderReminderAgenda(remindersState.reminders.filter((reminder) => !reminder.is_completed).slice(0, 5));
      renderRemindersCalendar();
    });

    page.addEventListener('click', async (event) => {
      const taskToggle = event.target.closest('[data-reminder-task-toggle]');
      const reminderToggle = event.target.closest('[data-reminder-toggle]');
      const reminderDelete = event.target.closest('[data-reminder-delete]');

      try {
        if (taskToggle) {
          await apiRequest(`/api/tasks/${taskToggle.dataset.reminderTaskToggle}/toggle/`, 'POST', {});
          await loadRemindersHub();
          await loadBootstrapData();
          return;
        }
        if (reminderToggle) {
          await apiRequest(`/api/reminders/${reminderToggle.dataset.reminderToggle}/toggle/`, 'POST', {});
          await loadRemindersHub();
          await loadBootstrapData();
          return;
        }
        if (reminderDelete) {
          await apiRequest(`/api/reminders/${reminderDelete.dataset.reminderDelete}/delete/`, 'POST', {});
          await loadRemindersHub();
          await loadBootstrapData();
        }
      } catch (err) {
        showToast(err.message || 'Could not update reminders');
      }
    });
  }

  loadRemindersHub({ silent: page.dataset.remindersLoaded === '1' });
}

function renderDiaryEntries(entries) {
  appState.diaryEntries = entries.slice();
  diaryState.entries = entries.slice();
  const container = document.getElementById('diary-past-entries');
  const loadMoreButton = document.getElementById('diary-load-more');
  if (!container) return;

  if (!entries.length) {
    container.innerHTML = '<div class="table-empty">No diary entries yet.</div>';
    if (loadMoreButton) loadMoreButton.classList.add('hidden');
    return;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  container.innerHTML = entries
    .map((entry) => {
      const date = new Date(entry.entry_date);
      const dateText = Number.isNaN(date.getTime())
        ? entry.entry_date
        : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      const preview = entry.content ? entry.content.slice(0, 80) : 'No content yet...';
      const diffDays = Number.isNaN(date.getTime())
        ? 999
        : Math.floor((todayStart - new Date(date.getFullYear(), date.getMonth(), date.getDate())) / 86400000);
      const recencyClass = diffDays === 0 ? 'is-today' : diffDays < 7 ? 'is-week' : 'is-older';
      const recencyLabel = diffDays === 0 ? 'Today' : diffDays < 7 ? 'This week' : 'Earlier';
      return `
        <article class="diary-entry-card ${recencyClass}">
          <div class="diary-entry-topline">
            <span class="diary-entry-date-badge ${recencyClass}">${escapeHtml(recencyLabel)}</span>
            <span class="diary-entry-date">${escapeHtml(dateText)}</span>
          </div>
          <div class="diary-entry-preview">${escapeHtml(preview)}${entry.content && entry.content.length > 80 ? '...' : ''}</div>
          <div class="diary-entry-footer"><span class="mood-badge">${escapeHtml(entry.mood || '🙂 Neutral')}</span></div>
        </article>`;
    })
    .join('');

  if (loadMoreButton) {
    loadMoreButton.classList.toggle('hidden', !diaryState.pagination.has_next);
    loadMoreButton.disabled = diaryState.isLoading;
    loadMoreButton.textContent = diaryState.isLoading ? 'Loading...' : 'Load More';
  }
}

async function saveDiaryEntry() {
  const main = document.getElementById('diary-main-text');
  const achievements = document.getElementById('diary-achievements');
  const lessons = document.getElementById('diary-lessons');
  const ideas = document.getElementById('diary-ideas');
  const selectedMood = document.querySelector('.mood-selector .mood-btn.selected');

  const payload = {
    mood: selectedMood ? selectedMood.textContent.trim() : '🙂 Neutral',
    content: main ? main.value.trim() : '',
    achievements: achievements ? achievements.value.trim() : '',
    lessons: lessons ? lessons.value.trim() : '',
    ideas: ideas ? ideas.value.trim() : '',
  };

  try {
    await apiRequest('/api/diary/save/', 'POST', payload);
    if (isDiaryPage()) {
      await Promise.all([loadDiaryEntriesPage(1), loadDiaryStreak()]);
    } else {
      await loadBootstrapData();
    }
    showToast('Entry saved');
  } catch (err) {
    showToast(err.message || 'Failed to save diary entry');
  }
}

async function saveProfileSettings() {
  const displayName = document.getElementById('settings-display-name');
  const email = document.getElementById('settings-email');
  const timezone = document.getElementById('settings-timezone');

  try {
    await apiRequest('/api/profile/save/', 'POST', {
      display_name: displayName ? displayName.value.trim() : '',
      email: email ? email.value.trim() : '',
      timezone: timezone ? timezone.value.trim() : '',
    });
    const newName = displayName ? displayName.value.trim() : '';
    appState.profileDisplayName = newName;
    const sidebarName = document.getElementById('sidebar-user-name');
    if (sidebarName) sidebarName.textContent = newName || 'User';
    updateClock();
    showToast('Settings saved');
  } catch (err) {
    showToast(err.message || 'Failed to save settings');
  }
}

async function saveNotificationSettings() {
  const payload = {
    scholarship_deadlines: Boolean(document.getElementById('notif-scholarship')?.checked),
    task_due_alerts: Boolean(document.getElementById('notif-tasks')?.checked),
    diary_prompt: Boolean(document.getElementById('notif-diary')?.checked),
    finance_alerts: Boolean(document.getElementById('notif-finance')?.checked),
  };

  try {
    await apiRequest('/api/notifications/save/', 'POST', payload);
    showToast('Notification preferences saved');
  } catch (err) {
    showToast(err.message || 'Failed to save notification settings');
  }
}

async function loadBootstrapData() {
  try {
    const data = await apiRequest('/api/bootstrap/');
    renderTasks(data.tasks || []);
    renderDiaryEntries(data.diary_entries || []);
    updateDashboardDiaryMetric(data.diary_streak || {});
    updateDashboardDiaryPreview(data.diary_entries || []);

    if (data.profile) {
      const displayName = document.getElementById('settings-display-name');
      const email = document.getElementById('settings-email');
      const timezone = document.getElementById('settings-timezone');
      const sidebarName = document.getElementById('sidebar-user-name');
      const sidebarEmail = document.getElementById('sidebar-user-email');
      if (displayName) displayName.value = data.profile.display_name || '';
      if (email) email.value = data.profile.email || '';
      if (timezone) timezone.value = data.profile.timezone || 'UTC';
      if (sidebarName) sidebarName.textContent = data.profile.display_name || 'User';
      if (sidebarEmail) sidebarEmail.textContent = data.profile.email || 'No email set';
      appState.profileDisplayName = data.profile.display_name || '';
      updateClock();
    }

    if (data.notifications) {
      const scholarship = document.getElementById('notif-scholarship');
      const tasks = document.getElementById('notif-tasks');
      const diary = document.getElementById('notif-diary');
      const finance = document.getElementById('notif-finance');
      if (scholarship) scholarship.checked = Boolean(data.notifications.scholarship_deadlines);
      if (tasks) tasks.checked = Boolean(data.notifications.task_due_alerts);
      if (diary) diary.checked = Boolean(data.notifications.diary_prompt);
      if (finance) finance.checked = Boolean(data.notifications.finance_alerts);
    }
  } catch (err) {
    showToast('Could not load saved data');
  }
}

function formatMoneyKES(value) {
  const num = Number(value || 0);
  return `KES ${num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getCurrentTheme() {
  try {
    const stored = localStorage.getItem('myos-theme');
    if (stored === 'dark' || stored === 'light') return stored;
  } catch (err) {
    // Ignore storage issues.
  }
  return 'light';
}

function applyTheme(theme) {
  const normalized = theme === 'dark' ? 'dark' : 'light';
  document.body.dataset.theme = normalized;
  try {
    localStorage.setItem('myos-theme', normalized);
  } catch (err) {
    // Ignore storage issues.
  }
  applyChartThemeDefaults();
}

function toggleTheme() {
  applyTheme(document.body.dataset.theme === 'dark' ? 'light' : 'dark');
  renderFinanceCharts();
}

function isFinancePage() {
  return getActivePage() === 'finance';
}

function isDiaryPage() {
  return getActivePage() === 'diary';
}

function isRemindersPage() {
  return getActivePage() === 'reminders';
}

function isBucketPage() {
  return getActivePage() === 'bucket';
}

function getFinanceNavItem() {
  return document.querySelector(`.sidebar .nav-item[href="${PAGE_ROUTES.finance}"]`);
}

function setFinanceRefreshIndicator(active) {
  const item = getFinanceNavItem();
  if (!item) return;
  item.classList.toggle('needs-refresh', Boolean(active));
  if (active) {
    if (item.dataset.prevTitle === undefined) {
      item.dataset.prevTitle = item.getAttribute('title') || '';
    }
    item.setAttribute('title', 'Finance has new updates');
  } else if (item.dataset.prevTitle !== undefined) {
    if (item.dataset.prevTitle) {
      item.setAttribute('title', item.dataset.prevTitle);
    } else {
      item.removeAttribute('title');
    }
    delete item.dataset.prevTitle;
  }
}

function hasFinanceNeedsRefresh() {
  try {
    return localStorage.getItem(FINANCE_REFRESH_KEY) === '1';
  } catch (err) {
    return false;
  }
}

function markFinanceNeedsRefresh() {
  try {
    localStorage.setItem(FINANCE_REFRESH_KEY, '1');
  } catch (err) {
    // Ignore storage issues.
  }
  setFinanceRefreshIndicator(true);
}

function clearFinanceNeedsRefresh() {
  try {
    localStorage.removeItem(FINANCE_REFRESH_KEY);
  } catch (err) {
    // Ignore storage issues.
  }
  setFinanceRefreshIndicator(false);
}

function financeApiGet(path, query = null) {
  if (query) {
    const params = new URLSearchParams(query);
    return apiRequest(`${path}?${params.toString()}`);
  }
  return apiRequest(path);
}

function financeApiPost(path, payload) {
  return apiRequest(path, 'POST', payload || {});
}

function readLedgerFiltersFromUI() {
  const getVal = (id) => (document.getElementById(id)?.value || '').trim();
  financeState.filters = {
    ...financeState.filters,
    q: getVal('ledger-search'),
    date_from: getVal('ledger-date-from'),
    date_to: getVal('ledger-date-to'),
    category_id: getVal('ledger-category-filter'),
    account: getVal('ledger-account-filter'),
    tx_type: getVal('ledger-type-filter'),
    amount_min: getVal('ledger-amount-min'),
    amount_max: getVal('ledger-amount-max'),
    sort: getVal('ledger-sort') || 'date_desc',
  };
}

function updateLedgerFilterUI() {
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value || '';
  };
  setVal('ledger-search', financeState.filters.q);
  setVal('ledger-date-from', financeState.filters.date_from);
  setVal('ledger-date-to', financeState.filters.date_to);
  setVal('ledger-category-filter', financeState.filters.category_id);
  setVal('ledger-account-filter', financeState.filters.account);
  setVal('ledger-type-filter', financeState.filters.tx_type);
  setVal('ledger-amount-min', financeState.filters.amount_min);
  setVal('ledger-amount-max', financeState.filters.amount_max);
  setVal('ledger-sort', financeState.filters.sort);
}

function renderFinanceMetrics(metrics = []) {
  financeState.metrics = metrics.slice();
  const container = document.getElementById('finance-metric-cards');
  if (!container) return;
  container.innerHTML = metrics.map((metric) => {
    const trend = Number(metric.trend || 0);
    const trendClass = trend >= 0 ? 'positive' : 'negative';
    const trendArrow = trend >= 0 ? '▲' : '▼';
    return `
      <div class="metric-link-card static metric-with-tooltip">
        <div class="metric-copy">
          <div class="metric-label">${escapeHtml(metric.label || 'Metric')}</div>
          <div class="metric-value">${formatMoneyKES(metric.value || 0)}</div>
          <div class="metric-trend ${trendClass}">${trendArrow} ${Math.abs(trend).toFixed(1)}%</div>
          <div class="metric-tooltip">${escapeHtml(metric.description || '')}</div>
        </div>
        <div class="metric-icon-wrap"><i class="fas ${escapeHtml(metric.icon || 'fa-chart-line')}"></i></div>
      </div>`;
  }).join('');
}

function formatTxnSign(row) {
  const signed = Number(row.signed_amount || 0);
  const css = signed >= 0 ? 'amount-positive' : 'amount-negative';
  return `<span class="${css}">${signed >= 0 ? '+' : '-'}${formatMoneyKES(Math.abs(signed))}</span>`;
}

function renderLedgerTable(rows = []) {
  financeState.ledger = rows.slice();
  const body = document.getElementById('ledger-table-body');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="table-empty">No transactions found for current filters.</td></tr>';
    return;
  }

  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.tx_date || '')}</td>
      <td>${escapeHtml(row.description || '')}</td>
      <td><span class="tag category-pill" style="background:${escapeHtml(row.category?.color || '#8B5A2B')}33;color:${escapeHtml(row.category?.color || '#8B5A2B')}">${escapeHtml(row.category?.name || 'Uncategorized')}</span></td>
      <td>${escapeHtml((row.account || '').replace('_', ' '))}</td>
      <td>${formatTxnSign(row)}</td>
      <td>${(row.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join(' ')}</td>
      <td class="action-cell">
        <button class="btn-outline btn-mini" type="button" data-action="edit-transaction" data-id="${row.id}">Edit</button>
        <button class="btn-outline btn-mini danger" type="button" data-action="delete-transaction" data-id="${row.id}">Delete</button>
      </td>
    </tr>
  `).join('');
}

function renderLedgerPagination(pagination) {
  financeState.pagination = { ...financeState.pagination, ...(pagination || {}) };
  const container = document.getElementById('ledger-pagination');
  if (!container) return;
  const page = financeState.pagination.page || 1;
  const totalPages = financeState.pagination.total_pages || 1;
  const totalItems = financeState.pagination.total_items || 0;
  container.innerHTML = `
    <div class="pagination-meta">Page ${page} of ${totalPages} · ${totalItems} rows</div>
    <div class="pagination-controls">
      <button class="btn-outline btn-mini" type="button" id="ledger-prev-page" ${page <= 1 ? 'disabled' : ''}>Prev</button>
      <button class="btn-outline btn-mini" type="button" id="ledger-next-page" ${page >= totalPages ? 'disabled' : ''}>Next</button>
    </div>`;

  const prev = document.getElementById('ledger-prev-page');
  const next = document.getElementById('ledger-next-page');
  if (prev) {
    prev.addEventListener('click', () => {
      if (financeState.pagination.page > 1) {
        financeState.filters.page = financeState.pagination.page - 1;
        loadFinanceLedger();
      }
    });
  }
  if (next) {
    next.addEventListener('click', () => {
      if (financeState.pagination.page < financeState.pagination.total_pages) {
        financeState.filters.page = financeState.pagination.page + 1;
        loadFinanceLedger();
      }
    });
  }
}

function renderBudgetCards(rows = []) {
  financeState.budgets = rows.slice();
  const grid = document.getElementById('budget-grid');
  if (!grid) return;
  if (!rows.length) {
    grid.innerHTML = '<div class="table-empty">No budgets configured yet.</div>';
    return;
  }

  const formatBudgetPeriod = (value) => {
    if (!value) return 'Period not set';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  grid.innerHTML = rows.map((item) => `
    <div class="budget-card ${item.is_over_limit ? 'over-limit' : item.is_warning ? 'warning' : ''}">
      <div class="budget-card-head">
        <span class="tag" style="background:${escapeHtml(item.category.color)}33;color:${escapeHtml(item.category.color)}">${escapeHtml(item.category.name)}</span>
        <div class="action-cell">
          <button class="btn-outline btn-mini" type="button" data-action="edit-budget" data-id="${item.id}">Edit</button>
          <button class="btn-outline btn-mini danger" type="button" data-action="delete-budget" data-id="${item.id}">Delete</button>
        </div>
      </div>
      <div class="budget-period">${formatBudgetPeriod(item.period_start)}</div>
      <div class="finance-row"><span class="finance-label">Monthly Limit</span><span>${formatMoneyKES(item.monthly_limit)}</span></div>
      <div class="finance-row"><span class="finance-label">Current Spend</span><span>${formatMoneyKES(item.current_spending)}</span></div>
      <div class="finance-row"><span class="finance-label">Remaining</span><span>${formatMoneyKES(item.remaining_balance)}</span></div>
      <div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, item.progress_pct)}%"></div></div>
      <div class="progress-label"><span>${item.progress_pct}% used</span><span>${item.is_over_limit ? 'Over limit' : item.is_warning ? 'Warning' : 'Healthy'}</span></div>
    </div>
  `).join('');
}

function renderSavingsGoals(rows = []) {
  financeState.goals = rows.slice();
  const grid = document.getElementById('savings-goals-grid');
  if (!grid) return;
  if (!rows.length) {
    grid.innerHTML = '<div class="table-empty">No savings goals yet.</div>';
    return;
  }

  grid.innerHTML = rows.map((item) => `
    <div class="goal-card">
      <div class="budget-card-head">
        <div class="card-title">${escapeHtml(item.name)}</div>
        <div class="action-cell">
          <button class="btn-outline btn-mini" type="button" data-action="edit-goal" data-id="${item.id}">Edit</button>
          <button class="btn-outline btn-mini danger" type="button" data-action="delete-goal" data-id="${item.id}">Delete</button>
        </div>
      </div>
      <div class="finance-row"><span class="finance-label">Target</span><span>${formatMoneyKES(item.target_amount)}</span></div>
      <div class="finance-row"><span class="finance-label">Current</span><span>${formatMoneyKES(item.current_savings)}</span></div>
      <div class="finance-row"><span class="finance-label">Deadline</span><span>${escapeHtml(item.deadline || 'No deadline')}</span></div>
      <div class="progress-track"><div class="progress-fill" style="width:${item.progress_pct}%"></div></div>
      <div class="progress-label"><span>${item.progress_pct}% complete</span><span>Suggest ${formatMoneyKES(item.monthly_target_suggestion)}/mo</span></div>
    </div>
  `).join('');
}

function renderApplicationPlanner(rows = []) {
  financeState.applicationCosts = rows.slice();
  const body = document.getElementById('application-table-body');
  const summary = document.getElementById('application-summary');
  if (!body || !summary) return;

  let estimatedTotal = 0;
  let actualTotal = 0;
  rows.forEach((row) => {
    estimatedTotal += Number(row.estimated_cost || 0);
    actualTotal += Number(row.actual_cost || 0);
  });

  summary.innerHTML = `
    <div class="finance-row"><span class="finance-label">Total Estimated</span><span>${formatMoneyKES(estimatedTotal)}</span></div>
    <div class="finance-row"><span class="finance-label">Total Actual</span><span>${formatMoneyKES(actualTotal)}</span></div>
    <div class="finance-row"><span class="finance-label">Outstanding</span><span>${formatMoneyKES(Math.max(0, estimatedTotal - actualTotal))}</span></div>
  `;

  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="table-empty">No application costs tracked yet.</td></tr>';
    return;
  }

  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.item_label || row.item_type || '')}</td>
      <td>${formatMoneyKES(row.estimated_cost || 0)}</td>
      <td>${row.actual_cost !== null ? formatMoneyKES(row.actual_cost) : '—'}</td>
      <td><span class="schol-status">${escapeHtml((row.status || '').replace('_', ' '))}</span></td>
      <td>${escapeHtml(row.deadline || '—')}</td>
      <td>${escapeHtml(row.notes || '—')}</td>
      <td class="action-cell">
        <button class="btn-outline btn-mini" type="button" data-action="edit-application" data-id="${row.id}">Edit</button>
        <button class="btn-outline btn-mini danger" type="button" data-action="delete-application" data-id="${row.id}">Delete</button>
      </td>
    </tr>
  `).join('');
}

function renderProjectBudgets(rows = []) {
  financeState.projectBudgets = rows.slice();
  const grid = document.getElementById('project-budget-grid');
  if (!grid) return;
  if (!rows.length) {
    grid.innerHTML = '<div class="table-empty">No project budgets created.</div>';
    return;
  }
  grid.innerHTML = rows.map((row) => `
    <div class="budget-card">
      <div class="budget-card-head">
        <div class="card-title">${escapeHtml(row.project_name)}</div>
        <div class="action-cell">
          <button class="btn-outline btn-mini" type="button" data-action="edit-project-budget" data-id="${row.id}">Edit</button>
          <button class="btn-outline btn-mini danger" type="button" data-action="delete-project-budget" data-id="${row.id}">Delete</button>
        </div>
      </div>
      <div class="finance-row"><span class="finance-label">Budget</span><span>${formatMoneyKES(row.budget_amount)}</span></div>
      <div class="finance-row"><span class="finance-label">Spent</span><span>${formatMoneyKES(row.spent_amount)}</span></div>
      <div class="finance-row"><span class="finance-label">Remaining</span><span>${formatMoneyKES(row.remaining_funds)}</span></div>
      <div class="finance-row"><span class="finance-label">ROI</span><span>${row.roi_actual_pct ?? 0}% / ${row.roi_target_pct ?? 0}%</span></div>
    </div>
  `).join('');
}

function renderRecurringForecast(rows = []) {
  financeState.recurringForecast = rows.slice();
  const list = document.getElementById('recurring-forecast-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="table-empty">No recurring forecast items.</div>';
    return;
  }
  list.innerHTML = rows.slice(0, 20).map((row) => `
    <div class="compact-list-item">
      <span class="compact-date">${escapeHtml(row.due_date)}</span>
      <span class="compact-copy">${escapeHtml(row.template_name)} · ${formatMoneyKES(row.amount)}</span>
    </div>
  `).join('');
}

function renderFinanceAlerts(rows = []) {
  financeState.alerts = rows.slice();
  const list = document.getElementById('budget-alerts-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="table-empty">No active alerts.</div>';
    return;
  }
  list.innerHTML = rows.slice(0, 20).map((row) => `
    <div class="insight-item ${row.is_read ? 'alert-read' : ''}">
      <span class="tag">${escapeHtml(row.severity)}</span>
      <span>${escapeHtml(row.message)}</span>
      ${row.is_read ? '' : `<button class="btn-outline btn-mini" type="button" data-action="read-alert" data-id="${row.id}">Read</button>`}
    </div>
  `).join('');
}

function renderFinanceInsights(rows = []) {
  financeState.insights = rows.slice();
  const list = document.getElementById('finance-insights-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="table-empty">No insights available yet.</div>';
    return;
  }
  list.innerHTML = rows.map((row) => `
    <div class="insight-item"><span class="tag">${escapeHtml(row.tag || 'Insight')}</span><span>${escapeHtml(row.message || '')}</span></div>
  `).join('');
}

function renderFinanceHealthSnapshot(summary = {}) {
  const box = document.getElementById('finance-health-snapshot');
  if (!box) return;
  box.innerHTML = `
    <div class="finance-row"><span class="finance-label">Cash Flow</span><span>${formatMoneyKES(summary.cash_flow || 0)}</span></div>
    <div class="finance-row"><span class="finance-label">Budget Remaining</span><span>${formatMoneyKES(summary.budget_remaining || 0)}</span></div>
    <div class="finance-row"><span class="finance-label">Total Savings</span><span>${formatMoneyKES(summary.total_savings || 0)}</span></div>
    <div class="finance-row"><span class="finance-label">Budget Warnings</span><span>${summary.budget_warning_count || 0}</span></div>
    <div class="finance-row"><span class="finance-label">Budget Overruns</span><span>${summary.budget_overrun_count || 0}</span></div>
  `;
}

function renderFinanceCategories(rows = []) {
  financeState.categories = rows.slice();
  const list = document.getElementById('finance-categories-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="table-empty">No categories created yet.</div>';
    return;
  }
  list.innerHTML = rows.map((row) => `
    <div class="finance-category-item">
      <div class="category-main">
        <span class="category-dot" style="background:${escapeHtml(row.color || '#8B5A2B')}"></span>
        <div>
          <div class="category-name">${escapeHtml(row.name || '')}</div>
          <div class="category-meta">${escapeHtml((row.kind || 'other').replace('_', ' '))}${row.is_active ? '' : ' · inactive'}</div>
        </div>
      </div>
      <div class="action-cell">
        <button class="btn-outline btn-mini" type="button" data-action="edit-category" data-id="${row.id}">Edit</button>
        <button class="btn-outline btn-mini danger" type="button" data-action="delete-category" data-id="${row.id}">Delete</button>
      </div>
    </div>
  `).join('');
}

function getChartBaseConfig(type = 'bar') {
  const rootStyle = getComputedStyle(document.documentElement);
  const bodyStyle = document.body ? getComputedStyle(document.body) : rootStyle;
  const read = (name, fallback) => bodyStyle.getPropertyValue(name).trim() || rootStyle.getPropertyValue(name).trim() || fallback;
  const GOLD = read('--gold', '#E2B56D');
  const GOLD_DEEP = read('--gold-deep', '#B98138');
  const BRONZE = read('--bronze', '#8B5A2B');
  const COCOA = read('--cocoa', '#6B3A1F');
  const CREAM = '#F0D7A6';
  const MUTED = read('--color-text-secondary', '#6f4a32');
  const SUCCESS = read('--green-500', '#2a9d5c');
  const DANGER = read('--red-500', '#c0392b');
  const PALETTE = [GOLD, BRONZE, '#D4A35A', COCOA, GOLD_DEEP, SUCCESS, DANGER, CREAM];

  return {
    type,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 700,
        easing: 'easeOutQuart',
      },
      plugins: {
        legend: {
          labels: {
            color: MUTED,
            font: { family: "'Quicksand', system-ui, sans-serif", size: 12, weight: '600' },
            padding: 16,
            pointStyleWidth: 8,
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: 'rgba(59,30,18,.94)',
          bodyColor: CREAM,
          bodyFont: { family: "'Quicksand', system-ui, sans-serif", size: 12 },
          borderColor: 'rgba(240,215,166,.24)',
          borderWidth: 1,
          boxPadding: 4,
          cornerRadius: 10,
          displayColors: true,
          padding: 12,
          titleColor: GOLD,
          titleFont: { family: "'Quicksand', system-ui, sans-serif", size: 13, weight: '700' },
        },
      },
      scales: (type === 'doughnut' || type === 'pie' || type === 'radar') ? undefined : {
        x: {
          grid: { color: 'rgba(59,30,18,.06)', drawBorder: false },
          ticks: {
            color: MUTED,
            font: { family: "'Quicksand', system-ui, sans-serif", size: 11 },
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(59,30,18,.07)', drawBorder: false },
          ticks: {
            color: MUTED,
            font: { family: "'Quicksand', system-ui, sans-serif", size: 11 },
          },
        },
      },
    },
    _palette: PALETTE,
  };
}

function chartGradient(ctx, colorTop = 'rgba(226,181,109,.55)', colorBottom = 'rgba(226,181,109,.03)') {
  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, colorTop);
  gradient.addColorStop(1, colorBottom);
  return gradient;
}

function deepMergeChartOptions(base = {}, overrides = {}) {
  const output = { ...base };
  Object.entries(overrides || {}).forEach(([key, value]) => {
    const isCanvasGradient = typeof CanvasGradient !== 'undefined' && value instanceof CanvasGradient;
    if (
      value
      && typeof value === 'object'
      && !Array.isArray(value)
      && !isCanvasGradient
    ) {
      output[key] = deepMergeChartOptions(output[key] || {}, value);
    } else {
      output[key] = value;
    }
  });
  return output;
}

function withChartBaseConfig(config = {}, ctx = null) {
  const type = config.type || 'bar';
  const base = getChartBaseConfig(type);
  const palette = base._palette || getChartDatasetColors(8);
  const datasets = (config.data?.datasets || []).map((dataset, index) => {
    const next = { ...dataset };
    if (!next.backgroundColor) {
      if (type === 'line' && ctx) next.backgroundColor = chartGradient(ctx);
      else next.backgroundColor = type === 'bar' ? `${palette[index % palette.length]}CC` : palette;
    }
    if (!next.borderColor && (type === 'bar' || type === 'line')) {
      next.borderColor = palette[index % palette.length];
    }
    if (type === 'bar') {
      if (next.borderRadius === undefined) next.borderRadius = 8;
      if (next.borderSkipped === undefined) next.borderSkipped = false;
      if (next.borderWidth === undefined) next.borderWidth = 1.5;
    }
    if (type === 'line') {
      if (next.tension === undefined) next.tension = 0.35;
      if (next.borderWidth === undefined) next.borderWidth = 2;
      if (next.pointRadius === undefined) next.pointRadius = 3;
      if (next.pointHoverRadius === undefined) next.pointHoverRadius = 5;
    }
    return next;
  });

  const { _palette, ...baseConfig } = base;
  return {
    ...baseConfig,
    ...config,
    data: config.data ? { ...config.data, datasets } : config.data,
    options: deepMergeChartOptions(base.options, config.options || {}),
  };
}

function getChartDatasetColors(len) {
  const palette = getChartBaseConfig('bar')._palette;
  return Array.from({ length: len }).map((_, idx) => palette[idx % palette.length]);
}

function upsertChart(chartId, config) {
  const canvas = document.getElementById(chartId);
  if (!canvas || typeof Chart === 'undefined') return;
  if (financeState.chartInstances[chartId]) {
    financeState.chartInstances[chartId].destroy();
  }
  const ctx = canvas.getContext('2d');
  financeState.chartInstances[chartId] = new Chart(ctx, withChartBaseConfig(config, ctx));
}

function renderFinanceCharts() {
  if (!isFinancePage()) return;
  const charts = financeState.charts || {};
  if (!charts.monthly_income_vs_expenses) return;

  const labelsA = charts.monthly_income_vs_expenses.labels || [];
  upsertChart('finance-income-expense-chart', {
    type: 'bar',
    data: {
      labels: labelsA,
      datasets: [
        { label: 'Income', data: charts.monthly_income_vs_expenses.income || [], backgroundColor: '#2f9c57', borderRadius: 8 },
        { label: 'Expenses', data: charts.monthly_income_vs_expenses.expenses || [], backgroundColor: '#bf4a4a', borderRadius: 8 },
      ],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });

  const catRows = charts.expense_category_distribution || [];
  upsertChart('finance-category-chart', {
    type: 'doughnut',
    data: {
      labels: catRows.map((r) => r.label),
      datasets: [{ data: catRows.map((r) => r.value), backgroundColor: catRows.map((r) => r.color || '#8B5A2B') }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });

  upsertChart('finance-savings-growth-chart', {
    type: 'line',
    data: {
      labels: charts.savings_growth?.labels || [],
      datasets: [{ label: 'Savings', data: charts.savings_growth?.values || [], borderColor: '#E2B56D', backgroundColor: '#E2B56D33', tension: 0.35, fill: true }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } } },
  });

  const budgetRows = charts.budget_utilization || [];
  upsertChart('finance-budget-utilization-chart', {
    type: 'bar',
    data: {
      labels: budgetRows.map((r) => r.label),
      datasets: [{ label: 'Utilization %', data: budgetRows.map((r) => r.value), backgroundColor: budgetRows.map((r) => r.color || '#8B5A2B') }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } },
  });

  const appRows = charts.application_cost_breakdown || [];
  upsertChart('finance-application-breakdown-chart', {
    type: 'bar',
    data: {
      labels: appRows.map((r) => r.label),
      datasets: [
        { label: 'Estimated', data: appRows.map((r) => r.estimated), backgroundColor: '#8B5A2B' },
        { label: 'Actual', data: appRows.map((r) => r.actual), backgroundColor: '#E2B56D' },
      ],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });

  const roiRows = charts.project_roi || [];
  upsertChart('finance-project-roi-chart', {
    type: 'bar',
    data: {
      labels: roiRows.map((r) => r.label),
      datasets: [
        { label: 'ROI Target %', data: roiRows.map((r) => r.target), backgroundColor: '#3B1E12' },
        { label: 'ROI Actual %', data: roiRows.map((r) => r.actual), backgroundColor: '#2f9c57' },
      ],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });
}

function populateFinanceSelects() {
  const categorySelectIds = ['ledger-category-filter', 'transaction-category', 'budget-category', 'recurring-category'];
  categorySelectIds.forEach((id) => {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    const hasAnyOption = id === 'ledger-category-filter' ? '<option value=\"\">All categories</option>' : '<option value=\"\">Select category</option>';
    select.innerHTML = hasAnyOption + financeState.categories.map((cat) => `<option value=\"${cat.id}\">${escapeHtml(cat.name)}</option>`).join('');
    select.value = current || select.value;
  });

  const goalSelect = document.getElementById('transaction-savings-goal');
  if (goalSelect) {
    const current = goalSelect.value;
    goalSelect.innerHTML = '<option value=\"\">None</option>' + financeState.goals.map((goal) => `<option value=\"${goal.id}\">${escapeHtml(goal.name)}</option>`).join('');
    goalSelect.value = current || '';
  }

  const appSelect = document.getElementById('transaction-application-cost');
  if (appSelect) {
    const current = appSelect.value;
    appSelect.innerHTML = '<option value=\"\">None</option>' + financeState.applicationCosts.map((item) => `<option value=\"${item.id}\">${escapeHtml(item.item_label || item.item_type)}</option>`).join('');
    appSelect.value = current || '';
  }

  const projectSelect = document.getElementById('transaction-project-budget');
  if (projectSelect) {
    const current = projectSelect.value;
    projectSelect.innerHTML = '<option value=\"\">None</option>' + financeState.projectBudgets.map((item) => `<option value=\"${item.id}\">${escapeHtml(item.project_name)}</option>`).join('');
    projectSelect.value = current || '';
  }

  updateLedgerFilterUI();
}

async function loadFinanceBootstrap() {
  if (!isFinancePage()) return;
  if (!isAuthenticated() && !isAppUnlocked()) return;
  try {
    const payload = await financeApiGet('/api/finance/bootstrap/', financeState.filters);
    financeState.charts = payload.charts || {};
    renderFinanceMetrics(payload.metrics || []);
    renderLedgerTable(payload.ledger?.rows || []);
    renderLedgerPagination(payload.ledger?.pagination || {});
    let budgetRows = payload.budgets || [];
    try {
      const budgetData = await financeApiGet('/api/finance/budgets/');
      if (Array.isArray(budgetData.rows)) budgetRows = budgetData.rows;
    } catch (err) {
      // Keep bootstrap budgets if full budget list fails.
    }
    renderBudgetCards(budgetRows);
    renderSavingsGoals(payload.savings_goals || []);
    renderApplicationPlanner(payload.application_costs || []);
    renderProjectBudgets(payload.project_budgets || []);
    renderRecurringForecast(payload.recurring_forecast || []);
    renderFinanceAlerts(payload.alerts || []);
    renderFinanceInsights(payload.insights || []);
    renderFinanceHealthSnapshot(payload.summary || {});

    financeState.goals = payload.savings_goals || [];
    financeState.applicationCosts = payload.application_costs || [];
    financeState.projectBudgets = payload.project_budgets || [];

    const categoryData = await financeApiGet('/api/finance/categories/');
    renderFinanceCategories(categoryData.rows || []);
    populateFinanceSelects();
    renderFinanceCharts();
    clearFinanceNeedsRefresh();
  } catch (err) {
    showToast(err.message || 'Failed to load finance command center');
  }
}

async function loadDiaryEntries() {
  return loadDiaryEntriesPage(1);
}

async function loadDiaryEntriesPage(page = 1) {
  if (!isDiaryPage()) return null;
  if (!isAuthenticated() && !isAppUnlocked()) return null;
  if (diaryState.isLoading) return null;

  diaryState.isLoading = true;
  const loadMoreButton = document.getElementById('diary-load-more');
  if (loadMoreButton) {
    loadMoreButton.disabled = true;
    loadMoreButton.textContent = 'Loading...';
  }

  try {
    const data = await apiRequest(`/api/diary/entries/?page=${page}`);
    diaryState.pagination = { ...(data.pagination || {}) };
    const nextEntries = page > 1
      ? [...diaryState.entries, ...(data.rows || [])]
      : (data.rows || []);
    renderDiaryEntries(nextEntries);
    updateDashboardDiaryPreview(nextEntries);
    return data;
  } catch (err) {
    showToast(err.message || 'Unable to load diary entries');
    return null;
  } finally {
    diaryState.isLoading = false;
    if (loadMoreButton) {
      loadMoreButton.disabled = false;
      loadMoreButton.textContent = 'Load More';
    }
  }
}

async function loadDiaryStreak() {
  const streakCard = document.getElementById('diary-streak-card');
  if (!streakCard) return null;

  try {
    const data = await apiRequest('/api/diary/streak/');
    if (!data.ok) return data;
    const countEl = document.getElementById('streak-count');
    const longestEl = document.getElementById('streak-longest');
    const totalEl = document.getElementById('streak-total');
    const grid = document.getElementById('streak-grid');

    if (countEl) countEl.textContent = data.current_streak ?? 0;
    if (longestEl) longestEl.textContent = data.longest_streak ?? 0;
    if (totalEl) totalEl.textContent = data.total_entries ?? 0;
    if (grid) {
      grid.innerHTML = (data.days || []).map((day) =>
        `<div class="streak-day${day.has_entry ? ' has-entry' : ''}" title="${escapeHtml(day.date)}"></div>`
      ).join('');
    }
    updateDashboardDiaryMetric(data);
    return data;
  } catch (err) {
    showToast(err.message || 'Unable to load streak data');
    return null;
  }
}

function setupDiaryPage() {
  if (!isDiaryPage()) return;
  const loadMoreButton = document.getElementById('diary-load-more');
  if (loadMoreButton && loadMoreButton.dataset.bound !== '1') {
    loadMoreButton.dataset.bound = '1';
    loadMoreButton.addEventListener('click', () => {
      if (diaryState.pagination.has_next) {
        loadDiaryEntriesPage((diaryState.pagination.page || 1) + 1);
      }
    });
  }

  loadDiaryEntriesPage(1);
  loadDiaryStreak();
}

function loadBucketGoals() {
  if (!isBucketPage()) return;
  window.location.reload();
}

async function loadFinanceLedger() {
  if (!isFinancePage() || !isAuthenticated()) return;
  try {
    const data = await financeApiGet('/api/finance/transactions/', financeState.filters);
    renderLedgerTable(data.rows || []);
    renderLedgerPagination(data.pagination || {});
  } catch (err) {
    showToast(err.message || 'Unable to load ledger data');
  }
}

function openModal(overlayId) {
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  overlay._lastFocused = document.activeElement;
  const card = overlay.querySelector('.modal-card, .ca-modal-card');
  if (card) card.style.animation = '';
  overlay.classList.remove('hidden');
  overlay.setAttribute('aria-hidden', 'false');
  document.body?.classList.add('has-open-modal');

  requestAnimationFrame(() => {
    requestAnimationFrame(() => overlay.classList.add('is-open'));
  });

  const focusable = overlay.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
  if (focusable.length) setTimeout(() => focusable[0].focus(), 50);

  overlay._backdropHandler = (event) => {
    if (event.target === overlay) closeModal(overlayId);
  };
  overlay.addEventListener('click', overlay._backdropHandler);
}

function closeModal(overlayId) {
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  overlay.classList.remove('is-open');
  if (overlay._backdropHandler) overlay.removeEventListener('click', overlay._backdropHandler);

  let didClose = false;
  const finish = () => {
    if (didClose) return;
    didClose = true;
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
    const card = overlay.querySelector('.modal-card, .ca-modal-card');
    if (card) card.style.animation = '';
    if (!document.querySelector('.modal-overlay:not(.hidden)')) {
      document.body?.classList.remove('has-open-modal');
    }
    overlay._lastFocused?.focus?.();
  };

  const card = overlay.querySelector('.modal-card, .ca-modal-card');
  if (card && !prefersReducedMotion()) {
    card.style.animation = 'modalSpringOut 180ms cubic-bezier(0.7, 0, 0.84, 0) both';
    card.addEventListener('animationend', finish, { once: true });
    setTimeout(finish, 240);
  } else {
    setTimeout(finish, 120);
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach((el) => {
    el.classList.remove('is-open');
    el.classList.add('hidden');
    el.setAttribute('aria-hidden', 'true');
  });
  document.body?.classList.remove('has-open-modal');
}

const AVATAR_ICON_CATEGORIES = [
  {
    name: 'Activities',
    icons: [
      { id: 'running', icon: 'fa-running', label: 'Running' },
      { id: 'swimming', icon: 'fa-swimmer', label: 'Swimming' },
      { id: 'football', icon: 'fa-football-ball', label: 'Football' },
      { id: 'basketball', icon: 'fa-basketball-ball', label: 'Basketball' },
      { id: 'music', icon: 'fa-music', label: 'Music' },
      { id: 'guitar', icon: 'fa-guitar', label: 'Guitar' },
      { id: 'chess', icon: 'fa-chess', label: 'Chess' },
      { id: 'gamepad', icon: 'fa-gamepad', label: 'Gaming' },
      { id: 'palette', icon: 'fa-palette', label: 'Art' },
      { id: 'camera', icon: 'fa-camera', label: 'Photography' },
      { id: 'book', icon: 'fa-book', label: 'Reading' },
      { id: 'film', icon: 'fa-film', label: 'Film' },
      { id: 'microphone', icon: 'fa-microphone', label: 'Podcast' },
      { id: 'dumbbell', icon: 'fa-dumbbell', label: 'Fitness' },
      { id: 'bicycle', icon: 'fa-bicycle', label: 'Cycling' },
      { id: 'hiking', icon: 'fa-hiking', label: 'Hiking' },
      { id: 'skiing', icon: 'fa-skiing', label: 'Skiing' },
      { id: 'volleyball', icon: 'fa-volleyball-ball', label: 'Volleyball' },
      { id: 'baseball', icon: 'fa-baseball-ball', label: 'Baseball' },
      { id: 'trophy', icon: 'fa-trophy', label: 'Trophy' },
      { id: 'microscope', icon: 'fa-microscope', label: 'Science' },
      { id: 'flask', icon: 'fa-flask', label: 'Chemistry' },
      { id: 'robot', icon: 'fa-robot', label: 'Robotics' },
      { id: 'code', icon: 'fa-code', label: 'Coding' },
      { id: 'pen', icon: 'fa-pen-fancy', label: 'Writing' },
      { id: 'drama', icon: 'fa-theater-masks', label: 'Drama' },
      { id: 'puzzle', icon: 'fa-puzzle-piece', label: 'Puzzles' },
      { id: 'dice', icon: 'fa-dice', label: 'Board Games' },
    ],
  },
  {
    name: 'Animals & Nature',
    icons: [
      { id: 'cat', icon: 'fa-cat', label: 'Cat' },
      { id: 'dog', icon: 'fa-dog', label: 'Dog' },
      { id: 'fish', icon: 'fa-fish', label: 'Fish' },
      { id: 'horse', icon: 'fa-horse', label: 'Horse' },
      { id: 'crow', icon: 'fa-crow', label: 'Bird' },
      { id: 'frog', icon: 'fa-frog', label: 'Frog' },
      { id: 'spider', icon: 'fa-spider', label: 'Spider' },
      { id: 'paw', icon: 'fa-paw', label: 'Paw' },
      { id: 'feather', icon: 'fa-feather', label: 'Feather' },
      { id: 'leaf', icon: 'fa-leaf', label: 'Leaf' },
      { id: 'seedling', icon: 'fa-seedling', label: 'Plant' },
      { id: 'tree', icon: 'fa-tree', label: 'Tree' },
      { id: 'sun', icon: 'fa-sun', label: 'Sun' },
      { id: 'moon', icon: 'fa-moon', label: 'Moon' },
      { id: 'star', icon: 'fa-star', label: 'Star' },
      { id: 'snowflake', icon: 'fa-snowflake', label: 'Snowflake' },
      { id: 'fire', icon: 'fa-fire', label: 'Fire' },
      { id: 'water', icon: 'fa-water', label: 'Water' },
      { id: 'mountain', icon: 'fa-mountain', label: 'Mountain' },
      { id: 'cloud', icon: 'fa-cloud', label: 'Cloud' },
      { id: 'dragon', icon: 'fa-dragon', label: 'Dragon' },
      { id: 'dove', icon: 'fa-dove', label: 'Dove' },
      { id: 'bug', icon: 'fa-bug', label: 'Bug' },
      { id: 'otter', icon: 'fa-otter', label: 'Otter' },
    ],
  },
  {
    name: 'Food & Drink',
    icons: [
      { id: 'pizza', icon: 'fa-pizza-slice', label: 'Pizza' },
      { id: 'hamburger', icon: 'fa-hamburger', label: 'Burger' },
      { id: 'coffee', icon: 'fa-coffee', label: 'Coffee' },
      { id: 'ice-cream', icon: 'fa-ice-cream', label: 'Ice Cream' },
      { id: 'apple', icon: 'fa-apple-alt', label: 'Apple' },
      { id: 'carrot', icon: 'fa-carrot', label: 'Carrot' },
      { id: 'bread', icon: 'fa-bread-slice', label: 'Bread' },
      { id: 'cocktail', icon: 'fa-cocktail', label: 'Cocktail' },
      { id: 'lemon', icon: 'fa-lemon', label: 'Lemon' },
      { id: 'egg', icon: 'fa-egg', label: 'Egg' },
      { id: 'pepper', icon: 'fa-pepper-hot', label: 'Pepper' },
      { id: 'cookie', icon: 'fa-cookie', label: 'Cookie' },
      { id: 'cheese', icon: 'fa-cheese', label: 'Cheese' },
      { id: 'drumstick', icon: 'fa-drumstick-bite', label: 'Chicken' },
      { id: 'wine', icon: 'fa-wine-glass-alt', label: 'Wine' },
      { id: 'beer', icon: 'fa-beer', label: 'Beer' },
    ],
  },
  {
    name: 'Travel & Places',
    icons: [
      { id: 'plane', icon: 'fa-plane', label: 'Plane' },
      { id: 'car', icon: 'fa-car', label: 'Car' },
      { id: 'rocket', icon: 'fa-rocket', label: 'Rocket' },
      { id: 'ship', icon: 'fa-ship', label: 'Ship' },
      { id: 'train', icon: 'fa-train', label: 'Train' },
      { id: 'bus', icon: 'fa-bus', label: 'Bus' },
      { id: 'globe', icon: 'fa-globe', label: 'Globe' },
      { id: 'map', icon: 'fa-map-marked-alt', label: 'Map' },
      { id: 'compass', icon: 'fa-compass', label: 'Compass' },
      { id: 'city', icon: 'fa-city', label: 'City' },
      { id: 'landmark', icon: 'fa-landmark', label: 'Landmark' },
      { id: 'umbrella-beach', icon: 'fa-umbrella-beach', label: 'Beach' },
      { id: 'campground', icon: 'fa-campground', label: 'Camping' },
      { id: 'igloo', icon: 'fa-igloo', label: 'Igloo' },
    ],
  },
  {
    name: 'Objects & Symbols',
    icons: [
      { id: 'heart', icon: 'fa-heart', label: 'Heart' },
      { id: 'gem', icon: 'fa-gem', label: 'Gem' },
      { id: 'crown', icon: 'fa-crown', label: 'Crown' },
      { id: 'bolt', icon: 'fa-bolt', label: 'Lightning' },
      { id: 'shield', icon: 'fa-shield-alt', label: 'Shield' },
      { id: 'key', icon: 'fa-key', label: 'Key' },
      { id: 'lock', icon: 'fa-lock', label: 'Lock' },
      { id: 'flag', icon: 'fa-flag', label: 'Flag' },
      { id: 'bell', icon: 'fa-bell', label: 'Bell' },
      { id: 'lightbulb', icon: 'fa-lightbulb', label: 'Idea' },
      { id: 'magnifier', icon: 'fa-search', label: 'Research' },
      { id: 'briefcase', icon: 'fa-briefcase', label: 'Business' },
      { id: 'graduation', icon: 'fa-graduation-cap', label: 'Graduate' },
      { id: 'atom', icon: 'fa-atom', label: 'Atom' },
      { id: 'infinity', icon: 'fa-infinity', label: 'Infinity' },
      { id: 'peace', icon: 'fa-peace', label: 'Peace' },
      { id: 'yin-yang', icon: 'fa-yin-yang', label: 'Balance' },
      { id: 'anchor', icon: 'fa-anchor', label: 'Anchor' },
      { id: 'hammer', icon: 'fa-hammer', label: 'Hammer' },
      { id: 'magic', icon: 'fa-magic', label: 'Magic' },
    ],
  },
  {
    name: 'People & Faces',
    icons: [
      { id: 'user', icon: 'fa-user', label: 'Person' },
      { id: 'user-astronaut', icon: 'fa-user-astronaut', label: 'Astronaut' },
      { id: 'user-ninja', icon: 'fa-user-ninja', label: 'Ninja' },
      { id: 'user-graduate', icon: 'fa-user-graduate', label: 'Graduate' },
      { id: 'user-md', icon: 'fa-user-md', label: 'Doctor' },
      { id: 'user-tie', icon: 'fa-user-tie', label: 'Professional' },
      { id: 'baby', icon: 'fa-baby', label: 'Baby' },
      { id: 'child', icon: 'fa-child', label: 'Child' },
      { id: 'hands-helping', icon: 'fa-hands-helping', label: 'Volunteer' },
      { id: 'pray', icon: 'fa-praying-hands', label: 'Prayer' },
      { id: 'fist', icon: 'fa-fist-raised', label: 'Strength' },
    ],
  },
];

let selectedAvatarIcon = null;
let selectedAvatarColor = '#0073c8';

function applyAvatarToShell(iconClass, color) {
  const safeIcon = iconClass || 'fa-user';
  const safeColor = color || '#0073c8';
  const topbarAvatar = document.getElementById('topbar-profile-avatar');
  const sidebarAvatar = document.querySelector('.user-avatar');
  if (topbarAvatar) {
    topbarAvatar.innerHTML = `<i class="fas ${safeIcon}" style="font-size:16px; color:white;"></i>`;
    topbarAvatar.style.background = safeColor;
  }
  if (sidebarAvatar) {
    sidebarAvatar.innerHTML = `<i class="fas ${safeIcon}" style="font-size:14px; color:white;"></i>`;
    sidebarAvatar.style.background = safeColor;
  }
}

function updateAvatarPreview() {
  const preview = document.getElementById('avatar-preview-icon');
  const circle = document.getElementById('avatar-preview-circle');
  if (preview) preview.className = `fas ${selectedAvatarIcon || 'fa-user'}`;
  if (circle) circle.style.background = selectedAvatarColor || '#0073c8';
}

function markSelectedAvatarControls() {
  document.querySelectorAll('.ca-avatar-icon-btn').forEach((btn) => {
    btn.classList.toggle('selected', btn.dataset.icon === selectedAvatarIcon);
  });
  document.querySelectorAll('.ca-avatar-color-btn').forEach((btn) => {
    btn.classList.toggle('selected', btn.dataset.color === selectedAvatarColor);
  });
}

function restoreAvatarFromStorage() {
  try {
    const savedIcon = localStorage.getItem('myos-avatar-icon');
    const savedColor = localStorage.getItem('myos-avatar-color');
    if (savedIcon && savedColor) {
      selectedAvatarIcon = savedIcon;
      selectedAvatarColor = savedColor;
      applyAvatarToShell(savedIcon, savedColor);
      updateAvatarPreview();
      markSelectedAvatarControls();
    }
  } catch (e) {
    // Ignore storage failures.
  }
}

function renderAvatarIconGrid() {
  const grid = document.getElementById('avatar-icon-grid');
  if (!grid || grid.dataset.rendered === '1') return;
  grid.dataset.rendered = '1';
  let html = '';
  AVATAR_ICON_CATEGORIES.forEach((cat) => {
    html += `<div class="ca-avatar-category-title">${cat.name}</div>`;
    html += '<div class="ca-avatar-icon-row">';
    cat.icons.forEach((icon) => {
      html += `<button class="ca-avatar-icon-btn" data-icon="${icon.icon}" data-id="${icon.id}" title="${icon.label}" onclick="selectAvatarIcon('${icon.icon}', '${icon.id}')">
        <i class="fas ${icon.icon}"></i>
      </button>`;
    });
    html += '</div>';
  });
  html += '<div class="ca-avatar-category-title">Background Color</div>';
  html += '<div class="ca-avatar-color-row">';
  ['#0073c8', '#00a6a0', '#2d8a4e', '#7b3fa0', '#e53935', '#fb8c00', '#546e7a', '#37474f'].forEach((color) => {
    html += `<button class="ca-avatar-color-btn" style="background:${color}" data-color="${color}" onclick="selectAvatarColor('${color}')" aria-label="Color ${color}"></button>`;
  });
  html += '</div>';
  grid.innerHTML = html;
}

window.openAccountSettingsModal = function openAccountSettingsModal() {
  window.showAccountSettingsPanel('main');
  openModal('account-settings-modal');
};

window.showAccountSettingsPanel = function showAccountSettingsPanel(panel) {
  const main = document.getElementById('account-settings-main-menu');
  const panels = document.querySelectorAll('.ca-settings-panel');
  if (!main) return;
  if (panel === 'main') {
    main.classList.remove('hidden');
    panels.forEach((item) => item.classList.add('hidden'));
  } else {
    main.classList.add('hidden');
    panels.forEach((item) => item.classList.add('hidden'));
    document.getElementById(`account-settings-panel-${panel}`)?.classList.remove('hidden');
  }
};

window.openAvatarModal = function openAvatarModal() {
  restoreAvatarFromStorage();
  if (!selectedAvatarIcon) selectedAvatarIcon = 'fa-user';
  if (!selectedAvatarColor) selectedAvatarColor = '#0073c8';
  renderAvatarIconGrid();
  updateAvatarPreview();
  markSelectedAvatarControls();
  closeModal('account-settings-modal');
  openModal('avatar-modal');
};

window.selectAvatarIcon = function selectAvatarIcon(iconClass, iconId) {
  selectedAvatarIcon = iconClass;
  updateAvatarPreview();
  document.querySelectorAll('.ca-avatar-icon-btn').forEach((btn) => btn.classList.remove('selected'));
  document.querySelector(`.ca-avatar-icon-btn[data-id="${iconId}"]`)?.classList.add('selected');
};

window.selectAvatarColor = function selectAvatarColor(color) {
  selectedAvatarColor = color;
  updateAvatarPreview();
  document.querySelectorAll('.ca-avatar-color-btn').forEach((btn) => btn.classList.remove('selected'));
  document.querySelector(`.ca-avatar-color-btn[data-color="${color}"]`)?.classList.add('selected');
};

window.saveAvatar = function saveAvatar() {
  if (!selectedAvatarIcon) return;
  applyAvatarToShell(selectedAvatarIcon, selectedAvatarColor);
  try {
    localStorage.setItem('myos-avatar-icon', selectedAvatarIcon);
    localStorage.setItem('myos-avatar-color', selectedAvatarColor);
  } catch (e) {
    // Ignore storage failures.
  }
  closeModal('avatar-modal');
  if (window.showToast) showToast('Avatar updated!', 'success');
};

window.saveEmailChange = function saveEmailChange() {
  const email = (document.getElementById('new-email-input')?.value || '').trim();
  if (!email || !email.includes('@')) {
    showToast('Enter a valid email address', 'error');
    return;
  }
  const sidebarEmail = document.getElementById('sidebar-user-email');
  const settingsEmail = document.getElementById('settings-email');
  if (sidebarEmail) sidebarEmail.textContent = email;
  if (settingsEmail) settingsEmail.value = email;
  try {
    localStorage.setItem('myos-account-email', email);
  } catch (e) {
    // Ignore storage failures.
  }
  showToast('Email updated locally', 'success');
  window.showAccountSettingsPanel('main');
};

window.savePasswordChange = function savePasswordChange() {
  const next = document.getElementById('new-password-input')?.value || '';
  const confirm = document.getElementById('confirm-password-input')?.value || '';
  if (next.length < 8) {
    showToast('Password must be at least 8 characters', 'error');
    return;
  }
  if (next !== confirm) {
    showToast('New passwords do not match', 'error');
    return;
  }
  ['current-password-input', 'new-password-input', 'confirm-password-input'].forEach((id) => {
    const input = document.getElementById(id);
    if (input) input.value = '';
  });
  showToast('Password preference saved', 'success');
  window.showAccountSettingsPanel('main');
};

window.saveNotificationPrefs = function saveNotificationPrefs() {
  showToast('Communication preferences saved', 'success');
  window.showAccountSettingsPanel('main');
};

window.confirmAccountDelete = function confirmAccountDelete() {
  const confirmValue = (document.getElementById('delete-confirm-input')?.value || '').trim();
  if (confirmValue !== 'DELETE') {
    showToast('Type DELETE to confirm', 'error');
    return;
  }
  showToast('Account deletion requires backend confirmation', 'info');
};

function initAccountSettingsUI() {
  const trigger = document.getElementById('topbar-profile-trigger');
  if (trigger && trigger.dataset.accountSettingsBound !== '1') {
    trigger.dataset.accountSettingsBound = '1';
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      window.openAccountSettingsModal();
    });
  }
  restoreAvatarFromStorage();
}

function wrapTablesForMobile(root = document) {
  const tables = [];
  if (root instanceof Element && root.matches('table')) tables.push(root);
  root.querySelectorAll?.('table').forEach((table) => tables.push(table));
  tables.forEach((table) => {
    if (table.closest('.table-scroll-wrap, .table-wrap')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll-wrap';
    wrapper.style.cssText = 'overflow-x: auto; -webkit-overflow-scrolling: touch;';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });
}

function updateCommonAppProgress(root = document) {
  const progressSection = root.querySelector?.('.ca-progress-section') || document.querySelector('.ca-progress-section');
  if (!progressSection) return;
  const steps = Array.from(progressSection.querySelectorAll('.ca-step'));
  const complete = steps.filter((step) => step.classList.contains('ca-step--done')).length;
  const total = steps.length || 1;
  const percent = Math.round((complete / total) * 100);
  const fraction = document.getElementById('progress-fraction');
  const fill = document.getElementById('progress-bar-fill');
  if (fraction) fraction.textContent = `${complete}/${total} sections complete`;
  if (fill) fill.style.width = `${percent}%`;
}

function setTransactionFormValues(row = null) {
  const isEdit = Boolean(row);
  const map = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val ?? '';
  };
  map('transaction-id', row?.id || '');
  map('transaction-date', row?.tx_date || new Date().toISOString().slice(0, 10));
  map('transaction-description', row?.description || '');
  map('transaction-category', row?.category?.id || '');
  map('transaction-account', row?.account || 'bank');
  map('transaction-type', row?.tx_type || 'expense');
  map('transaction-amount', row?.amount || '');
  map('transaction-tags', (row?.tags || []).join(', '));
  map('transaction-savings-goal', row?.savings_goal_id || '');
  map('transaction-application-cost', row?.application_cost_id || '');
  map('transaction-project-budget', row?.project_budget_id || '');
  map('transaction-notes', row?.notes || '');

  const title = document.getElementById('transaction-modal-title');
  if (title) title.textContent = isEdit ? 'Edit Transaction' : 'Add Transaction';
}

async function submitTransactionForm(event) {
  event.preventDefault();
  const transactionId = document.getElementById('transaction-id')?.value;
  const payload = {
    tx_date: document.getElementById('transaction-date')?.value,
    description: document.getElementById('transaction-description')?.value,
    category_id: Number(document.getElementById('transaction-category')?.value || 0),
    account: document.getElementById('transaction-account')?.value,
    tx_type: document.getElementById('transaction-type')?.value,
    amount: document.getElementById('transaction-amount')?.value,
    tags: document.getElementById('transaction-tags')?.value,
    savings_goal_id: document.getElementById('transaction-savings-goal')?.value || null,
    application_cost_id: document.getElementById('transaction-application-cost')?.value || null,
    project_budget_id: document.getElementById('transaction-project-budget')?.value || null,
    notes: document.getElementById('transaction-notes')?.value,
  };
  try {
    if (transactionId) {
      await financeApiPost(`/api/finance/transactions/${transactionId}/update/`, payload);
      showToast('Transaction updated');
    } else {
      await financeApiPost('/api/finance/transactions/create/', payload);
      showToast('Transaction created');
    }
    closeModal('transaction-modal-overlay');
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save transaction');
  }
}

function fillSimpleForm(prefix, row, fieldMap) {
  Object.entries(fieldMap).forEach(([field, source]) => {
    const el = document.getElementById(`${prefix}-${field}`);
    if (!el) return;
    el.value = row?.[source] ?? '';
  });
}

function openBudgetModal(row = null) {
  fillSimpleForm('budget', row, {
    id: 'id',
    category: 'category.id',
  });
  document.getElementById('budget-id').value = row?.id || '';
  document.getElementById('budget-category').value = row?.category?.id || '';
  document.getElementById('budget-period-start').value = row?.period_start || new Date().toISOString().slice(0, 10);
  document.getElementById('budget-monthly-limit').value = row?.monthly_limit || '';
  document.getElementById('budget-threshold').value = row?.warning_threshold_pct || 90;
  document.getElementById('budget-active').value = row?.is_active ? '1' : '0';
  document.getElementById('budget-modal-title').textContent = row ? 'Edit Budget' : 'Add Budget';
  openModal('budget-modal-overlay');
}

async function submitBudgetForm(event) {
  event.preventDefault();
  const id = document.getElementById('budget-id').value;
  const payload = {
    category_id: Number(document.getElementById('budget-category').value || 0),
    period_start: document.getElementById('budget-period-start').value,
    monthly_limit: document.getElementById('budget-monthly-limit').value,
    warning_threshold_pct: document.getElementById('budget-threshold').value,
    is_active: document.getElementById('budget-active').value === '1',
  };
  try {
    if (id) await financeApiPost(`/api/finance/budgets/${id}/update/`, payload);
    else await financeApiPost('/api/finance/budgets/create/', payload);
    closeModal('budget-modal-overlay');
    showToast(`Budget ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save budget');
  }
}

function openGoalModal(row = null) {
  document.getElementById('goal-id').value = row?.id || '';
  document.getElementById('goal-name').value = row?.name || '';
  document.getElementById('goal-target-amount').value = row?.target_amount || '';
  document.getElementById('goal-starting-amount').value = row?.starting_amount || row?.current_savings || '';
  document.getElementById('goal-deadline').value = row?.deadline || '';
  document.getElementById('goal-status').value = row?.status || 'active';
  document.getElementById('goal-modal-title').textContent = row ? 'Edit Savings Goal' : 'Add Savings Goal';
  openModal('goal-modal-overlay');
}

async function submitGoalForm(event) {
  event.preventDefault();
  const id = document.getElementById('goal-id').value;
  const payload = {
    name: document.getElementById('goal-name').value,
    target_amount: document.getElementById('goal-target-amount').value,
    starting_amount: document.getElementById('goal-starting-amount').value,
    deadline: document.getElementById('goal-deadline').value || null,
    status: document.getElementById('goal-status').value,
  };
  try {
    if (id) await financeApiPost(`/api/finance/savings-goals/${id}/update/`, payload);
    else await financeApiPost('/api/finance/savings-goals/create/', payload);
    closeModal('goal-modal-overlay');
    showToast(`Goal ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save goal');
  }
}

function openApplicationModal(row = null) {
  document.getElementById('application-id').value = row?.id || '';
  document.getElementById('application-item-type').value = row?.item_type || 'other';
  document.getElementById('application-estimated').value = row?.estimated_cost || '';
  document.getElementById('application-actual').value = row?.actual_cost ?? '';
  document.getElementById('application-status').value = row?.status || 'planned';
  document.getElementById('application-deadline').value = row?.deadline || '';
  document.getElementById('application-notes').value = row?.notes || '';
  document.getElementById('application-modal-title').textContent = row ? 'Edit Application Cost' : 'Add Application Cost';
  openModal('application-modal-overlay');
}

async function submitApplicationForm(event) {
  event.preventDefault();
  const id = document.getElementById('application-id').value;
  const payload = {
    item_type: document.getElementById('application-item-type').value,
    estimated_cost: document.getElementById('application-estimated').value,
    actual_cost: document.getElementById('application-actual').value || null,
    status: document.getElementById('application-status').value,
    deadline: document.getElementById('application-deadline').value || null,
    notes: document.getElementById('application-notes').value,
  };
  try {
    if (id) await financeApiPost(`/api/finance/application-costs/${id}/update/`, payload);
    else await financeApiPost('/api/finance/application-costs/create/', payload);
    closeModal('application-modal-overlay');
    showToast(`Application item ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save application item');
  }
}

function openProjectBudgetModal(row = null) {
  document.getElementById('project-budget-id').value = row?.id || '';
  document.getElementById('project-budget-name').value = row?.project_name || '';
  document.getElementById('project-budget-amount').value = row?.budget_amount || '';
  document.getElementById('project-budget-spent-adjustment').value = row?.manual_spent_adjustment || 0;
  document.getElementById('project-budget-roi-target').value = row?.roi_target_pct ?? '';
  document.getElementById('project-budget-roi-actual').value = row?.roi_actual_pct ?? '';
  document.getElementById('project-budget-status').value = row?.status || 'active';
  document.getElementById('project-budget-modal-title').textContent = row ? 'Edit Project Budget' : 'Add Project Budget';
  openModal('project-budget-modal-overlay');
}

async function submitProjectBudgetForm(event) {
  event.preventDefault();
  const id = document.getElementById('project-budget-id').value;
  const payload = {
    project_name: document.getElementById('project-budget-name').value,
    budget_amount: document.getElementById('project-budget-amount').value,
    manual_spent_adjustment: document.getElementById('project-budget-spent-adjustment').value,
    roi_target_pct: document.getElementById('project-budget-roi-target').value || null,
    roi_actual_pct: document.getElementById('project-budget-roi-actual').value || null,
    status: document.getElementById('project-budget-status').value,
  };
  try {
    if (id) await financeApiPost(`/api/finance/project-budgets/${id}/update/`, payload);
    else await financeApiPost('/api/finance/project-budgets/create/', payload);
    closeModal('project-budget-modal-overlay');
    showToast(`Project budget ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save project budget');
  }
}

function openRecurringModal(row = null) {
  document.getElementById('recurring-id').value = row?.id || '';
  document.getElementById('recurring-name').value = row?.name || '';
  document.getElementById('recurring-category').value = row?.category_id || '';
  document.getElementById('recurring-account').value = row?.account || 'bank';
  document.getElementById('recurring-amount').value = row?.amount || '';
  document.getElementById('recurring-cadence').value = row?.cadence || 'monthly';
  document.getElementById('recurring-next-due').value = row?.next_due_date || '';
  document.getElementById('recurring-end-date').value = row?.end_date || '';
  document.getElementById('recurring-active').value = row?.is_active ? '1' : '0';
  document.getElementById('recurring-modal-title').textContent = row ? 'Edit Recurring Template' : 'Add Recurring Template';
  openModal('recurring-modal-overlay');
}

async function submitRecurringForm(event) {
  event.preventDefault();
  const id = document.getElementById('recurring-id').value;
  const payload = {
    name: document.getElementById('recurring-name').value,
    category_id: Number(document.getElementById('recurring-category').value || 0),
    account: document.getElementById('recurring-account').value,
    amount: document.getElementById('recurring-amount').value,
    cadence: document.getElementById('recurring-cadence').value,
    next_due_date: document.getElementById('recurring-next-due').value,
    end_date: document.getElementById('recurring-end-date').value || null,
    is_active: document.getElementById('recurring-active').value === '1',
  };
  try {
    if (id) await financeApiPost(`/api/finance/recurring/${id}/update/`, payload);
    else await financeApiPost('/api/finance/recurring/create/', payload);
    closeModal('recurring-modal-overlay');
    showToast(`Recurring template ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save recurring template');
  }
}

function openCategoryModal(row = null) {
  document.getElementById('category-id').value = row?.id || '';
  document.getElementById('category-name').value = row?.name || '';
  document.getElementById('category-slug').value = row?.slug || '';
  document.getElementById('category-kind').value = row?.kind || 'expense';
  document.getElementById('category-color').value = row?.color || '#8B5A2B';
  document.getElementById('category-icon').value = row?.icon || 'fa-wallet';
  document.getElementById('category-sort-order').value = row?.sort_order ?? 0;
  document.getElementById('category-active').value = row?.is_active === false ? '0' : '1';
  document.getElementById('category-modal-title').textContent = row ? 'Edit Category' : 'Add Category';
  openModal('category-modal-overlay');
}

async function submitCategoryForm(event) {
  event.preventDefault();
  const id = document.getElementById('category-id').value;
  const payload = {
    name: document.getElementById('category-name').value,
    slug: document.getElementById('category-slug').value,
    kind: document.getElementById('category-kind').value,
    color: document.getElementById('category-color').value,
    icon: document.getElementById('category-icon').value,
    sort_order: document.getElementById('category-sort-order').value,
    is_active: document.getElementById('category-active').value === '1',
  };
  try {
    if (id) await financeApiPost(`/api/finance/categories/${id}/update/`, payload);
    else await financeApiPost('/api/finance/categories/create/', payload);
    closeModal('category-modal-overlay');
    showToast(`Category ${id ? 'updated' : 'created'}`);
    await loadFinanceBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save category');
  }
}

async function refreshForecast(days = 60) {
  if (!isFinancePage()) return;
  try {
    const data = await financeApiGet('/api/finance/forecast/', { days });
    renderRecurringForecast(data.rows || []);
  } catch (err) {
    showToast(err.message || 'Unable to refresh forecast');
  }
}

function attachFinanceActionDelegates() {
  const page = document.getElementById('page-finance');
  if (!page) return;
  page.addEventListener('click', async (event) => {
    const btn = event.target.closest('[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    const id = Number(btn.dataset.id || 0);
    try {
      if (action === 'edit-transaction') {
        const row = financeState.ledger.find((item) => item.id === id);
        setTransactionFormValues(row);
        openModal('transaction-modal-overlay');
      } else if (action === 'delete-transaction') {
        await financeApiPost(`/api/finance/transactions/${id}/delete/`, {});
        showToast('Transaction deleted');
        await loadFinanceBootstrap();
      } else if (action === 'edit-budget') {
        const row = financeState.budgets.find((item) => item.id === id);
        openBudgetModal(row);
      } else if (action === 'delete-budget') {
        await financeApiPost(`/api/finance/budgets/${id}/delete/`, {});
        showToast('Budget deleted');
        await loadFinanceBootstrap();
      } else if (action === 'edit-goal') {
        const row = financeState.goals.find((item) => item.id === id);
        openGoalModal(row);
      } else if (action === 'delete-goal') {
        await financeApiPost(`/api/finance/savings-goals/${id}/delete/`, {});
        showToast('Goal deleted');
        await loadFinanceBootstrap();
      } else if (action === 'edit-application') {
        const row = financeState.applicationCosts.find((item) => item.id === id);
        openApplicationModal(row);
      } else if (action === 'delete-application') {
        await financeApiPost(`/api/finance/application-costs/${id}/delete/`, {});
        showToast('Application item deleted');
        await loadFinanceBootstrap();
      } else if (action === 'edit-project-budget') {
        const row = financeState.projectBudgets.find((item) => item.id === id);
        openProjectBudgetModal(row);
      } else if (action === 'delete-project-budget') {
        await financeApiPost(`/api/finance/project-budgets/${id}/delete/`, {});
        showToast('Project budget deleted');
        await loadFinanceBootstrap();
      } else if (action === 'edit-category') {
        const row = financeState.categories.find((item) => item.id === id);
        openCategoryModal(row || null);
      } else if (action === 'delete-category') {
        if (!window.confirm('Delete this category? This is blocked if it is already referenced.')) return;
        await financeApiPost(`/api/finance/categories/${id}/delete/`, {});
        showToast('Category deleted');
        await loadFinanceBootstrap();
      } else if (action === 'read-alert') {
        await financeApiPost(`/api/finance/alerts/${id}/mark-read/`, {});
        await loadFinanceBootstrap();
      }
    } catch (err) {
      showToast(err.message || 'Action failed');
    }
  });
}

function setupFinancePage() {
  if (!isFinancePage()) return;
  applyTheme(getCurrentTheme());
  if (financeState.isSetup) {
    if ((window.location.hash || '').toLowerCase() === '#finance-analytics') {
      switchTab('fin', 'analytics');
    }
    loadFinanceBootstrap();
    return;
  }
  financeState.isSetup = true;

  const bind = (id, eventName, handler) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(eventName, handler);
  };

  bind('quick-add-transaction-btn', 'click', () => {
    setTransactionFormValues(null);
    openModal('transaction-modal-overlay');
  });
  bind('ledger-apply-filters-btn', 'click', () => {
    readLedgerFiltersFromUI();
    financeState.filters.page = 1;
    loadFinanceLedger();
  });
  bind('ledger-export-csv-btn', 'click', () => {
    readLedgerFiltersFromUI();
    const params = new URLSearchParams(financeState.filters);
    window.location.href = `/api/finance/transactions/export.csv?${params.toString()}`;
  });
  bind('add-budget-btn', 'click', () => openBudgetModal(null));
  bind('add-goal-btn', 'click', () => openGoalModal(null));
  bind('add-application-cost-btn', 'click', () => openApplicationModal(null));
  bind('add-project-budget-btn', 'click', () => openProjectBudgetModal(null));
  bind('quick-add-recurring-btn', 'click', () => openRecurringModal(null));
  bind('quick-add-category-btn', 'click', () => openCategoryModal(null));
  bind('manage-categories-btn', 'click', () => openCategoryModal(null));
  bind('refresh-forecast-btn', 'click', () => refreshForecast(60));
  bind('mark-all-alerts-read-btn', 'click', async () => {
    try {
      await financeApiPost('/api/finance/alerts/mark-all-read/', {});
      await loadFinanceBootstrap();
    } catch (err) {
      showToast(err.message || 'Failed to mark alerts');
    }
  });

  bind('transaction-form', 'submit', submitTransactionForm);
  bind('budget-form', 'submit', submitBudgetForm);
  bind('goal-form', 'submit', submitGoalForm);
  bind('application-form', 'submit', submitApplicationForm);
  bind('project-budget-form', 'submit', submitProjectBudgetForm);
  bind('recurring-form', 'submit', submitRecurringForm);
  bind('category-form', 'submit', submitCategoryForm);

  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => closeModal(el.dataset.closeModal));
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) overlay.classList.add('hidden');
    });
  });

  document.addEventListener('keydown', (event) => {
    if (!isFinancePage()) return;
    if (event.key === 'Escape') {
      closeAllModals();
      return;
    }
    const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
    if (isTyping) return;
    if (event.key.toLowerCase() === 'n') {
      setTransactionFormValues(null);
      openModal('transaction-modal-overlay');
    } else if (event.key === '/') {
      event.preventDefault();
      document.getElementById('ledger-search')?.focus();
    } else if (event.key.toLowerCase() === 'e') {
      document.getElementById('ledger-export-csv-btn')?.click();
    }
  });

  attachFinanceActionDelegates();
  if ((window.location.hash || '').toLowerCase() === '#finance-analytics') {
    switchTab('fin', 'analytics');
  }
  loadFinanceBootstrap();
}

function isProjectsPage() {
  return getActivePage() === 'projects';
}

function projectsApiGet(path, query = null) {
  if (query) {
    const params = new URLSearchParams(query);
    return apiRequest(`${path}?${params.toString()}`);
  }
  return apiRequest(path);
}

function projectsApiPost(path, payload) {
  return apiRequest(path, 'POST', payload || {});
}

function upsertProjectChart(chartId, config) {
  const canvas = document.getElementById(chartId);
  if (!canvas || typeof Chart === 'undefined') return;
  if (projectsState.chartInstances[chartId]) {
    projectsState.chartInstances[chartId].destroy();
  }
  const ctx = canvas.getContext('2d');
  projectsState.chartInstances[chartId] = new Chart(ctx, withChartBaseConfig(config, ctx));
}

function renderProjectsCharts(rows = []) {
  if (!isProjectsPage()) return;
  const statusLabels = ['Idea', 'Pending', 'In Progress', 'Completed'];
  const statusKeys = ['idea', 'pending', 'in_progress', 'completed'];
  const statusCounts = statusKeys.map((key) => rows.filter((row) => row.status === key).length);

  upsertProjectChart('projects-status-chart', {
    type: 'pie',
    data: {
      labels: statusLabels,
      datasets: [
        {
          data: statusCounts,
          backgroundColor: ['#E2B56D', '#8B5A2B', '#6B3A1F', '#2f9c57'],
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
    },
  });

  const topProjects = rows.slice(0, 6);
  upsertProjectChart('projects-activity-chart', {
    type: 'bar',
    data: {
      labels: topProjects.map((row) => row.title),
      datasets: [
        {
          label: 'Progress %',
          data: topProjects.map((row) => Number(row.progress || 0)),
          backgroundColor: '#E2B56D',
          borderRadius: 8,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
        },
      },
    },
  });
}

function renderProjectMilestones(rows = []) {
  const milestones = document.getElementById('project-milestones-list');
  const timeline = document.getElementById('project-timeline-list');
  if (!milestones || !timeline) return;

  if (!rows.length) {
    milestones.innerHTML = '<div class="table-empty">No milestones available.</div>';
    timeline.innerHTML = '<div class="table-empty">No timeline data available.</div>';
    return;
  }

  milestones.innerHTML = rows
    .map((row) => {
      const status = String(row.status || 'idea').replace('_', ' ');
      return `
        <div class="milestone-row">
          <div class="milestone-title">${escapeHtml(row.title || 'Untitled')}</div>
          <div class="milestone-bar"><div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, Math.max(0, Number(row.progress || 0)))}%"></div></div></div>
          <div class="muted-note">${escapeHtml(status)}</div>
        </div>
      `;
    })
    .join('');

  timeline.innerHTML = rows
    .map((row) => {
      const start = row.start_date || 'N/A';
      const end = row.end_date || 'N/A';
      const progress = Math.min(100, Math.max(0, Number(row.progress || 0)));
      return `
        <div class="stack-list">
          <div class="list-row">
            <span class="list-title">${escapeHtml(row.title || 'Untitled')}</span>
            <span class="muted-note">${escapeHtml(start)} → ${escapeHtml(end)}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>
          <div class="progress-label"><span>${progress}% complete</span><span>${escapeHtml(String(row.status || 'idea').replace('_', ' '))}</span></div>
        </div>
      `;
    })
    .join('');
}

function renderProjects(rows = []) {
  projectsState.rows = rows.slice();
  const grid = document.getElementById('projects-grid');
  if (!grid) return;

  if (!rows.length) {
    grid.innerHTML = '<div class="dash-card"><div class="table-empty">No projects have been created yet.</div></div>';
    renderProjectMilestones([]);
    renderProjectsCharts([]);
    return;
  }

  grid.innerHTML = rows
    .map((row) => {
      const progress = Math.min(100, Math.max(0, Number(row.progress || 0)));
      const statusText = String(row.status || 'idea').replace('_', ' ');
      return `
        <div class="item-card">
          <div class="card-status status-${statusText.replace(' ', '')}">${escapeHtml(statusText)}</div>
          <div class="item-title">${escapeHtml(row.title || 'Untitled')}</div>
          <div class="item-meta">${escapeHtml(row.description || 'No description yet.')}</div>
          <div class="finance-row"><span class="finance-label">Start</span><span>${escapeHtml(row.start_date || 'Not set')}</span></div>
          <div class="finance-row"><span class="finance-label">End</span><span>${escapeHtml(row.end_date || 'Not set')}</span></div>
          <div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>
          <div class="progress-label"><span>${progress}% complete</span><span>${escapeHtml(statusText)}</span></div>
          <div class="action-cell">
            <button class="btn-outline btn-mini" type="button" data-action="edit-project" data-id="${row.id}">Edit</button>
            <button class="btn-outline btn-mini danger" type="button" data-action="delete-project" data-id="${row.id}">Delete</button>
          </div>
        </div>
      `;
    })
    .join('');

  renderProjectMilestones(rows);
  renderProjectsCharts(rows);
}

function openProjectModal(row = null) {
  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  setValue('project-id', row?.id || '');
  setValue('project-title', row?.title || '');
  setValue('project-description', row?.description || '');
  setValue('project-status', row?.status || 'idea');
  setValue('project-progress', Number(row?.progress || 0));
  setValue('project-start-date', row?.start_date || '');
  setValue('project-end-date', row?.end_date || '');

  const title = document.getElementById('project-modal-title');
  if (title) title.textContent = row ? 'Edit Project' : 'Add Project';
  openModal('project-modal-overlay');
}

async function submitProjectForm(event) {
  event.preventDefault();
  const projectId = document.getElementById('project-id')?.value || '';
  const payload = {
    title: (document.getElementById('project-title')?.value || '').trim(),
    description: (document.getElementById('project-description')?.value || '').trim(),
    status: document.getElementById('project-status')?.value || 'idea',
    progress: document.getElementById('project-progress')?.value || 0,
    start_date: document.getElementById('project-start-date')?.value || null,
    end_date: document.getElementById('project-end-date')?.value || null,
  };

  try {
    if (projectId) {
      await projectsApiPost(`/api/projects/${projectId}/update/`, payload);
      showToast('Project updated');
    } else {
      await projectsApiPost('/api/projects/create/', payload);
      showToast('Project created');
    }
    closeModal('project-modal-overlay');
    await loadProjects();
  } catch (err) {
    showToast(err.message || 'Unable to save project');
  }
}

async function loadProjects() {
  if (!isProjectsPage() || !isAuthenticated()) return;
  try {
    const data = await projectsApiGet('/api/projects/');
    renderProjects(data.rows || []);
  } catch (err) {
    showToast(err.message || 'Unable to load projects');
  }
}

function attachProjectActionDelegates() {
  const page = document.getElementById('page-projects');
  if (!page) return;
  page.addEventListener('click', async (event) => {
    const btn = event.target.closest('[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    const id = Number(btn.dataset.id || 0);
    try {
      if (action === 'edit-project') {
        const row = projectsState.rows.find((item) => item.id === id);
        openProjectModal(row || null);
      } else if (action === 'delete-project') {
        if (!window.confirm('Delete this project?')) return;
        await projectsApiPost(`/api/projects/${id}/delete/`, {});
        showToast('Project deleted');
        await loadProjects();
      }
    } catch (err) {
      showToast(err.message || 'Project action failed');
    }
  });
}

function setupProjectsPage() {
  if (!isProjectsPage()) return;
  if (projectsState.isSetup) {
    loadProjects();
    return;
  }
  projectsState.isSetup = true;

  const addBtn = document.getElementById('add-project-btn');
  if (addBtn) {
    addBtn.addEventListener('click', () => openProjectModal(null));
  }

  const form = document.getElementById('project-form');
  if (form) {
    form.addEventListener('submit', submitProjectForm);
  }

  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => closeModal(el.dataset.closeModal));
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) overlay.classList.add('hidden');
    });
  });

  attachProjectActionDelegates();
  loadProjects();
}

function isPersonalPage() {
  return getActivePage() === 'personal';
}

function personalApiGet(path, query = null) {
  if (query) {
    const params = new URLSearchParams(query);
    return apiRequest(`${path}?${params.toString()}`);
  }
  return apiRequest(path);
}

function personalApiPost(path, payload) {
  return apiRequest(path, 'POST', payload || {});
}

function ensurePersonalArray(raw) {
  if (Array.isArray(raw)) return raw.map((item) => String(item).trim()).filter(Boolean);
  return [];
}

function getPersonalDraftIndicator() {
  const card = document.querySelector('.personal-progress-card');
  if (!card) return null;
  let indicator = document.getElementById('personal-draft-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'personal-draft-indicator';
    indicator.className = 'personal-draft-indicator';
    card.appendChild(indicator);
  }
  return indicator;
}

function setPersonalDraftIndicator(message, isError = false) {
  const indicator = getPersonalDraftIndicator();
  if (!indicator) return;
  indicator.textContent = message || '';
  indicator.classList.toggle('error', isError);
}

function renderPersonalStepStatus() {
  const steps = document.querySelectorAll('#personal-steps .wizard-step');
  for (let i = 1; i <= 6; i += 1) {
    const stepData = personalState.stepStatus.find((item) => item.step === i) || {};
    const icon = stepData.icon || (i === personalState.currentStep ? '•' : '○');
    const status = stepData.status || 'not_started';
    const stepEl = steps[i - 1];
    const iconEl = document.getElementById(`personal-step-icon-${i}`);
    if (iconEl) iconEl.textContent = icon;
    if (stepEl) {
      stepEl.classList.toggle('active', i === personalState.currentStep);
      stepEl.classList.toggle('completed', status === 'completed' && i !== personalState.currentStep);
      stepEl.classList.toggle('in-progress', status === 'in_progress' && i !== personalState.currentStep);
    }
  }
}

function renderPersonalCompletion() {
  const score = Number(personalState.completionScore || 0);
  const scoreEl = document.getElementById('personal-completion-score');
  const fillEl = document.getElementById('personal-completion-fill');
  const labelEl = document.getElementById('personal-completion-label');
  const subEl = document.getElementById('personal-completion-sub');
  const suggestionsEl = document.getElementById('personal-completion-suggestions');
  const completedSteps = (personalState.stepStatus || []).filter((item) => item.status === 'completed').length;

  if (scoreEl) scoreEl.textContent = `${score}%`;
  if (fillEl) fillEl.style.width = `${Math.min(100, Math.max(0, score))}%`;
  if (labelEl) labelEl.textContent = score >= 100 ? 'Vault profile complete' : `Profile completion: ${score}%`;
  if (subEl) subEl.textContent = `${completedSteps} / 6 steps`;

  if (!suggestionsEl) return;
  const suggestions = ensurePersonalArray(personalState.suggestions).slice(0, 6);
  if (!suggestions.length) {
    suggestionsEl.innerHTML = '<div class="compact-list-item"><span class="compact-copy">All core sections are completed.</span></div>';
    return;
  }
  suggestionsEl.innerHTML = suggestions
    .map((item) => `<div class="compact-list-item"><i class="fas fa-lightbulb"></i><span class="compact-copy">${escapeHtml(item)}</span></div>`)
    .join('');
}

function renderPersonalTagList(containerId, listKey) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const values = ensurePersonalArray(personalState.tags[listKey]);
  if (!values.length) {
    container.innerHTML = '<div class="muted-note">No entries yet</div>';
    return;
  }
  container.innerHTML = values
    .map(
      (item) => `
        <span class="personal-tag-chip">
          <span>${escapeHtml(item)}</span>
          <button type="button" aria-label="Remove tag" data-action="remove-personal-tag" data-list="${escapeHtml(listKey)}" data-value="${escapeHtml(item)}">×</button>
        </span>
      `
    )
    .join('');
}

function addPersonalTag(listKey, value) {
  const text = String(value || '').trim();
  if (!text) return;
  const existing = ensurePersonalArray(personalState.tags[listKey]);
  if (existing.includes(text)) return;
  existing.push(text);
  personalState.tags[listKey] = existing;
  if (listKey === 'languages') renderPersonalTagList('vault-language-tags', 'languages');
  if (listKey === 'additionalEmails') renderPersonalTagList('vault-additional-emails', 'additionalEmails');
  if (listKey === 'otherPhones') renderPersonalTagList('vault-other-phones', 'otherPhones');

  const autosaveStep = listKey === 'languages' ? 1 : 2;
  schedulePersonalAutosave(autosaveStep);
}

function removePersonalTag(listKey, value) {
  const text = String(value || '').trim();
  if (!text) return;
  personalState.tags[listKey] = ensurePersonalArray(personalState.tags[listKey]).filter((item) => item !== text);
  if (listKey === 'languages') renderPersonalTagList('vault-language-tags', 'languages');
  if (listKey === 'additionalEmails') renderPersonalTagList('vault-additional-emails', 'additionalEmails');
  if (listKey === 'otherPhones') renderPersonalTagList('vault-other-phones', 'otherPhones');

  const autosaveStep = listKey === 'languages' ? 1 : 2;
  schedulePersonalAutosave(autosaveStep);
}

let personalPhotoObjectUrl = '';

function setPersonalPhotoPreview(source) {
  const card = document.getElementById('personal-photo-preview-card');
  if (!card) return;

  if (personalPhotoObjectUrl) {
    URL.revokeObjectURL(personalPhotoObjectUrl);
    personalPhotoObjectUrl = '';
  }

  if (!source) {
    card.innerHTML = '<div class="muted-note">No photo uploaded yet</div>';
    return;
  }

  let imageUrl = '';
  if (typeof source === 'string') {
    imageUrl = source;
  } else {
    personalPhotoObjectUrl = URL.createObjectURL(source);
    imageUrl = personalPhotoObjectUrl;
  }

  const fullName = [personalState.identity.first_name, personalState.identity.last_name].filter(Boolean).join(' ').trim() || 'Profile';
  card.innerHTML = `
    <img src="${escapeHtml(imageUrl)}" alt="Profile preview" class="personal-photo-image">
    <div class="personal-photo-meta">
      <div class="personal-photo-name">${escapeHtml(fullName)}</div>
      <div class="personal-photo-sub">${escapeHtml(personalState.identity.nationality || 'Nationality not set')}</div>
      <div class="personal-photo-sub muted-note">Auto-cropped preview for identity card.</div>
    </div>
  `;
}

async function buildSquareProfilePhoto(file) {
  if (!file || !String(file.type || '').startsWith('image/')) return file;
  return new Promise((resolve) => {
    const srcUrl = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const side = Math.min(img.width, img.height);
      const sx = Math.floor((img.width - side) / 2);
      const sy = Math.floor((img.height - side) / 2);
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 640;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        URL.revokeObjectURL(srcUrl);
        resolve(file);
        return;
      }
      ctx.drawImage(img, sx, sy, side, side, 0, 0, 640, 640);
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(srcUrl);
        if (!blob) {
          resolve(file);
          return;
        }
        const safeName = (file.name || 'profile').replace(/\.[a-zA-Z0-9]+$/, '');
        resolve(new File([blob], `${safeName}-cropped.jpg`, { type: 'image/jpeg' }));
      }, 'image/jpeg', 0.92);
    };
    img.onerror = () => {
      URL.revokeObjectURL(srcUrl);
      resolve(file);
    };
    img.src = srcUrl;
  });
}

async function handlePersonalProfilePhotoSelection(file) {
  if (!file) return;
  const extension = (file.name.split('.').pop() || '').toLowerCase();
  if (!['jpg', 'jpeg', 'png'].includes(extension)) {
    showToast('Profile photo must be JPG or PNG');
    return;
  }
  personalState.pendingProfilePhoto = await buildSquareProfilePhoto(file);
  setPersonalPhotoPreview(personalState.pendingProfilePhoto);
  setPersonalDraftIndicator('Profile photo ready. Saving draft...');
  schedulePersonalAutosave(1);
}

function renderPersonalIdentitySection() {
  const identity = personalState.identity || {};
  const set = (id, value) => {
    const field = document.getElementById(id);
    if (field) field.value = value ?? '';
  };
  set('vault-first-name', identity.first_name || '');
  set('vault-last-name', identity.last_name || '');
  set('vault-dob', identity.dob || '');
  set('vault-gender', identity.gender || '');
  set('vault-nationality', identity.nationality || '');

  personalState.tags.languages = ensurePersonalArray(identity.languages);
  renderPersonalTagList('vault-language-tags', 'languages');
  setPersonalPhotoPreview(personalState.pendingProfilePhoto || identity.profile_photo_url || '');
}

function renderPersonalContactSection() {
  const contact = personalState.contact || {};
  const set = (id, value) => {
    const field = document.getElementById(id);
    if (field) field.value = value ?? '';
  };
  set('vault-primary-email', contact.primary_email || '');
  set('vault-secondary-email', contact.secondary_email || '');
  set('vault-primary-phone', contact.primary_phone || '');
  set('vault-secondary-phone', contact.secondary_phone || '');
  set('vault-home-address', contact.home_address || '');
  set('vault-city', contact.city || '');
  set('vault-country', contact.country || '');
  set('vault-postal-code', contact.postal_code || '');

  personalState.tags.additionalEmails = ensurePersonalArray(contact.additional_emails);
  personalState.tags.otherPhones = ensurePersonalArray(contact.other_phone_numbers);
  renderPersonalTagList('vault-additional-emails', 'additionalEmails');
  renderPersonalTagList('vault-other-phones', 'otherPhones');
}

function renderPersonalIdentityDocuments() {
  const docs = personalState.identityDocuments || {};
  const set = (id, value) => {
    const field = document.getElementById(id);
    if (field) field.value = value ?? '';
  };
  set('vault-national-id', docs.national_id || '');
  set('vault-passport-number', docs.passport_number || '');
  set('vault-passport-expiry', docs.passport_expiry || '');
  set('vault-drivers-license', docs.drivers_license || '');
  set('vault-student-id', docs.student_id || '');
}

function renderPersonalIdentityFiles() {
  const body = document.getElementById('vault-identity-files-table');
  if (!body) return;
  const files = personalState.uploadedFiles || [];
  if (!files.length) {
    body.innerHTML = '<tr><td colspan="4" class="table-empty">No identity files uploaded yet</td></tr>';
    return;
  }

  body.innerHTML = files
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.file_type_label || row.file_type || '')}</td>
          <td>
            ${row.file_url ? `<a href="${escapeHtml(row.file_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.file_name || 'File')}</a>` : escapeHtml(row.file_name || 'File')}
            <div class="muted-note">${formatBytes(Number(row.file_size || 0))}</div>
          </td>
          <td>${escapeHtml(formatDateDisplay(row.updated_at))}</td>
          <td class="action-cell">
            <button type="button" class="btn-outline btn-mini" data-action="download-identity-file" data-id="${row.id}">Download</button>
            <button type="button" class="btn-outline danger btn-mini" data-action="delete-identity-file" data-id="${row.id}">Delete</button>
          </td>
        </tr>
      `
    )
    .join('');
}

function recomputeLocalExpiryAlerts() {
  const alerts = [];
  const expiry = personalState.identityDocuments?.passport_expiry;
  if (expiry) {
    const target = new Date(expiry);
    if (!Number.isNaN(target.getTime())) {
      const today = new Date();
      const diff = Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
      if (diff >= 0 && diff <= 180) {
        alerts.push({
          message: `Passport expires in ${diff} day${diff === 1 ? '' : 's'}.`,
          severity: diff <= 60 ? 'warning' : 'info',
        });
      }
    }
  }
  personalState.expiryAlerts = alerts;
}

function renderPersonalExpiryAlerts() {
  const list = document.getElementById('vault-expiry-alerts');
  if (!list) return;
  const alerts = personalState.expiryAlerts || [];
  if (!alerts.length) {
    list.innerHTML = '<div class="compact-list-item"><span class="compact-copy">No expiry reminders right now.</span></div>';
    return;
  }
  list.innerHTML = alerts
    .map((item) => `
      <div class="compact-list-item ${item.severity === 'warning' ? 'personal-alert-warning' : ''}">
        <i class="fas fa-clock"></i>
        <span class="compact-copy">${escapeHtml(item.message || '')}</span>
      </div>
    `)
    .join('');
}

function getPlatformIcon(platform) {
  const map = {
    google: 'fab fa-google',
    github: 'fab fa-github',
    linkedin: 'fab fa-linkedin',
    twitter_x: 'fab fa-x-twitter',
    instagram: 'fab fa-instagram',
    facebook: 'fab fa-facebook',
    tiktok: 'fab fa-tiktok',
    discord: 'fab fa-discord',
    reddit: 'fab fa-reddit',
    custom: 'fas fa-globe',
  };
  return map[platform] || 'fas fa-globe';
}

function getFilteredDigitalAccounts() {
  const q = String(personalState.filters.accountSearch || '').toLowerCase();
  const platform = personalState.filters.accountPlatform || '';
  return (personalState.digitalAccounts || []).filter((row) => {
    if (platform && row.platform !== platform) return false;
    if (!q) return true;
    const haystack = [row.platform_label, row.custom_platform, row.username, row.email_used, row.profile_link, row.notes]
      .map((item) => String(item || '').toLowerCase())
      .join(' ');
    return haystack.includes(q);
  });
}

function renderDigitalAccountsTable() {
  const body = document.getElementById('vault-digital-accounts-table');
  if (!body) return;
  const rows = getFilteredDigitalAccounts();
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="table-empty">No account records found</td></tr>';
    return;
  }
  body.innerHTML = rows
    .map((row) => {
      const platformLabel = row.platform === 'custom' && row.custom_platform
        ? row.custom_platform
        : row.platform_label || row.platform || 'Platform';
      return `
        <tr>
          <td><span class="vault-platform"><i class="${getPlatformIcon(row.platform)}"></i> ${escapeHtml(platformLabel)}</span></td>
          <td>${escapeHtml(row.username || '—')}</td>
          <td>${escapeHtml(row.email_used || '—')}</td>
          <td>${row.profile_link ? `<a href="${escapeHtml(row.profile_link)}" target="_blank" rel="noopener noreferrer">Open Link</a>` : '—'}</td>
          <td>${escapeHtml(row.notes || '—')}</td>
          <td class="action-cell">
            <button type="button" class="btn-outline btn-mini" data-action="edit-digital-account" data-id="${row.id}">Edit</button>
            <button type="button" class="btn-outline danger btn-mini" data-action="delete-digital-account" data-id="${row.id}">Delete</button>
          </td>
        </tr>
      `;
    })
    .join('');
}

function renderSocialProfilesSection() {
  const profile = personalState.socialProfiles || {};
  const set = (id, value) => {
    const field = document.getElementById(id);
    if (field) field.value = value ?? '';
  };
  set('vault-linkedin', profile.linkedin || '');
  set('vault-twitter', profile.twitter_x || '');
  set('vault-instagram', profile.instagram || '');
  set('vault-github', profile.github || '');
  set('vault-portfolio', profile.portfolio_website || '');
  set('vault-blog', profile.personal_blog || '');
  set('vault-youtube', profile.youtube_channel || '');
}

function renderSocialPreview() {
  const list = document.getElementById('vault-social-preview');
  if (!list) return;
  const links = [
    { label: 'LinkedIn', value: personalState.socialProfiles.linkedin, icon: 'fab fa-linkedin' },
    { label: 'Twitter / X', value: personalState.socialProfiles.twitter_x, icon: 'fab fa-x-twitter' },
    { label: 'Instagram', value: personalState.socialProfiles.instagram, icon: 'fab fa-instagram' },
    { label: 'GitHub', value: personalState.socialProfiles.github, icon: 'fab fa-github' },
    { label: 'Portfolio', value: personalState.socialProfiles.portfolio_website, icon: 'fas fa-briefcase' },
    { label: 'Blog', value: personalState.socialProfiles.personal_blog, icon: 'fas fa-blog' },
    { label: 'YouTube', value: personalState.socialProfiles.youtube_channel, icon: 'fab fa-youtube' },
  ].filter((row) => row.value);

  if (!links.length) {
    list.innerHTML = '<div class="compact-list-item"><span class="compact-copy">No public profile links added yet.</span></div>';
    return;
  }
  list.innerHTML = links
    .map(
      (row) => `
        <a class="compact-list-item" href="${escapeHtml(row.value)}" target="_blank" rel="noopener noreferrer">
          <i class="${row.icon}"></i>
          <span class="compact-copy">${escapeHtml(row.label)}</span>
        </a>
      `
    )
    .join('');
}

function renderPasswordReferencesTable() {
  const body = document.getElementById('vault-password-references-table');
  if (!body) return;
  const rows = personalState.passwordReferences || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="table-empty">No password reference entries yet</td></tr>';
    return;
  }
  body.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.platform || '')}</td>
          <td>${escapeHtml(row.username || '—')}</td>
          <td>${escapeHtml(row.email_used || '—')}</td>
          <td>${escapeHtml(row.password_hint || '—')}</td>
          <td>${row.two_factor_enabled ? 'Yes' : 'No'}</td>
          <td>${escapeHtml(row.password_manager_label || row.password_manager || '—')}</td>
          <td class="action-cell">
            <button type="button" class="btn-outline btn-mini" data-action="edit-password-reference" data-id="${row.id}">Edit</button>
            <button type="button" class="btn-outline danger btn-mini" data-action="delete-password-reference" data-id="${row.id}">Delete</button>
          </td>
        </tr>
      `
    )
    .join('');
}

function renderPersonalVaultPage() {
  renderPersonalCompletion();
  renderPersonalStepStatus();
  renderPersonalIdentitySection();
  renderPersonalContactSection();
  renderPersonalIdentityDocuments();
  renderPersonalIdentityFiles();
  renderPersonalExpiryAlerts();
  renderDigitalAccountsTable();
  renderSocialProfilesSection();
  renderSocialPreview();
  renderPasswordReferencesTable();
}

function recomputeLocalPersonalCompletion() {
  const identity = personalState.identity || {};
  const contact = personalState.contact || {};
  const docs = personalState.identityDocuments || {};
  const fileCount = (personalState.uploadedFiles || []).length;
  const social = personalState.socialProfiles || {};

  const step1 = Boolean(
    identity.first_name || identity.last_name || identity.dob || identity.nationality
    || (ensurePersonalArray(personalState.tags.languages).length > 0)
    || identity.profile_photo_url || personalState.pendingProfilePhoto
  );
  const step2 = Boolean((contact.primary_email && contact.primary_phone && contact.city && contact.country));
  const step3 = Boolean((docs.national_id || docs.passport_number || docs.passport_expiry || docs.drivers_license || docs.student_id) && fileCount > 0);
  const step4 = (personalState.digitalAccounts || []).length > 0;
  const step5 = Boolean(social.linkedin || social.twitter_x || social.instagram || social.github || social.portfolio_website || social.personal_blog || social.youtube_channel);
  const step6 = (personalState.passwordReferences || []).length > 0;

  const checks = [step1, step2, step3, step4, step5, step6];
  const completedCount = checks.filter(Boolean).length;
  personalState.completionScore = Math.round((completedCount / 6) * 100);
  personalState.stepStatus = checks.map((isDone, index) => ({
    step: index + 1,
    status: isDone ? 'completed' : 'not_started',
    icon: isDone ? '✓' : '○',
  }));
  const nextStep = personalState.stepStatus.find((item) => item.status !== 'completed');
  if (nextStep) {
    const row = personalState.stepStatus[nextStep.step - 1];
    row.status = 'in_progress';
    row.icon = '•';
  }
  const suggestions = [];
  if (!step1) suggestions.push('Add your basic identity details and profile photo.');
  if (!step2) suggestions.push('Add a primary contact email and phone number.');
  if (!step3) suggestions.push('Upload identity documents and add passport details.');
  if (!step4) suggestions.push('Add your key digital accounts.');
  if (!step5) suggestions.push('Add public social profile links.');
  if (!step6) suggestions.push('Add password reference entries with 2FA status.');
  personalState.suggestions = suggestions;
}

function getPersonalRecommendedStep() {
  const inProgress = (personalState.stepStatus || []).find((item) => item.status === 'in_progress');
  if (inProgress) return inProgress.step;
  const incomplete = (personalState.stepStatus || []).find((item) => item.status !== 'completed');
  if (incomplete) return incomplete.step;
  return personalState.currentStep || 1;
}

async function loadPersonalVaultBootstrap({ preserveStep = false, silent = false } = {}) {
  if (!isPersonalPage() || !isAuthenticated()) return;
  const previousStep = personalState.currentStep || 1;
  try {
    const payload = await personalApiGet('/api/personal-vault/bootstrap/');
    personalState.identity = payload.identity || {};
    personalState.contact = payload.contact || {};
    personalState.identityDocuments = payload.identity_documents || {};
    personalState.uploadedFiles = payload.uploaded_files || [];
    personalState.digitalAccounts = payload.digital_accounts || [];
    personalState.socialProfiles = payload.social_profiles || {};
    personalState.passwordReferences = payload.password_references || [];
    personalState.completionScore = Number(payload.completion_score || 0);
    personalState.stepStatus = payload.step_status || [];
    personalState.suggestions = payload.suggestions || [];
    personalState.expiryAlerts = payload.expiry_alerts || [];

    personalState.tags.languages = ensurePersonalArray(personalState.identity.languages);
    personalState.tags.additionalEmails = ensurePersonalArray(personalState.contact.additional_emails);
    personalState.tags.otherPhones = ensurePersonalArray(personalState.contact.other_phone_numbers);

    renderPersonalVaultPage();
    const stepToShow = preserveStep ? previousStep : getPersonalRecommendedStep();
    goPersonalStep(stepToShow);
  } catch (err) {
    if (!silent) showToast(err.message || 'Failed to load Personal Identity Vault');
  }
}

function getPersonalStep1Payload() {
  return {
    first_name: (document.getElementById('vault-first-name')?.value || '').trim(),
    last_name: (document.getElementById('vault-last-name')?.value || '').trim(),
    dob: document.getElementById('vault-dob')?.value || '',
    gender: document.getElementById('vault-gender')?.value || '',
    nationality: (document.getElementById('vault-nationality')?.value || '').trim(),
    languages: ensurePersonalArray(personalState.tags.languages),
  };
}

function getPersonalStep2Payload() {
  return {
    primary_email: (document.getElementById('vault-primary-email')?.value || '').trim(),
    secondary_email: (document.getElementById('vault-secondary-email')?.value || '').trim(),
    additional_emails: ensurePersonalArray(personalState.tags.additionalEmails),
    primary_phone: (document.getElementById('vault-primary-phone')?.value || '').trim(),
    secondary_phone: (document.getElementById('vault-secondary-phone')?.value || '').trim(),
    other_phone_numbers: ensurePersonalArray(personalState.tags.otherPhones),
    home_address: (document.getElementById('vault-home-address')?.value || '').trim(),
    city: (document.getElementById('vault-city')?.value || '').trim(),
    country: (document.getElementById('vault-country')?.value || '').trim(),
    postal_code: (document.getElementById('vault-postal-code')?.value || '').trim(),
  };
}

function getPersonalStep3Payload() {
  return {
    national_id: (document.getElementById('vault-national-id')?.value || '').trim(),
    passport_number: (document.getElementById('vault-passport-number')?.value || '').trim(),
    passport_expiry: document.getElementById('vault-passport-expiry')?.value || '',
    drivers_license: (document.getElementById('vault-drivers-license')?.value || '').trim(),
    student_id: (document.getElementById('vault-student-id')?.value || '').trim(),
  };
}

function getPersonalStep5Payload() {
  return {
    linkedin: (document.getElementById('vault-linkedin')?.value || '').trim(),
    twitter_x: (document.getElementById('vault-twitter')?.value || '').trim(),
    instagram: (document.getElementById('vault-instagram')?.value || '').trim(),
    github: (document.getElementById('vault-github')?.value || '').trim(),
    portfolio_website: (document.getElementById('vault-portfolio')?.value || '').trim(),
    personal_blog: (document.getElementById('vault-blog')?.value || '').trim(),
    youtube_channel: (document.getElementById('vault-youtube')?.value || '').trim(),
  };
}

async function savePersonalStep1({ goNext = false, silent = false, refresh = true } = {}) {
  const payload = getPersonalStep1Payload();
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (Array.isArray(value)) formData.append(key, value.join(', '));
    else formData.append(key, value ?? '');
  });
  if (personalState.pendingProfilePhoto) {
    formData.append('profile_photo', personalState.pendingProfilePhoto);
  }
  const response = await apiRequestForm('/api/personal-vault/step1/save/', formData);
  if (response?.identity) {
    personalState.identity = response.identity;
  }
  personalState.pendingProfilePhoto = null;
  if (refresh) {
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } else {
    recomputeLocalPersonalCompletion();
    renderPersonalCompletion();
    renderPersonalStepStatus();
    renderPersonalIdentitySection();
  }
  if (!silent) showToast('Basic identity information saved');
  if (goNext) goPersonalStep(2);
}

async function savePersonalStep2({ goNext = false, silent = false, refresh = true } = {}) {
  const response = await personalApiPost('/api/personal-vault/step2/save/', getPersonalStep2Payload());
  if (response?.contact) {
    personalState.contact = response.contact;
  }
  if (refresh) {
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } else {
    recomputeLocalPersonalCompletion();
    renderPersonalCompletion();
    renderPersonalStepStatus();
    renderPersonalContactSection();
  }
  if (!silent) showToast('Contact information saved');
  if (goNext) goPersonalStep(3);
}

async function savePersonalStep3({ goNext = false, silent = false, refresh = true } = {}) {
  const response = await personalApiPost('/api/personal-vault/step3/save/', getPersonalStep3Payload());
  if (response?.identity_documents) {
    personalState.identityDocuments = response.identity_documents;
  }
  if (refresh) {
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } else {
    recomputeLocalExpiryAlerts();
    recomputeLocalPersonalCompletion();
    renderPersonalCompletion();
    renderPersonalStepStatus();
    renderPersonalIdentityDocuments();
    renderPersonalExpiryAlerts();
  }
  if (!silent) showToast('Identity document details saved');
  if (goNext) goPersonalStep(4);
}

async function savePersonalStep5({ goNext = false, silent = false, refresh = true } = {}) {
  const response = await personalApiPost('/api/personal-vault/social-profiles/save/', getPersonalStep5Payload());
  if (response?.social_profiles) {
    personalState.socialProfiles = response.social_profiles;
  }
  if (refresh) {
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } else {
    recomputeLocalPersonalCompletion();
    renderPersonalCompletion();
    renderPersonalStepStatus();
    renderSocialProfilesSection();
    renderSocialPreview();
  }
  if (!silent) showToast('Public profile links saved');
  if (goNext) goPersonalStep(6);
}

async function saveCurrentPersonalStep({ goNext = false, silent = false } = {}) {
  const step = personalState.currentStep || 1;
  if (step === 1) await savePersonalStep1({ goNext, silent });
  else if (step === 2) await savePersonalStep2({ goNext, silent });
  else if (step === 3) await savePersonalStep3({ goNext, silent });
  else if (step === 5) await savePersonalStep5({ goNext, silent });
  else if (step === 6) {
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
    if (!silent) showToast('Personal Identity Vault synced');
  } else if (goNext) {
    goPersonalStep(Math.min(6, step + 1));
  }
}

function schedulePersonalAutosave(step) {
  if (!isPersonalPage()) return;
  const key = `step${step}`;
  clearTimeout(personalState.autosaveTimers[key]);
  setPersonalDraftIndicator('Saving draft...');
  personalState.autosaveTimers[key] = setTimeout(async () => {
    try {
      if (step === 1) await savePersonalStep1({ silent: true, refresh: false });
      else if (step === 2) await savePersonalStep2({ silent: true, refresh: false });
      else if (step === 3) await savePersonalStep3({ silent: true, refresh: false });
      else if (step === 5) await savePersonalStep5({ silent: true, refresh: false });
      setPersonalDraftIndicator(`Draft saved at ${new Date().toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit' })}`);
    } catch (err) {
      setPersonalDraftIndicator(err.message || 'Draft save failed', true);
    }
  }, 900);
}

function openDigitalAccountModal(row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('vault-digital-account-id', row?.id || '');
  set('vault-account-platform', row?.platform || 'google');
  set('vault-account-custom-platform', row?.custom_platform || '');
  set('vault-account-username', row?.username || '');
  set('vault-account-email', row?.email_used || '');
  set('vault-account-profile-link', row?.profile_link || '');
  set('vault-account-notes', row?.notes || '');
  const title = document.getElementById('vault-digital-account-modal-title');
  if (title) title.textContent = row ? 'Edit Digital Account' : 'Add Digital Account';
  openModal('vault-digital-account-modal-overlay');
}

async function submitDigitalAccountForm(event) {
  event.preventDefault();
  const id = document.getElementById('vault-digital-account-id')?.value;
  const payload = {
    platform: document.getElementById('vault-account-platform')?.value || 'google',
    custom_platform: (document.getElementById('vault-account-custom-platform')?.value || '').trim(),
    username: (document.getElementById('vault-account-username')?.value || '').trim(),
    email_used: (document.getElementById('vault-account-email')?.value || '').trim(),
    profile_link: (document.getElementById('vault-account-profile-link')?.value || '').trim(),
    notes: (document.getElementById('vault-account-notes')?.value || '').trim(),
  };
  try {
    if (id) await personalApiPost(`/api/personal-vault/digital-accounts/${id}/update/`, payload);
    else await personalApiPost('/api/personal-vault/digital-accounts/create/', payload);
    closeModal('vault-digital-account-modal-overlay');
    showToast(`Digital account ${id ? 'updated' : 'created'}`);
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } catch (err) {
    showToast(err.message || 'Unable to save digital account');
  }
}

function openPasswordReferenceModal(row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('vault-password-reference-id', row?.id || '');
  set('vault-ref-platform', row?.platform || '');
  set('vault-ref-username', row?.username || '');
  set('vault-ref-email', row?.email_used || '');
  set('vault-ref-password-hint', row?.password_hint || '');
  set('vault-ref-two-factor', row?.two_factor_enabled ? '1' : '0');
  set('vault-ref-password-manager', row?.password_manager || 'bitwarden');
  set('vault-ref-backup-location', row?.backup_codes_location || '');
  set('vault-ref-notes', row?.notes || '');
  const title = document.getElementById('vault-password-reference-modal-title');
  if (title) title.textContent = row ? 'Edit Password Reference' : 'Add Password Reference';
  openModal('vault-password-reference-modal-overlay');
}

async function submitPasswordReferenceForm(event) {
  event.preventDefault();
  const id = document.getElementById('vault-password-reference-id')?.value;
  const payload = {
    platform: (document.getElementById('vault-ref-platform')?.value || '').trim(),
    username: (document.getElementById('vault-ref-username')?.value || '').trim(),
    email_used: (document.getElementById('vault-ref-email')?.value || '').trim(),
    password_hint: (document.getElementById('vault-ref-password-hint')?.value || '').trim(),
    two_factor_enabled: document.getElementById('vault-ref-two-factor')?.value === '1',
    backup_codes_location: (document.getElementById('vault-ref-backup-location')?.value || '').trim(),
    password_manager: document.getElementById('vault-ref-password-manager')?.value || 'bitwarden',
    notes: (document.getElementById('vault-ref-notes')?.value || '').trim(),
  };
  try {
    if (id) await personalApiPost(`/api/personal-vault/password-references/${id}/update/`, payload);
    else await personalApiPost('/api/personal-vault/password-references/create/', payload);
    closeModal('vault-password-reference-modal-overlay');
    showToast(`Password reference ${id ? 'updated' : 'created'}`);
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } catch (err) {
    showToast(err.message || 'Unable to save password reference');
  }
}

async function uploadIdentityVaultFile() {
  const selectedInputFile = document.getElementById('vault-identity-file')?.files?.[0];
  const uploadFile = selectedInputFile || personalState.pendingIdentityFile;
  if (!uploadFile) {
    showToast('Select or drop a file first');
    return;
  }
  const payload = new FormData();
  payload.append('file_type', document.getElementById('vault-identity-file-type')?.value || 'other');
  payload.append('file', uploadFile);
  try {
    await apiRequestForm('/api/personal-vault/identity-files/upload/', payload);
    personalState.pendingIdentityFile = null;
    const field = document.getElementById('vault-identity-file');
    if (field) field.value = '';
    showToast('Identity file uploaded');
    await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
  } catch (err) {
    showToast(err.message || 'Identity file upload failed');
  }
}

function bindPersonalTagInput(inputId, buttonId, listKey) {
  const input = document.getElementById(inputId);
  const button = document.getElementById(buttonId);
  if (!input || !button) return;
  button.addEventListener('click', () => {
    addPersonalTag(listKey, input.value);
    input.value = '';
    input.focus();
  });
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    addPersonalTag(listKey, input.value);
    input.value = '';
  });
}

function setupPersonalDropzones() {
  const photoZone = document.getElementById('personal-photo-drop-zone');
  const docsZone = document.getElementById('personal-identity-drop-zone');
  const docsInput = document.getElementById('vault-identity-file');

  const attachDropHandlers = (zone, onDrop) => {
    if (!zone) return;
    const prevent = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((evt) => zone.addEventListener(evt, prevent));
    ['dragenter', 'dragover'].forEach((evt) => zone.addEventListener(evt, () => zone.classList.add('dragover')));
    ['dragleave', 'drop'].forEach((evt) => zone.addEventListener(evt, () => zone.classList.remove('dragover')));
    zone.addEventListener('drop', (event) => {
      const file = event.dataTransfer?.files?.[0];
      if (file) onDrop(file);
    });
  };

  attachDropHandlers(photoZone, (file) => {
    handlePersonalProfilePhotoSelection(file);
  });
  attachDropHandlers(docsZone, (file) => {
    personalState.pendingIdentityFile = file;
    showToast(`Identity file attached: ${file.name}`);
  });

  if (docsZone && docsInput) {
    docsZone.addEventListener('click', () => docsInput.click());
  }
}

function attachPersonalActionDelegates() {
  const page = document.getElementById('page-personal');
  if (!page) return;
  page.addEventListener('click', async (event) => {
    const trigger = event.target.closest('[data-action]');
    if (!trigger) return;
    const action = trigger.dataset.action;
    const id = Number(trigger.dataset.id || 0);
    const listKey = trigger.dataset.list || '';
    const value = trigger.dataset.value || '';

    try {
      if (action === 'remove-personal-tag') {
        removePersonalTag(listKey, value);
      } else if (action === 'download-identity-file') {
        const row = (personalState.uploadedFiles || []).find((item) => item.id === id);
        if (row?.file_url) window.open(row.file_url, '_blank', 'noopener,noreferrer');
      } else if (action === 'delete-identity-file') {
        if (!window.confirm('Delete this identity file?')) return;
        await personalApiPost(`/api/personal-vault/identity-files/${id}/delete/`, {});
        showToast('Identity file deleted');
        await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
      } else if (action === 'edit-digital-account') {
        const row = (personalState.digitalAccounts || []).find((item) => item.id === id);
        openDigitalAccountModal(row || null);
      } else if (action === 'delete-digital-account') {
        if (!window.confirm('Delete this account record?')) return;
        await personalApiPost(`/api/personal-vault/digital-accounts/${id}/delete/`, {});
        showToast('Digital account deleted');
        await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
      } else if (action === 'edit-password-reference') {
        const row = (personalState.passwordReferences || []).find((item) => item.id === id);
        openPasswordReferenceModal(row || null);
      } else if (action === 'delete-password-reference') {
        if (!window.confirm('Delete this password reference?')) return;
        await personalApiPost(`/api/personal-vault/password-references/${id}/delete/`, {});
        showToast('Password reference deleted');
        await loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
      }
    } catch (err) {
      showToast(err.message || 'Personal vault action failed');
    }
  });
}

function setupPersonalAutosaveBindings() {
  const bind = (id, step, events = ['input', 'change']) => {
    const field = document.getElementById(id);
    if (!field) return;
    events.forEach((eventName) => {
      field.addEventListener(eventName, () => schedulePersonalAutosave(step));
    });
  };

  ['vault-first-name', 'vault-last-name', 'vault-dob', 'vault-gender', 'vault-nationality'].forEach((id) => bind(id, 1));
  [
    'vault-primary-email',
    'vault-secondary-email',
    'vault-primary-phone',
    'vault-secondary-phone',
    'vault-home-address',
    'vault-city',
    'vault-country',
    'vault-postal-code',
  ].forEach((id) => bind(id, 2));
  ['vault-national-id', 'vault-passport-number', 'vault-passport-expiry', 'vault-drivers-license', 'vault-student-id'].forEach((id) => bind(id, 3));
  ['vault-linkedin', 'vault-twitter', 'vault-instagram', 'vault-github', 'vault-portfolio', 'vault-blog', 'vault-youtube'].forEach((id) => bind(id, 5));
}

function setupPersonalPage() {
  if (!isPersonalPage()) return;
  if (personalState.isSetup) {
    loadPersonalVaultBootstrap({ preserveStep: true, silent: true });
    return;
  }
  personalState.isSetup = true;

  const bind = (id, eventName, handler) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(eventName, handler);
  };

  bind('personal-refresh-btn', 'click', () => loadPersonalVaultBootstrap({ preserveStep: true }));
  bind('save-step1-btn', 'click', async () => {
    try {
      await savePersonalStep1({ goNext: true });
    } catch (err) {
      showToast(err.message || 'Unable to save step 1');
    }
  });
  bind('save-step2-btn', 'click', async () => {
    try {
      await savePersonalStep2({ goNext: true });
    } catch (err) {
      showToast(err.message || 'Unable to save step 2');
    }
  });
  bind('save-step3-btn', 'click', async () => {
    try {
      await savePersonalStep3({ goNext: true });
    } catch (err) {
      showToast(err.message || 'Unable to save step 3');
    }
  });
  bind('save-step5-btn', 'click', async () => {
    try {
      await savePersonalStep5({ goNext: true });
    } catch (err) {
      showToast(err.message || 'Unable to save step 5');
    }
  });
  bind('save-vault-btn', 'click', async () => {
    try {
      await saveCurrentPersonalStep({ silent: false });
    } catch (err) {
      showToast(err.message || 'Unable to sync vault');
    }
  });

  bind('add-digital-account-btn', 'click', () => openDigitalAccountModal(null));
  bind('add-password-reference-btn', 'click', () => openPasswordReferenceModal(null));
  bind('apply-account-filters-btn', 'click', () => {
    personalState.filters.accountSearch = (document.getElementById('vault-account-search')?.value || '').trim();
    personalState.filters.accountPlatform = (document.getElementById('vault-account-platform-filter')?.value || '').trim();
    renderDigitalAccountsTable();
  });

  bind('upload-identity-file-btn', 'click', uploadIdentityVaultFile);
  bind('vault-identity-file', 'change', (event) => {
    const file = event.target?.files?.[0];
    if (!file) return;
    personalState.pendingIdentityFile = file;
  });
  bind('vault-profile-photo', 'change', async (event) => {
    const file = event.target?.files?.[0];
    if (file) await handlePersonalProfilePhotoSelection(file);
  });

  bind('vault-digital-account-form', 'submit', submitDigitalAccountForm);
  bind('vault-password-reference-form', 'submit', submitPasswordReferenceForm);

  bindPersonalTagInput('vault-language-input', 'add-language-tag-btn', 'languages');
  bindPersonalTagInput('vault-additional-email-input', 'add-email-btn', 'additionalEmails');
  bindPersonalTagInput('vault-other-phone-input', 'add-phone-btn', 'otherPhones');

  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => closeModal(el.dataset.closeModal));
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) overlay.classList.add('hidden');
    });
  });

  document.addEventListener('keydown', (event) => {
    if (!isPersonalPage()) return;
    if (event.key === 'Escape') {
      closeAllModals();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      saveCurrentPersonalStep({ silent: false }).catch((err) => showToast(err.message || 'Unable to save'));
    }
  });

  const accountSearch = document.getElementById('vault-account-search');
  if (accountSearch) {
    accountSearch.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      document.getElementById('apply-account-filters-btn')?.click();
    });
  }

  ['vault-linkedin', 'vault-twitter', 'vault-instagram', 'vault-github', 'vault-portfolio', 'vault-blog', 'vault-youtube'].forEach((id) => {
    const field = document.getElementById(id);
    if (!field) return;
    field.addEventListener('input', () => {
      personalState.socialProfiles = {
        ...personalState.socialProfiles,
        ...getPersonalStep5Payload(),
      };
      renderSocialPreview();
    });
  });

  setupPersonalDropzones();
  setupPersonalAutosaveBindings();
  attachPersonalActionDelegates();
  loadPersonalVaultBootstrap();
}

function isEducationPage() {
  return getActivePage() === 'education';
}

function educationApiGet(path, query = null) {
  if (query) {
    const params = new URLSearchParams(query);
    return apiRequest(`${path}?${params.toString()}`);
  }
  return apiRequest(path);
}

function educationApiPost(path, payload) {
  return apiRequest(path, 'POST', payload || {});
}

function formatDateDisplay(value) {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-KE', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getStatusChipClass(status) {
  if (status === 'completed' || status === 'accepted') return 'status-completed';
  if (status === 'in_progress' || status === 'preparing_documents' || status === 'interview_stage') return 'status-inprogress';
  return 'status-idea';
}

function getScholarshipDaysLeft(deadline) {
  if (!deadline) return null;
  const d = new Date(deadline);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  const diffMs = d.getTime() - now.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

async function loadDashboardEducationAlerts() {
  const banner = document.getElementById('dashboard-education-alert-banner');
  const list = document.getElementById('dashboard-education-alert-list');
  if (!banner || !list || !isAuthenticated()) return;
  try {
    const payload = await educationApiGet('/api/education/deadline-alerts/');
    const rows = payload.rows || [];
    if (!rows.length) {
      banner.innerHTML = '<i class=\"fas fa-circle-check\"></i> No urgent education deadlines.';
      list.innerHTML = '<div class=\"table-empty\">Everything is on track.</div>';
      return;
    }
    banner.innerHTML = `<i class=\"fas fa-exclamation-triangle\"></i> ${escapeHtml(rows[0].message)}`;
    list.innerHTML = rows.slice(0, 3).map((row) => `
      <a class=\"compact-list-item\" href=\"/education/\">\n        <span class=\"compact-date\">${row.days_left}d</span>\n        <span class=\"compact-copy\">${escapeHtml(row.message)}</span>\n      </a>
    `).join('');
  } catch (err) {
    banner.innerHTML = '<i class=\"fas fa-triangle-exclamation\"></i> Unable to load education alerts right now.';
  }
}

function renderEducationAlerts(alerts = []) {
  educationState.deadlineAlerts = alerts.slice();
  const banner = document.getElementById('education-alert-banner');
  const list = document.getElementById('education-deadline-alerts');
  if (!banner || !list) return;

  if (!alerts.length) {
    banner.innerHTML = '<i class=\"fas fa-circle-check\"></i> No urgent scholarship deadlines right now.';
    list.innerHTML = '';
    return;
  }

  banner.innerHTML = `<i class=\"fas fa-clock\"></i> ${escapeHtml(alerts[0].message)}`;
  list.innerHTML = alerts.slice(0, 8).map((item) => `
    <div class=\"education-alert-item\">
      <span>${escapeHtml(item.message)}</span>
      <span class=\"days\">${item.days_left}d</span>
    </div>
  `).join('');
}

function renderAcademicLevels(levels = []) {
  educationState.levels = levels.slice();
  const grid = document.getElementById('academic-level-grid');
  if (!grid) return;
  if (!levels.length) {
    grid.innerHTML = '<div class=\"table-empty\">No academic levels added yet.</div>';
    return;
  }

  grid.innerHTML = levels.map((level) => {
    const statusClass = getStatusChipClass(level.status);
    const years = [level.start_year, level.end_year].filter(Boolean).join(' - ') || 'Timeline not set';
    const examCount = (level.exam_certifications || []).length;
    return `
      <div class=\"education-level-card\">
        <div class=\"education-card-head\">
          <div>
            <div class=\"education-title\">${escapeHtml(level.level_label)}</div>
            <div class=\"education-subtitle\">${escapeHtml(level.school_name || level.university_name || 'Not specified')}</div>
          </div>
          <span class=\"card-status ${statusClass}\">${escapeHtml((level.status || 'planned').replace('_', ' '))}</span>
        </div>
        <div class=\"education-details\">
          <div class=\"education-detail\"><strong>Location:</strong> ${escapeHtml(level.location || level.country || '—')}</div>
          <div class=\"education-detail\"><strong>Years:</strong> ${escapeHtml(years)}</div>
          <div class=\"education-detail\"><strong>Adm/Student #:</strong> ${escapeHtml(level.admission_number || level.student_number || '—')}</div>
          <div class=\"education-detail\"><strong>GPA/Grade:</strong> ${escapeHtml(level.gpa || level.grades || '—')}</div>
        </div>
        <div class=\"education-expand\">
          <div class=\"education-detail\"><strong>Subjects:</strong> ${escapeHtml(level.subjects_taken || '—')}</div>
          <div class=\"education-detail\"><strong>Research:</strong> ${escapeHtml(level.research_topic || '—')}</div>
          <div class=\"education-detail\"><strong>Internships:</strong> ${escapeHtml(level.internships || '—')}</div>
          <div class=\"education-detail\"><strong>Clubs:</strong> ${escapeHtml(level.clubs_activities || '—')}</div>
          <div class=\"education-detail\"><strong>Awards:</strong> ${escapeHtml(level.awards || '—')}</div>
          <div class=\"education-detail\"><strong>Exam Toggle:</strong> ${level.certification_exam_completed ? 'Yes' : 'No'} (${examCount} exam record${examCount === 1 ? '' : 's'})</div>
          <div class=\"education-detail\"><strong>Certificate:</strong> ${level.certificate_url ? `<a href=\"${escapeHtml(level.certificate_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a>` : '—'}</div>
          <div class=\"education-detail\"><strong>Transcript:</strong> ${level.transcript_url ? `<a href=\"${escapeHtml(level.transcript_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a>` : '—'}</div>
        </div>
        <div class=\"action-cell\">
          <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-level\" data-id=\"${level.id}\">Edit</button>
          <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"add-level-exam\" data-id=\"${level.id}\">Add Exam</button>
          <button class=\"btn-outline btn-mini danger\" type=\"button\" data-action=\"delete-level\" data-id=\"${level.id}\">Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

function renderExamTable(levels = []) {
  educationState.exams = [];
  levels.forEach((level) => {
    (level.exam_certifications || []).forEach((exam) => {
      educationState.exams.push({
        ...exam,
        level_label: level.level_label,
      });
    });
  });

  const body = document.getElementById('exam-table-body');
  if (!body) return;
  if (!educationState.exams.length) {
    body.innerHTML = '<tr><td colspan=\"7\" class=\"table-empty\">No exam records yet.</td></tr>';
    return;
  }

  body.innerHTML = educationState.exams.map((row) => `
    <tr>
      <td>${escapeHtml(row.level_label || '—')}</td>
      <td>${escapeHtml(row.exam_name || '')}</td>
      <td>${escapeHtml(row.exam_year || '—')}</td>
      <td>${escapeHtml(row.candidate_number || '—')}</td>
      <td>${escapeHtml(row.grade_score || '—')}</td>
      <td>${row.certificate_url ? `<a href=\"${escapeHtml(row.certificate_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a>` : '—'}</td>
      <td class=\"action-cell\">\n        <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-exam\" data-id=\"${row.id}\">Edit</button>\n        <button class=\"btn-outline btn-mini danger\" type=\"button\" data-action=\"delete-exam\" data-id=\"${row.id}\">Delete</button>\n      </td>
    </tr>
  `).join('');
}

function renderDocumentVault(rows = []) {
  educationState.documents = rows.slice();
  const body = document.getElementById('document-table-body');
  if (!body) return;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan=\"6\" class=\"table-empty\">No documents uploaded yet.</td></tr>';
    return;
  }

  body.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.title || '')}</td>
      <td>${escapeHtml(row.document_type_label || row.document_type || '')}</td>
      <td>${escapeHtml(row.version || 'v1')}</td>
      <td>${escapeHtml(formatDateDisplay(row.expiration_date))}</td>
      <td>${escapeHtml(formatDateDisplay(row.updated_at))}</td>
      <td class=\"action-cell\">
        <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-document\" data-id=\"${row.id}\">Edit</button>
        <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"download-document\" data-id=\"${row.id}\">Download</button>
        <button class=\"btn-outline btn-mini danger\" type=\"button\" data-action=\"delete-document\" data-id=\"${row.id}\">Delete</button>
      </td>
    </tr>
  `).join('');
}

function filterScholarships(rows = []) {
  const q = (educationState.filters.q || '').toLowerCase();
  const status = educationState.filters.status || '';
  return rows.filter((row) => {
    const appStatus = row.application?.status || '';
    const searchable = `${row.name || ''} ${row.country || ''} ${row.university || ''} ${row.field_of_study || ''}`.toLowerCase();
    if (q && !searchable.includes(q)) return false;
    if (status && status !== appStatus) return false;
    return true;
  });
}

function renderScholarships(rows = []) {
  educationState.scholarships = rows.slice();
  const grid = document.getElementById('scholarship-grid');
  if (!grid) return;
  const filtered = filterScholarships(rows);

  if (!filtered.length) {
    grid.innerHTML = '<div class=\"table-empty\">No scholarships match your current filters.</div>';
    return;
  }

  grid.innerHTML = filtered.map((row) => {
    const daysLeft = getScholarshipDaysLeft(row.application_deadline);
    const app = row.application || {};
    const statusClass = app.result_badge || 'pending';
    return `
      <div class=\"education-scholarship-card\">
        <div class=\"education-card-head\">
          <div>
            <div class=\"education-title\">${escapeHtml(row.name || '')}</div>
            <div class=\"education-subtitle\">${escapeHtml(row.country || 'Country not set')} · ${escapeHtml(row.field_of_study || 'Field not set')}</div>
          </div>
          <span class=\"scholarship-result ${statusClass}\">${statusClass === 'accepted' ? '🟢 Accepted' : statusClass === 'rejected' ? '🔴 Rejected' : '🟡 Pending'}</span>
        </div>
        <div class=\"education-details\">
          <div class=\"education-detail\"><strong>University:</strong> ${escapeHtml(row.university || '—')}</div>
          <div class=\"education-detail\"><strong>Degree:</strong> ${escapeHtml(row.degree_level || '—')}</div>
          <div class=\"education-detail\"><strong>Deadline:</strong> ${escapeHtml(formatDateDisplay(row.application_deadline))}</div>
          <div class=\"education-detail\"><strong>Countdown:</strong> ${daysLeft === null ? '—' : `${daysLeft} day${daysLeft === 1 ? '' : 's'}`}</div>
          <div class=\"education-detail\"><strong>Status:</strong> ${escapeHtml(app.status_label || 'Researching')}</div>
          <div class=\"education-detail\"><strong>Application ID:</strong> ${escapeHtml(app.application_id || '—')}</div>
          <div class=\"education-detail\"><strong>Submitted:</strong> ${app.is_submitted ? 'Yes' : 'No'}</div>
          <div class=\"education-detail\"><strong>Submission Date:</strong> ${escapeHtml(formatDateDisplay(app.submission_date))}</div>
        </div>
        <div class=\"education-progress-track\"><div class=\"education-progress-fill\" style=\"width:${row.progress_pct || 0}%\"></div></div>
        <div class=\"progress-label\"><span>${row.requirements_completed}/${row.requirements_total} requirements</span><span>${row.progress_pct || 0}%</span></div>
        <div class=\"education-checklist\">
          ${(row.requirements || []).map((req) => `
            <div class=\"education-check-item\">
              <div class=\"left\">
                <button class=\"check-box ${req.is_completed ? 'checked' : ''}\" type=\"button\" data-action=\"toggle-requirement\" data-id=\"${req.id}\">${req.is_completed ? CHECK_ICON_SMALL : ''}</button>
                <span>${escapeHtml(req.requirement_name)}</span>
              </div>
              <div class=\"action-cell\">
                ${req.linked_document_title ? `<span class=\"tag\">${escapeHtml(req.linked_document_title)}</span>` : ''}
                <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-requirement\" data-id=\"${req.id}\" data-scholarship-id=\"${row.id}\">Edit</button>
                <button class=\"btn-outline btn-mini danger\" type=\"button\" data-action=\"delete-requirement\" data-id=\"${req.id}\">Delete</button>
              </div>
            </div>
          `).join('')}
        </div>
        <div class=\"action-cell\">
          <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-scholarship\" data-id=\"${row.id}\">Edit Scholarship</button>
          <button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"add-requirement\" data-scholarship-id=\"${row.id}\">Add Requirement</button>
          ${app.id ? `<button class=\"btn-outline btn-mini\" type=\"button\" data-action=\"edit-application\" data-id=\"${app.id}\">Application Data</button>` : ''}
          <button class=\"btn-outline btn-mini danger\" type=\"button\" data-action=\"delete-scholarship\" data-id=\"${row.id}\">Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

function updateEducationSelects() {
  const levelSelect = document.getElementById('education-exam-level');
  if (levelSelect) {
    const current = levelSelect.value;
    levelSelect.innerHTML = '<option value=\"\">Select level</option>' + educationState.levels.map((row) => `<option value=\"${row.id}\">${escapeHtml(row.level_label)} · ${escapeHtml(row.school_name || row.university_name || 'Untitled')}</option>`).join('');
    levelSelect.value = current || '';
  }

  const linkedDoc = document.getElementById('education-linked-document');
  if (linkedDoc) {
    const current = linkedDoc.value;
    linkedDoc.innerHTML = '<option value=\"\">None</option>' + educationState.documents.map((doc) => `<option value=\"${doc.id}\">${escapeHtml(doc.title)} (${escapeHtml(doc.version || 'v1')})</option>`).join('');
    linkedDoc.value = current || '';
  }
}

async function loadEducationBootstrap() {
  if (!isEducationPage() || !isAuthenticated()) return;
  try {
    const payload = await educationApiGet('/api/education/bootstrap/');
    renderEducationAlerts(payload.deadline_alerts || []);
    renderAcademicLevels(payload.academic_levels || []);
    renderExamTable(payload.academic_levels || []);
    renderDocumentVault(payload.documents || []);
    renderScholarships(payload.scholarships || []);
    updateEducationSelects();
  } catch (err) {
    showToast(err.message || 'Failed to load education workspace');
  }
}

function openEducationLevelModal(row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-level-id', row?.id || '');
  set('education-level-type', row?.level_type || 'primary');
  set('education-level-status', row?.status || 'planned');
  set('education-school-name', row?.school_name || '');
  set('education-admission-number', row?.admission_number || '');
  set('education-location', row?.location || '');
  set('education-start-year', row?.start_year || '');
  set('education-end-year', row?.end_year || '');
  set('education-expected-grad-year', row?.expected_graduation_year || '');
  set('education-subjects', row?.subjects_taken || '');
  set('education-grades', row?.grades || '');
  set('education-certification-toggle', row?.certification_exam_completed ? '1' : '0');
  set('education-university-name', row?.university_name || '');
  set('education-country', row?.country || '');
  set('education-degree', row?.degree || '');
  set('education-major-program', row?.major_program || '');
  set('education-gpa', row?.gpa || '');
  set('education-research-topic', row?.research_topic || '');
  set('education-internships', row?.internships || '');
  set('education-clubs', row?.clubs_activities || '');
  set('education-awards', row?.awards || '');
  set('education-level-notes', row?.notes || '');
  const title = document.getElementById('education-level-modal-title');
  if (title) title.textContent = row ? 'Edit Academic Level' : 'Add Academic Level';
  openModal('education-level-modal-overlay');
}

async function submitEducationLevelForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-level-id').value;
  const formData = new FormData();
  const append = (key, val) => formData.append(key, val ?? '');
  append('level_type', document.getElementById('education-level-type')?.value);
  append('status', document.getElementById('education-level-status')?.value);
  append('school_name', document.getElementById('education-school-name')?.value);
  append('admission_number', document.getElementById('education-admission-number')?.value);
  append('location', document.getElementById('education-location')?.value);
  append('start_year', document.getElementById('education-start-year')?.value);
  append('end_year', document.getElementById('education-end-year')?.value);
  append('expected_graduation_year', document.getElementById('education-expected-grad-year')?.value);
  append('subjects_taken', document.getElementById('education-subjects')?.value);
  append('grades', document.getElementById('education-grades')?.value);
  append('certification_exam_completed', document.getElementById('education-certification-toggle')?.value === '1' ? '1' : '0');
  append('university_name', document.getElementById('education-university-name')?.value);
  append('country', document.getElementById('education-country')?.value);
  append('degree', document.getElementById('education-degree')?.value);
  append('major_program', document.getElementById('education-major-program')?.value);
  append('gpa', document.getElementById('education-gpa')?.value);
  append('research_topic', document.getElementById('education-research-topic')?.value);
  append('internships', document.getElementById('education-internships')?.value);
  append('clubs_activities', document.getElementById('education-clubs')?.value);
  append('awards', document.getElementById('education-awards')?.value);
  append('notes', document.getElementById('education-level-notes')?.value);
  const certificate = document.getElementById('education-certificate-file')?.files?.[0];
  const transcript = document.getElementById('education-transcript-file')?.files?.[0];
  if (certificate) formData.append('certificate_file', certificate);
  if (transcript) formData.append('transcript_file', transcript);

  try {
    if (id) await apiRequestForm(`/api/education/levels/${id}/update/`, formData);
    else await apiRequestForm('/api/education/levels/create/', formData);
    closeModal('education-level-modal-overlay');
    showToast(`Academic level ${id ? 'updated' : 'created'}`);
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save academic level');
  }
}

function openEducationExamModal(row = null, levelId = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-exam-id', row?.id || '');
  set('education-exam-level', row?.academic_level_id || levelId || '');
  set('education-exam-name', row?.exam_name || '');
  set('education-exam-year', row?.exam_year || '');
  set('education-candidate-number', row?.candidate_number || '');
  set('education-grade-score', row?.grade_score || '');
  set('education-exam-notes', row?.notes || '');
  const title = document.getElementById('education-exam-modal-title');
  if (title) title.textContent = row ? 'Edit Certification Exam' : 'Add Certification Exam';
  openModal('education-exam-modal-overlay');
}

async function submitEducationExamForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-exam-id').value;
  const formData = new FormData();
  formData.append('academic_level_id', document.getElementById('education-exam-level')?.value || '');
  formData.append('exam_name', document.getElementById('education-exam-name')?.value || '');
  formData.append('exam_year', document.getElementById('education-exam-year')?.value || '');
  formData.append('candidate_number', document.getElementById('education-candidate-number')?.value || '');
  formData.append('grade_score', document.getElementById('education-grade-score')?.value || '');
  formData.append('notes', document.getElementById('education-exam-notes')?.value || '');
  const cert = document.getElementById('education-exam-certificate-file')?.files?.[0];
  if (cert) formData.append('certificate_file', cert);

  try {
    if (id) await apiRequestForm(`/api/education/exams/${id}/update/`, formData);
    else await apiRequestForm('/api/education/exams/create/', formData);
    closeModal('education-exam-modal-overlay');
    showToast(`Exam ${id ? 'updated' : 'created'}`);
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save exam');
  }
}

function openEducationScholarshipModal(row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-scholarship-id', row?.id || '');
  set('education-scholarship-name', row?.name || '');
  set('education-scholarship-country', row?.country || '');
  set('education-scholarship-university', row?.university || '');
  set('education-scholarship-field', row?.field_of_study || '');
  set('education-scholarship-degree', row?.degree_level || '');
  set('education-scholarship-website', row?.official_website || '');
  set('education-scholarship-deadline', row?.application_deadline || '');
  set('education-tuition-coverage', row?.tuition_coverage || '');
  set('education-monthly-stipend', row?.monthly_stipend || '');
  set('education-travel-coverage', row?.travel_coverage ? '1' : '0');
  set('education-accommodation', row?.accommodation ? '1' : '0');
  set('education-other-benefits', row?.other_benefits || '');
  const title = document.getElementById('education-scholarship-modal-title');
  if (title) title.textContent = row ? 'Edit Scholarship' : 'Add Scholarship';
  openModal('education-scholarship-modal-overlay');
}

async function submitEducationScholarshipForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-scholarship-id').value;
  const payload = {
    name: document.getElementById('education-scholarship-name')?.value,
    country: document.getElementById('education-scholarship-country')?.value,
    university: document.getElementById('education-scholarship-university')?.value,
    field_of_study: document.getElementById('education-scholarship-field')?.value,
    degree_level: document.getElementById('education-scholarship-degree')?.value,
    official_website: document.getElementById('education-scholarship-website')?.value,
    application_deadline: document.getElementById('education-scholarship-deadline')?.value || null,
    tuition_coverage: document.getElementById('education-tuition-coverage')?.value,
    monthly_stipend: document.getElementById('education-monthly-stipend')?.value || null,
    travel_coverage: document.getElementById('education-travel-coverage')?.value === '1',
    accommodation: document.getElementById('education-accommodation')?.value === '1',
    other_benefits: document.getElementById('education-other-benefits')?.value,
  };
  try {
    if (id) await educationApiPost(`/api/education/scholarships/${id}/update/`, payload);
    else await educationApiPost('/api/education/scholarships/create/', payload);
    closeModal('education-scholarship-modal-overlay');
    showToast(`Scholarship ${id ? 'updated' : 'created'}`);
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save scholarship');
  }
}

function openEducationApplicationModal(row = null) {
  if (!row) return;
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-application-id', row.id || '');
  set('education-application-status', row.status || 'researching');
  set('education-is-submitted', row.is_submitted ? '1' : '0');
  set('education-submission-date', row.submission_date || '');
  set('education-application-id-field', row.application_id || '');
  set('education-portal-link', row.portal_link || '');
  set('education-application-notes', row.notes || '');
  openModal('education-application-modal-overlay');
}

async function submitEducationApplicationForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-application-id').value;
  if (!id) {
    showToast('Application record is missing.');
    return;
  }
  const payload = {
    status: document.getElementById('education-application-status')?.value,
    is_submitted: document.getElementById('education-is-submitted')?.value === '1',
    submission_date: document.getElementById('education-submission-date')?.value || null,
    application_id: document.getElementById('education-application-id-field')?.value,
    portal_link: document.getElementById('education-portal-link')?.value,
    notes: document.getElementById('education-application-notes')?.value,
  };
  try {
    await educationApiPost(`/api/education/applications/${id}/update/`, payload);
    closeModal('education-application-modal-overlay');
    showToast('Application updated');
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to update application');
  }
}

function openEducationRequirementModal(scholarshipId, row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-requirement-id', row?.id || '');
  set('education-requirement-scholarship-id', scholarshipId || row?.scholarship_id || '');
  set('education-requirement-name', row?.requirement_name || '');
  set('education-requirement-sort', row?.sort_order ?? 0);
  set('education-requirement-required', row?.is_required ? '1' : '0');
  set('education-requirement-completed', row?.is_completed ? '1' : '0');
  set('education-linked-document', row?.linked_document_id || '');
  const title = document.getElementById('education-requirement-modal-title');
  if (title) title.textContent = row ? 'Edit Requirement' : 'Add Requirement';
  openModal('education-requirement-modal-overlay');
}

async function submitEducationRequirementForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-requirement-id').value;
  const payload = {
    scholarship_id: Number(document.getElementById('education-requirement-scholarship-id')?.value || 0),
    requirement_name: document.getElementById('education-requirement-name')?.value,
    sort_order: Number(document.getElementById('education-requirement-sort')?.value || 0),
    is_required: document.getElementById('education-requirement-required')?.value === '1',
    is_completed: document.getElementById('education-requirement-completed')?.value === '1',
    linked_document_id: document.getElementById('education-linked-document')?.value || null,
  };
  try {
    if (id) await educationApiPost(`/api/education/requirements/${id}/update/`, payload);
    else await educationApiPost('/api/education/requirements/create/', payload);
    closeModal('education-requirement-modal-overlay');
    showToast(`Requirement ${id ? 'updated' : 'created'}`);
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save requirement');
  }
}

function openEducationDocumentModal(row = null) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  };
  set('education-document-id', row?.id || '');
  set('education-document-title', row?.title || '');
  set('education-document-type', row?.document_type || 'other');
  set('education-document-version', row?.version || 'v1');
  set('education-document-expiration', row?.expiration_date || '');
  set('education-document-notes', row?.notes || '');
  const title = document.getElementById('education-document-modal-title');
  if (title) title.textContent = row ? 'Edit Document' : 'Add Document';
  openModal('education-document-modal-overlay');
}

async function submitEducationDocumentForm(event) {
  event.preventDefault();
  const id = document.getElementById('education-document-id').value;
  const fileInput = document.getElementById('education-document-file');
  const selectedFile = fileInput?.files?.[0] || educationState.pendingDocumentFile || null;
  const formData = new FormData();
  formData.append('title', document.getElementById('education-document-title')?.value || '');
  formData.append('document_type', document.getElementById('education-document-type')?.value || 'other');
  formData.append('version', document.getElementById('education-document-version')?.value || 'v1');
  formData.append('expiration_date', document.getElementById('education-document-expiration')?.value || '');
  formData.append('notes', document.getElementById('education-document-notes')?.value || '');
  if (selectedFile) formData.append('file', selectedFile);

  try {
    if (id) await apiRequestForm(`/api/education/documents/${id}/update/`, formData);
    else await apiRequestForm('/api/education/documents/create/', formData);
    educationState.pendingDocumentFile = null;
    closeModal('education-document-modal-overlay');
    showToast(`Document ${id ? 'updated' : 'uploaded'}`);
    await loadEducationBootstrap();
  } catch (err) {
    showToast(err.message || 'Unable to save document');
  }
}

function getScholarshipById(id) {
  return educationState.scholarships.find((item) => item.id === id);
}

function getRequirementById(id) {
  for (const scholarship of educationState.scholarships) {
    const req = (scholarship.requirements || []).find((item) => item.id === id);
    if (req) return { requirement: req, scholarship };
  }
  return null;
}

function setupEducationDropzone() {
  const zone = document.getElementById('education-document-drop-zone');
  if (!zone) return;
  const prevent = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((evt) => zone.addEventListener(evt, prevent));
  ['dragenter', 'dragover'].forEach((evt) => zone.addEventListener(evt, () => zone.classList.add('dragover')));
  ['dragleave', 'drop'].forEach((evt) => zone.addEventListener(evt, () => zone.classList.remove('dragover')));

  zone.addEventListener('drop', (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    educationState.pendingDocumentFile = file;
    openEducationDocumentModal(null);
    showToast(`Attached ${file.name} to document form`);
  });
}

function setupEducationPage() {
  if (!isEducationPage()) return;
  if (educationState.isSetup) {
    loadEducationBootstrap();
    return;
  }
  educationState.isSetup = true;

  const bind = (id, eventName, handler) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(eventName, handler);
  };

  bind('quick-add-level-btn', 'click', () => openEducationLevelModal(null));
  bind('quick-add-scholarship-btn', 'click', () => openEducationScholarshipModal(null));
  bind('quick-add-document-btn', 'click', () => openEducationDocumentModal(null));
  bind('add-level-btn', 'click', () => openEducationLevelModal(null));
  bind('add-exam-btn', 'click', () => openEducationExamModal(null));
  bind('add-scholarship-btn', 'click', () => openEducationScholarshipModal(null));
  bind('add-document-btn', 'click', () => openEducationDocumentModal(null));
  bind('apply-scholarship-filters-btn', 'click', () => {
    educationState.filters.q = (document.getElementById('scholarship-search')?.value || '').trim();
    educationState.filters.status = (document.getElementById('scholarship-status-filter')?.value || '').trim();
    renderScholarships(educationState.scholarships);
  });

  bind('education-level-form', 'submit', submitEducationLevelForm);
  bind('education-exam-form', 'submit', submitEducationExamForm);
  bind('education-scholarship-form', 'submit', submitEducationScholarshipForm);
  bind('education-application-form', 'submit', submitEducationApplicationForm);
  bind('education-requirement-form', 'submit', submitEducationRequirementForm);
  bind('education-document-form', 'submit', submitEducationDocumentForm);

  const page = document.getElementById('page-education');
  if (page) {
    page.addEventListener('click', async (event) => {
      const btn = event.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.dataset.action;
      const id = Number(btn.dataset.id || 0);
      const scholarshipId = Number(btn.dataset.scholarshipId || 0);
      try {
        if (action === 'edit-level') {
          const row = educationState.levels.find((item) => item.id === id);
          openEducationLevelModal(row || null);
        } else if (action === 'delete-level') {
          if (!window.confirm('Delete this academic level?')) return;
          await educationApiPost(`/api/education/levels/${id}/delete/`, {});
          await loadEducationBootstrap();
        } else if (action === 'add-level-exam') {
          openEducationExamModal(null, id);
        } else if (action === 'edit-exam') {
          const row = educationState.exams.find((item) => item.id === id);
          openEducationExamModal(row || null);
        } else if (action === 'delete-exam') {
          if (!window.confirm('Delete this exam record?')) return;
          await educationApiPost(`/api/education/exams/${id}/delete/`, {});
          await loadEducationBootstrap();
        } else if (action === 'edit-scholarship') {
          const row = getScholarshipById(id);
          openEducationScholarshipModal(row || null);
        } else if (action === 'delete-scholarship') {
          if (!window.confirm('Delete this scholarship and linked tracker data?')) return;
          await educationApiPost(`/api/education/scholarships/${id}/delete/`, {});
          await loadEducationBootstrap();
        } else if (action === 'edit-application') {
          let target = null;
          for (const row of educationState.scholarships) {
            if (row.application?.id === id) {
              target = row.application;
              break;
            }
          }
          openEducationApplicationModal(target);
        } else if (action === 'add-requirement') {
          openEducationRequirementModal(scholarshipId, null);
        } else if (action === 'edit-requirement') {
          const found = getRequirementById(id);
          openEducationRequirementModal(Number(btn.dataset.scholarshipId || found?.scholarship?.id || 0), found?.requirement || null);
        } else if (action === 'delete-requirement') {
          if (!window.confirm('Delete this requirement?')) return;
          await educationApiPost(`/api/education/requirements/${id}/delete/`, {});
          await loadEducationBootstrap();
        } else if (action === 'toggle-requirement') {
          await educationApiPost(`/api/education/requirements/${id}/toggle/`, {});
          await loadEducationBootstrap();
        } else if (action === 'edit-document') {
          const row = educationState.documents.find((item) => item.id === id);
          openEducationDocumentModal(row || null);
        } else if (action === 'download-document') {
          const row = educationState.documents.find((item) => item.id === id);
          if (row?.file_url) window.open(row.file_url, '_blank', 'noopener,noreferrer');
        } else if (action === 'delete-document') {
          if (!window.confirm('Delete this document from vault?')) return;
          await educationApiPost(`/api/education/documents/${id}/delete/`, {});
          await loadEducationBootstrap();
        }
      } catch (err) {
        showToast(err.message || 'Education action failed');
      }
    });
  }

  document.querySelectorAll('[data-close-modal]').forEach((el) => {
    el.addEventListener('click', () => closeModal(el.dataset.closeModal));
  });
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) overlay.classList.add('hidden');
    });
  });

  setupEducationDropzone();
  loadEducationBootstrap();
}

function toggleCheck(el) {
  el.classList.toggle('checked');
  el.innerHTML = el.classList.contains('checked') ? CHECK_ICON : '';
}

function selectMood(btn) {
  btn.closest('.mood-selector').querySelectorAll('.mood-btn').forEach((b) => b.classList.remove('selected'));
  btn.classList.add('selected');
}

function isTypingContext() {
  const active = document.activeElement;
  if (!active) return false;
  const tag = active.tagName;
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || active.isContentEditable;
}

function isNotificationsPage() {
  return getActivePage() === 'notifications';
}

function updateNotificationBadge(unreadCount = null) {
  const badge = document.getElementById('notif-badge');
  const label = document.getElementById('notif-count-label');
  const panel = document.getElementById('notif-panel');
  const fallbackUnread = Array.from(document.querySelectorAll('.notif-item')).filter((item) => item.classList.contains('unread')).length;
  const unread = Number.isFinite(Number(unreadCount))
    ? Number(unreadCount)
    : Number(panel?.dataset.unreadCount || fallbackUnread);
  if (badge) {
    badge.textContent = unread;
    badge.classList.toggle('is-visible', unread > 0);
  }
  if (label) label.textContent = `${unread} unread`;
  if (panel) panel.dataset.unreadCount = String(unread);
}

function syncNotificationSummary(summary = {}) {
  const unread = Number(summary.unread_count || 0);
  updateNotificationBadge(unread);

  const totalCount = document.getElementById('notifications-total-count');
  if (totalCount && summary.total_count !== undefined) {
    totalCount.textContent = String(summary.total_count);
  }

  const unreadCount = document.getElementById('notifications-unread-count');
  if (unreadCount && summary.unread_count !== undefined) {
    unreadCount.textContent = String(summary.unread_count);
  }
}

function getNotificationMarkReadUrl(notificationId, markUrl = null) {
  if (markUrl) return markUrl;
  return `/api/notifications/${encodeURIComponent(notificationId)}/mark-read/`;
}

function renderNotificationPanelRows(rows = [], summary = {}) {
  const panel = document.getElementById('notif-panel');
  if (!panel) return;

  const list = panel.querySelector('.notif-list');
  if (!list) return;

  syncNotificationSummary(summary);

  if (!rows.length) {
    list.innerHTML = `
      <div class="notif-empty">
        <div class="notif-empty-icon"><i class="fas fa-bell-slash"></i></div>
        <div class="notif-empty-title">All clear</div>
        <div class="notif-empty-copy">New reminders, finance alerts, and education deadlines will show up here.</div>
      </div>
    `;
    return;
  }

  list.innerHTML = rows.slice(0, NOTIFICATION_PANEL_LIMIT).map((row) => `
    <button
      type="button"
      class="notif-item notif-item--${escapeHtml(row.tone || 'info')}${row.is_read ? '' : ' unread'}"
      data-notification-id="${escapeHtml(row.id)}"
      data-mark-url="${escapeHtml(getNotificationMarkReadUrl(row.id, row.mark_read_url))}"
      data-url="${escapeHtml(row.url || '#')}"
      data-read="${row.is_read ? '1' : '0'}"
    >
      <span class="notif-icon notif-icon--${escapeHtml(row.tone || 'info')}"><i class="fas ${escapeHtml(row.icon || 'fa-bell')}"></i></span>
      <span class="notif-body">
        <span class="notif-row">
          <span class="notif-kicker">${escapeHtml(row.source_label || row.source || 'Update')}</span>
          <span class="notif-meta">${escapeHtml(row.time_label || '')}</span>
        </span>
        <span class="notif-text">${escapeHtml(row.title || 'Notification')}</span>
        <span class="notif-subtext">${escapeHtml(row.message || '')}</span>
        ${(row.chips || []).length ? `
          <span class="notif-chip-row">
            ${(row.chips || []).slice(0, 2).map((chip) => `<span class="notif-chip">${escapeHtml(chip)}</span>`).join('')}
          </span>
        ` : ''}
      </span>
      ${row.is_read ? '' : '<span class="notif-dot" aria-hidden="true"></span>'}
    </button>
  `).join('');
}

async function refreshNotificationInterfaces({ reloadPage = false } = {}) {
  try {
    const payload = await apiRequest('/api/notifications/');
    renderNotificationPanelRows(payload.rows || [], payload.summary || {});
  } catch (err) {
    updateNotificationBadge();
  }

  if (reloadPage && isNotificationsPage()) {
    navigateInApp(`${window.location.pathname}${window.location.search}${window.location.hash}`);
  }
}

async function markNotificationReadOnServer(notificationId, markUrl = null) {
  if (!notificationId) return;
  await apiRequest(getNotificationMarkReadUrl(notificationId, markUrl), 'POST', {});
}

async function markAllNotificationsReadOnServer() {
  await apiRequest('/api/notifications/mark-all-read/', 'POST', {});
}

function openNotifications() {
  const panel = document.getElementById('notif-panel');
  if (!panel) return;
  closeModal('quick-add-modal-overlay');
  closeCommandPalette();
  panel.classList.remove('hidden');
  panel.setAttribute('aria-hidden', 'false');
  updateNotificationBadge();
}

function closeNotifications() {
  const panel = document.getElementById('notif-panel');
  if (!panel) return;
  panel.classList.add('hidden');
  panel.setAttribute('aria-hidden', 'true');
}

function toggleQuickAdd(forceOpen = null) {
  const overlayId = 'quick-add-modal-overlay';
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  const shouldOpen = forceOpen !== null ? forceOpen : overlay.classList.contains('hidden');
  if (shouldOpen) {
    closeNotifications();
    closeCommandPalette();
    openQuickForm('task');
    openModal(overlayId);
  } else {
    closeModal(overlayId);
  }
}

function openQuickForm(type) {
  const formKey = String(type || 'task');
  document.querySelectorAll('.quick-add-option').forEach((option) => {
    option.classList.toggle('active', option.dataset.form === formKey);
  });
  document.querySelectorAll('.quick-add-form').forEach((form) => {
    form.classList.toggle('active', form.dataset.form === formKey);
  });
}

function setupNotifications() {
  const btn = document.getElementById('notifications-btn');
  const panel = document.getElementById('notif-panel');
  const markBtn = document.getElementById('notif-mark-read-btn');
  if (!btn || !panel) return;
  if (panel.dataset.notificationsReady === '1') return;
  panel.dataset.notificationsReady = '1';

  btn.addEventListener('click', (event) => {
    event.stopPropagation();
    if (panel.classList.contains('hidden')) openNotifications();
    else closeNotifications();
  });

  if (markBtn) {
    markBtn.addEventListener('click', async () => {
      try {
        await markAllNotificationsReadOnServer();
        await refreshNotificationInterfaces();
      } catch (err) {
        showToast(err.message || 'Unable to mark notifications as read');
      }
    });
  }

  panel.addEventListener('click', async (event) => {
    const item = event.target.closest('.notif-item');
    if (!item || !panel.contains(item)) return;

    const notificationId = item.dataset.notificationId;
    const url = item.dataset.url;
    const wasUnread = item.classList.contains('unread');
    if (wasUnread) {
      item.classList.remove('unread');
      item.dataset.read = '1';
    }
    closeNotifications();

    try {
      if (wasUnread && notificationId) {
        await markNotificationReadOnServer(notificationId, item.dataset.markUrl);
      }
      await refreshNotificationInterfaces();
    } catch (err) {
      showToast(err.message || 'Unable to update notification');
    }

    if (url && url !== '#') navigateInApp(url);
  });

  document.addEventListener('click', (event) => {
    if (panel.classList.contains('hidden')) return;
    if (panel.contains(event.target) || btn.contains(event.target)) return;
    closeNotifications();
  });

  updateNotificationBadge();
}

function setupNotificationCenterPage() {
  const page = document.getElementById('notifications-page');
  if (!page || page.dataset.notificationsPageReady === '1') return;
  page.dataset.notificationsPageReady = '1';

  const markAllBtn = document.getElementById('notification-page-mark-all-btn');
  if (markAllBtn) {
    markAllBtn.addEventListener('click', async () => {
      try {
        await markAllNotificationsReadOnServer();
        await refreshNotificationInterfaces({ reloadPage: true });
      } catch (err) {
        showToast(err.message || 'Unable to mark notifications as read');
      }
    });
  }

  page.addEventListener('click', async (event) => {
    const markReadBtn = event.target.closest('[data-notification-mark-read]');
    if (!markReadBtn || !page.contains(markReadBtn)) return;
    event.preventDefault();

    try {
      await markNotificationReadOnServer(markReadBtn.dataset.notificationMarkRead);
      await refreshNotificationInterfaces({ reloadPage: true });
    } catch (err) {
      showToast(err.message || 'Unable to mark notification as read');
    }
  });
}

function normalizeEndpointPath(endpoint) {
  if (!endpoint) return '';
  try {
    return new URL(endpoint, window.location.origin).pathname.toLowerCase();
  } catch (err) {
    return String(endpoint).split('?')[0].toLowerCase();
  }
}

function getTodayISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

async function ensureFinanceCategoryId() {
  try {
    const data = await apiRequest('/api/finance/categories/');
    const rows = data.rows || [];
    const active = rows.find((row) => row.is_active) || rows[0];
    if (active?.id) return active.id;
  } catch (err) {
    // Ignore and try to create a default category.
  }

  const basePayload = {
    name: 'General',
    slug: 'general',
    kind: 'expense',
    color: '#8B5A2B',
    icon: 'fa-wallet',
    is_active: true,
    sort_order: 0,
  };

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const payload = { ...basePayload };
    if (attempt === 1) {
      payload.slug = `general-${Date.now() % 100000}`;
    }
    try {
      const res = await apiRequest('/api/finance/categories/create/', 'POST', payload);
      if (res?.category?.id) return res.category.id;
    } catch (err) {
      // Try again with a different slug.
    }
  }

  try {
    const data = await apiRequest('/api/finance/categories/');
    const rows = data.rows || [];
    const fallback = rows[0];
    return fallback?.id || null;
  } catch (err) {
    return null;
  }
}

function refreshAfterQuickAdd(endpoint) {
  const path = normalizeEndpointPath(endpoint);
  if (!path) return;

  if (path.startsWith('/api/finance/')) {
    if (isFinancePage()) {
      loadFinanceBootstrap();
    } else {
      markFinanceNeedsRefresh();
    }
    return;
  }

  if (path.startsWith('/api/projects/')) {
    if (isProjectsPage()) loadProjects();
    return;
  }

  if (path.startsWith('/api/diary/')) {
    if (isDiaryPage()) {
      loadDiaryEntriesPage(1);
      loadDiaryStreak();
    }
    return;
  }

  if (path.startsWith('/api/bucket/') || path.startsWith('/bucket-list/')) {
    if (isBucketPage()) loadBucketGoals();
    return;
  }

  if (path.startsWith('/api/tasks/')) {
    if (getActivePage() === 'dashboard') loadBootstrapData();
    if (isRemindersPage()) loadRemindersHub();
    return;
  }

  if (path.startsWith('/api/reminders/')) {
    if (isRemindersPage()) loadRemindersHub();
    loadBootstrapData();
  }
}

async function submitQuickAddForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const endpoint = form.dataset.endpoint || form.getAttribute('action');
  const payload = {};
  new FormData(form).forEach((value, key) => {
    payload[key] = value;
  });

  if (!endpoint) {
    form.submit();
    return;
  }

  try {
    const endpointPath = normalizeEndpointPath(endpoint);
    if (endpointPath === '/api/finance/transactions/create/') {
      if (!payload.tx_date) payload.tx_date = getTodayISO();
      if (!payload.account) payload.account = 'bank';
      if (!payload.tx_type) payload.tx_type = 'expense';
      if (!payload.category_id) {
        const categoryId = await ensureFinanceCategoryId();
        if (categoryId) payload.category_id = categoryId;
      }
    }
    await apiRequest(endpoint, 'POST', payload);
    showToast('Item added successfully', 'success');
    closeModal('quick-add-modal-overlay');
    form.reset();
    refreshAfterQuickAdd(endpoint);
  } catch (err) {
    showToast('Something went wrong — please try again', 'error');
  }
}

function setupQuickAdd() {
  const btn = document.getElementById('quick-add-btn');
  const overlay = document.getElementById('quick-add-modal-overlay');
  if (btn) btn.addEventListener('click', () => toggleQuickAdd());
  document.querySelectorAll('.quick-add-form').forEach((form) => {
    form.addEventListener('submit', submitQuickAddForm);
  });
  if (overlay) {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeModal('quick-add-modal-overlay');
    });
  }
  document.querySelectorAll('[data-close-modal="quick-add-modal-overlay"]').forEach((el) => {
    el.addEventListener('click', () => closeModal('quick-add-modal-overlay'));
  });
}

function setupCommandPaletteOverlay() {
  const overlay = document.getElementById('command-palette-overlay');
  const input = document.getElementById('command-palette-input');
  const list = document.getElementById('command-palette-list');
  if (!overlay || !input || !list) return;

  input.addEventListener('input', () => filterCommands(input.value));
  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      moveCommandPaletteSelection(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      moveCommandPaletteSelection(-1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      executeCommandPaletteSelection();
    } else if (event.key === 'Escape') {
      closeCommandPalette();
    }
  });

  list.addEventListener('click', (event) => {
    const item = event.target.closest('.command-item');
    if (!item) return;
    const index = Number(item.dataset.commandIndex);
    if (Number.isInteger(index)) executeCommandPaletteSelection(index);
  });

  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) closeCommandPalette();
  });
}

function normalizeBucketValue(value) {
  return String(value || '').trim().toLowerCase();
}

function updateBucketProgress() {
  document.querySelectorAll('.bucket-goal-card').forEach((card) => {
    const rawStatus = normalizeBucketValue(card.dataset.status);
    const statusKey = rawStatus.replace(/_/g, ' ');
    let progress = Number(card.dataset.progress);
    if (!Number.isFinite(progress)) progress = null;
    if (statusKey === 'completed') {
      progress = 100;
    } else if (progress === null) {
      progress = statusKey.includes('progress') ? 60 : 0;
    }
    progress = Math.max(0, Math.min(100, progress));
    card.dataset.progress = String(progress);
    const fill = card.querySelector('.progress-fill');
    if (fill) fill.style.width = `${progress}%`;
    const percent = card.querySelector('.progress-percent');
    if (percent) percent.textContent = `${progress}%`;
    card.classList.toggle('is-completed', progress >= 100);
  });
}

function updateCategoryCounts() {
  const cards = Array.from(document.querySelectorAll('.bucket-goal-card'));
  const counts = { all: cards.length };

  cards.forEach((card) => {
    const key = normalizeBucketValue(card.dataset.category) || 'uncategorized';
    counts[key] = (counts[key] || 0) + 1;
  });

  document.querySelectorAll('.bucket-cat').forEach((cat) => {
    const raw = cat.dataset.category || cat.querySelector('.cat-name')?.textContent;
    const key = normalizeBucketValue(raw);
    const countEl = cat.querySelector('.cat-count');
    const serverCount = Number(cat.dataset.count);
    const total = Number.isFinite(serverCount)
      ? serverCount
      : (key === 'all' ? counts.all : (counts[key] || 0));
    if (countEl) countEl.textContent = total;
  });

  const empty = document.getElementById('bucket-empty');
  const grid = document.getElementById('bucket-grid');
  if (empty && grid) {
    const hasGoals = cards.length > 0;
    empty.classList.toggle('hidden', hasGoals);
    grid.classList.toggle('hidden', !hasGoals);
  }

  updateBucketProgress();
}

function openAddGoalModal(trigger = null) {
  const overlayId = 'bucket-goal-modal-overlay';
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;

  const form = document.getElementById('bucket-goal-form');
  const title = document.getElementById('bucket-goal-title');
  const description = document.getElementById('bucket-goal-description');
  const category = document.getElementById('bucket-goal-category');
  const status = document.getElementById('bucket-goal-status');
  const year = document.getElementById('bucket-goal-year');
  const cost = document.getElementById('bucket-goal-cost');
  const priority = document.getElementById('bucket-goal-priority');
  const modalTitle = document.getElementById('bucket-goal-modal-title');

  const setValue = (el, value) => {
    if (!el) return;
    el.value = value ?? '';
  };

  const goalId = trigger?.dataset?.goalId;
  if (goalId) {
    const card = document.querySelector(`.bucket-goal-card[data-goal-id="${goalId}"]`);
    const rawCategory = normalizeBucketValue(card?.dataset?.category);
    setValue(title, card?.dataset?.title || '');
    setValue(description, card?.dataset?.description || '');
    setValue(category, rawCategory || '');
    setValue(status, card?.dataset?.status || 'not_started');
    setValue(year, card?.dataset?.year || '');
    setValue(cost, card?.dataset?.cost || '');
    setValue(priority, card?.dataset?.priority || 'normal');
    if (form?.dataset?.editUrlTemplate) {
      form.action = form.dataset.editUrlTemplate.replace(/0\/?$/, `${goalId}/`);
    }
    if (modalTitle) modalTitle.textContent = 'Edit Bucket Goal';
  } else {
    setValue(title, '');
    setValue(description, '');
    setValue(category, '');
    setValue(status, 'not_started');
    setValue(year, '');
    setValue(cost, '');
    setValue(priority, 'normal');
    if (form?.dataset?.addUrl) {
      form.action = form.dataset.addUrl;
    }
    if (modalTitle) modalTitle.textContent = 'Add Bucket Goal';
  }

  openModal(overlayId);
}

function newDiaryEntry() {
  const now = new Date();
  document.getElementById('diary-current-date').textContent = now.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  if (document.getElementById('diary-main-text')) document.getElementById('diary-main-text').value = '';
  if (document.getElementById('diary-achievements')) document.getElementById('diary-achievements').value = '';
  if (document.getElementById('diary-lessons')) document.getElementById('diary-lessons').value = '';
  if (document.getElementById('diary-ideas')) document.getElementById('diary-ideas').value = '';
  showToast('Started a new diary entry');
}

function filterBucket(el, event) {
  if (!el) return;
  if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) return;
  if (event) event.preventDefault();
  document.querySelectorAll('.bucket-cat').forEach((c) => c.classList.remove('active'));
  el.classList.add('active');

  const activeCategory = normalizeBucketValue(el.dataset.category || el.querySelector('.cat-name')?.textContent);
  document.querySelectorAll('.bucket-goal-card').forEach((card) => {
    const cardCategory = normalizeBucketValue(card.dataset.category);
    const show = !activeCategory || activeCategory === 'all' || cardCategory === activeCategory;
    card.classList.toggle('hidden', !show);
  });

  const href = el.getAttribute('href');
  if (event && href && window.history && window.history.pushState) {
    window.history.pushState({}, '', href);
  }
}

function animateProgressBars() {
  if ('IntersectionObserver' in window) return;
  document.querySelectorAll('.progress-fill').forEach((fill) => {
    fill.classList.remove('is-animated');
    void fill.offsetWidth;
    fill.classList.add('is-animated');
  });
}

function toDateKey(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, '0');
  const d = String(dateObj.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function dashboardCalendarKey() {
  const focus = dashboardCalendarState.cursor;
  return `${focus.getFullYear()}-${String(focus.getMonth() + 1).padStart(2, '0')}`;
}

async function loadDashboardCalendarEvents({ force = false } = {}) {
  const grid = document.getElementById('dashboard-calendar-grid');
  if (!grid || dashboardCalendarState.isLoading) return;
  const key = dashboardCalendarKey();
  if (!force && dashboardCalendarState.loadedKey === key) return;

  dashboardCalendarState.isLoading = true;
  try {
    const [year, month] = key.split('-');
    const response = await fetch(`/api/calendar/events/?year=${year}&month=${Number(month)}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    });
    const payload = await response.json();
    dashboardCalendarState.events = payload.events || [];
    dashboardCalendarState.loadedKey = key;
    DASHBOARD_EVENT_DATES.clear();
    dashboardCalendarState.events.forEach((event) => {
      if (event.date) DASHBOARD_EVENT_DATES.add(event.date);
    });
    renderDashboardCalendar();
    renderDashboardSelectedDateAgenda();
  } catch (err) {
    dashboardCalendarState.events = [];
  } finally {
    dashboardCalendarState.isLoading = false;
  }
}

function eventRowsForDate(dateKey) {
  if (!dateKey) return [];
  const calendarEvents = dashboardCalendarState.events.filter((event) => sameDateKey(event.date, dateKey));
  const taskEvents = appState.tasks
    .filter((task) => sameDateKey(task.due_date, dateKey))
    .map((task) => ({
      id: `task-local-${task.id}`,
      type: 'task',
      title: task.title,
      date: task.due_date,
      is_done: task.is_done,
      color: task.is_done ? '#16a34a' : '#2563eb',
      url: PAGE_ROUTES.reminders,
    }));
  const seen = new Set();
  return [...calendarEvents, ...taskEvents].filter((item) => {
    const key = `${item.type}-${item.id || item.title}-${item.date}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function renderDashboardSelectedDateAgenda() {
  const label = document.getElementById('dashboard-selected-date-label');
  const list = document.getElementById('dashboard-selected-date-list');
  if (!label || !list) return;

  const selectedDate = dashboardCalendarState.selectedDate;
  if (!selectedDate) {
    label.textContent = 'Select a date to filter tasks.';
    list.innerHTML = '<div class="table-empty">No date selected.</div>';
    return;
  }

  label.textContent = formatDisplayDate(selectedDate);
  const rows = eventRowsForDate(selectedDate);
  if (!rows.length) {
    list.innerHTML = '<div class="table-empty">No tasks or reminders on this date.</div>';
    return;
  }

  list.innerHTML = rows.slice(0, 5).map((event) => `
    <a class="compact-list-item" href="${escapeHtml(event.url || PAGE_ROUTES.reminders)}" data-inapp-nav="true">
      <span class="compact-date" style="color:${escapeHtml(event.color || '#2563eb')}">${escapeHtml(event.type || 'event')}</span>
      <span class="compact-copy">${escapeHtml(event.title || 'Calendar item')}</span>
    </a>
  `).join('');
  enhanceInAppNavLinks(list);
}

function renderDashboardCalendar() {
  const monthLabel = document.getElementById('dashboard-calendar-month');
  const grid = document.getElementById('dashboard-calendar-grid');
  if (!monthLabel || !grid) return;

  const focus = dashboardCalendarState.cursor;
  const year = focus.getFullYear();
  const month = focus.getMonth();
  const firstDay = new Date(year, month, 1);
  const startingWeekday = firstDay.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;

  monthLabel.textContent = firstDay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let html = dayNames.map((name) => `<div class="calendar-day-name">${name}</div>`).join('');

  for (let i = 0; i < startingWeekday; i += 1) {
    const dayNum = daysInPrevMonth - startingWeekday + i + 1;
    html += `<div class="calendar-day other-month">${dayNum}</div>`;
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateObj = new Date(year, month, day);
    const dateKey = toDateKey(dateObj);
    const classes = ['calendar-day'];
    if (isCurrentMonth && day === today.getDate()) classes.push('today');
    if (DASHBOARD_EVENT_DATES.has(dateKey)) classes.push('has-event');
    if (dashboardCalendarState.selectedDate === dateKey) classes.push('is-selected');
    html += `<button class="${classes.join(' ')}" type="button" data-date="${dateKey}" data-dashboard-calendar-date="${dateKey}" aria-label="Show tasks for ${dateKey}">${day}</button>`;
  }

  const totalCells = startingWeekday + daysInMonth;
  const trailingDays = (7 - (totalCells % 7)) % 7;
  for (let i = 1; i <= trailingDays; i += 1) {
    html += `<div class="calendar-day other-month">${i}</div>`;
  }

  grid.innerHTML = html;
  grid.querySelectorAll('[data-dashboard-calendar-date]').forEach((button) => {
    button.addEventListener('click', () => {
      dashboardCalendarState.selectedDate = button.dataset.dashboardCalendarDate || '';
      renderDashboardCalendar();
      renderTasks(appState.tasks);
    });
  });
  loadDashboardCalendarEvents();
}

function shiftDashboardMonth(offset) {
  dashboardCalendarState.cursor = new Date(
    dashboardCalendarState.cursor.getFullYear(),
    dashboardCalendarState.cursor.getMonth() + offset,
    1
  );
  dashboardCalendarState.selectedDate = '';
  dashboardCalendarState.loadedKey = '';
  renderDashboardCalendar();
}

function prevDashboardMonth() {
  shiftDashboardMonth(-1);
}

function nextDashboardMonth() {
  shiftDashboardMonth(1);
}

function getThemeColor(variableName, fallback) {
  const bodyValue = document.body ? getComputedStyle(document.body).getPropertyValue(variableName).trim() : '';
  const rootValue = getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
  return bodyValue || rootValue || fallback;
}

function initChart(canvasId, configBuilder) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return;
  if (canvas.dataset.chartReady === '1') return;
  if (canvas.offsetParent === null) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const config = configBuilder();
  new Chart(ctx, withChartBaseConfig(config, ctx));
  canvas.dataset.chartReady = '1';
}

function initCharts() {
  const coffee = getThemeColor('--coffee', '#3B1E12');
  const gold = getThemeColor('--gold', '#E2B56D');
  const bronze = getThemeColor('--bronze', '#8B5A2B');
  const cocoa = getThemeColor('--cocoa', '#6B3A1F');

  initChart('projects-activity-chart', () => ({
    type: 'bar',
    data: {
      labels: [],
      datasets: [{
        label: 'Completed Tasks',
        data: [],
        backgroundColor: [gold, gold, bronze, bronze, coffee, cocoa],
        borderRadius: 8,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 2 } },
      },
    },
  }));

  initChart('projects-status-chart', () => ({
    type: 'pie',
    data: {
      labels: [],
      datasets: [{
        data: [],
        backgroundColor: [gold, bronze, coffee],
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
    },
  }));

}

function applyChartThemeDefaults() {
  if (!window.Chart) return;
  const surface = getThemeColor('--color-bg-surface', '#ffffff');
  const text = getThemeColor('--color-text-primary', '#343a40');
  const muted = getThemeColor('--color-text-secondary', '#6f4a32');
  const border = getThemeColor('--color-border-subtle', 'rgba(59,30,18,.10)');
  const accent = getThemeColor('--gold', '#E2B56D');
  const coffee = getThemeColor('--coffee', '#3B1E12');

  Chart.defaults.color = text;
  Chart.defaults.font.family = "'Quicksand', system-ui, sans-serif";
  Chart.defaults.borderColor = border;
  Chart.defaults.backgroundColor = 'rgba(226,181,109,0.18)';
  Chart.defaults.plugins.legend.labels.color = muted;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(59,30,18,.94)';
  Chart.defaults.plugins.tooltip.titleColor = accent;
  Chart.defaults.plugins.tooltip.bodyColor = '#F0D7A6';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(240,215,166,.24)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.usePointStyle = true;
  Chart.defaults.scale.grid.color = 'rgba(59,30,18,.07)';
  Chart.defaults.scale.ticks.color = muted;
  Chart.defaults.elements.arc.borderColor = surface;
  Chart.defaults.elements.line.borderWidth = 2;
  Chart.defaults.elements.bar.borderRadius = 8;
  Chart.defaults.elements.bar.borderSkipped = false;
  Chart.defaults.datasets.bar.backgroundColor = accent;
  Chart.defaults.datasets.line.backgroundColor = 'rgba(226,181,109,0.18)';
  Chart.defaults.datasets.line.borderColor = coffee;
}

function showToast(message, type = 'default', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'Notifications');
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  let resolvedType = type;
  if (!resolvedType || resolvedType === 'auto') {
    resolvedType = /fail|unable|error|invalid|missing/i.test(message) ? 'error' : 'success';
  }
  if (resolvedType === 'default' && /fail|unable|error|invalid|missing/i.test(message)) {
    resolvedType = 'error';
  }

  const icons = {
    success: 'fa-check-circle',
    error: 'fa-times-circle',
    info: 'fa-info-circle',
    warning: 'fa-exclamation-triangle',
    default: 'fa-bell',
  };
  const toast = document.createElement('div');
  toast.className = `toast toast--${resolvedType}`;
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.style.setProperty('--toast-duration', `${duration}ms`);
  toast.innerHTML = `<i class="fas ${icons[resolvedType] || icons.default} toast-icon" aria-hidden="true"></i><span class="toast-body">${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  const dismiss = () => {
    if (!toast.isConnected || toast.classList.contains('is-leaving')) return;
    toast.classList.add('is-leaving');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    setTimeout(() => toast.remove(), 360);
  };

  let dismissTimer = setTimeout(dismiss, duration);
  let startX = 0;
  let currentX = 0;
  let isDragging = false;

  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('is-visible'));
  });

  toast.addEventListener('pointerdown', (event) => {
    startX = event.clientX;
    currentX = 0;
    isDragging = true;
    toast.setPointerCapture?.(event.pointerId);
    toast.classList.add('is-dragging');
    clearTimeout(dismissTimer);
  });

  toast.addEventListener('pointermove', (event) => {
    if (!isDragging) return;
    currentX = Math.max(0, event.clientX - startX);
    toast.style.setProperty('--swipe-x', `${currentX}px`);
  });

  toast.addEventListener('pointerup', () => {
    isDragging = false;
    toast.classList.remove('is-dragging');
    if (currentX > 80) {
      dismiss();
    } else {
      toast.style.setProperty('--swipe-x', '0px');
      dismissTimer = setTimeout(dismiss, duration);
    }
    currentX = 0;
  });

  toast.addEventListener('pointercancel', () => {
    isDragging = false;
    toast.classList.remove('is-dragging');
    toast.style.setProperty('--swipe-x', '0px');
    dismissTimer = setTimeout(dismiss, duration);
  });

  toast.addEventListener('click', () => {
    clearTimeout(dismissTimer);
    dismiss();
  });
}

function setupOtpUX() {
  const otpInputs = Array.from(document.querySelectorAll('.otp-digit'));
  if (!otpInputs.length) return;

  otpInputs.forEach((input, idx) => {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !input.value && idx > 0) {
        otpInputs[idx - 1].focus();
      }
      if (e.key === 'ArrowLeft' && idx > 0) otpInputs[idx - 1].focus();
      if (e.key === 'ArrowRight' && idx < otpInputs.length - 1) otpInputs[idx + 1].focus();
      if (e.key === 'Enter') handleLogin();
    });

    input.addEventListener('paste', (e) => {
      const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
      if (!pasted) return;
      e.preventDefault();
      pasted.split('').forEach((char, pIdx) => {
        if (otpInputs[pIdx]) otpInputs[pIdx].value = char;
      });
      if (pasted.length === 6) setTimeout(handleLogin, 150);
    });
  });
}

function mountUIHelpers() {
  if (!document.getElementById('toast-container')) {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
}

function closeSidebarDrawer() {
  document.body.classList.remove('sidebar-open');
  const toggle = document.getElementById('mobile-nav-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

function openSidebarDrawer() {
  document.body.classList.add('sidebar-open');
  const toggle = document.getElementById('mobile-nav-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

function toggleSidebarDrawer() {
  if (document.body.classList.contains('sidebar-open')) closeSidebarDrawer();
  else openSidebarDrawer();
}

function setupMobileSidebar() {
  const topbar = document.querySelector('.topbar');
  const search = document.querySelector('.topbar-search');
  if (!topbar || !search || document.getElementById('mobile-nav-toggle')) return;

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.id = 'mobile-nav-toggle';
  toggle.className = 'mobile-nav-toggle';
  toggle.setAttribute('aria-label', 'Toggle navigation');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.innerHTML = '<i class="fas fa-bars"></i>';
  topbar.insertBefore(toggle, search);

  const backdrop = document.createElement('button');
  backdrop.type = 'button';
  backdrop.id = 'sidebar-backdrop';
  backdrop.className = 'sidebar-backdrop';
  backdrop.setAttribute('aria-label', 'Close navigation');
  document.body.appendChild(backdrop);

  toggle.addEventListener('click', toggleSidebarDrawer);
  backdrop.addEventListener('click', closeSidebarDrawer);

  document.querySelectorAll('.sidebar .nav-item').forEach((item) => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 980) closeSidebarDrawer();
    });
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 980) closeSidebarDrawer();
  });
}

function setBodyScrollState() {
  document.body.classList.toggle('is-scrolled', window.scrollY > 10);
}

function buildCommandPaletteItems() {
  const pageItems = [
    { label: 'Dashboard', meta: 'Pages', icon: 'fas fa-table-cells-large', action: () => navigateInApp(PAGE_ROUTES.dashboard) },
    { label: 'Finance', meta: 'Pages', icon: 'far fa-credit-card', action: () => navigateInApp(PAGE_ROUTES.finance) },
    { label: 'Diary', meta: 'Pages', icon: 'far fa-bookmark', action: () => navigateInApp(PAGE_ROUTES.diary) },
    { label: 'Reminders & TODOs', meta: 'Pages', icon: 'far fa-bell', action: () => navigateInApp(PAGE_ROUTES.reminders) },
    { label: 'Projects', meta: 'Pages', icon: 'fas fa-rocket', action: () => navigateInApp(PAGE_ROUTES.projects) },
  ];

  const quickItems = [
    {
      label: 'Add task',
      meta: 'Actions',
      icon: 'fas fa-list-check',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('task');
      },
    },
    {
      label: 'Add reminder',
      meta: 'Actions',
      icon: 'far fa-bell',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('reminder');
      },
    },
    {
      label: 'Add note',
      meta: 'Actions',
      icon: 'far fa-note-sticky',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('note');
      },
    },
    {
      label: 'Track expense',
      meta: 'Actions',
      icon: 'far fa-credit-card',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('expense');
      },
    },
    {
      label: 'Create Goal',
      meta: 'Actions',
      icon: 'fas fa-bullseye',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('goal');
      },
    },
    {
      label: 'Create Bucket List Item',
      meta: 'Actions',
      icon: 'fas fa-star',
      action: () => {
        toggleQuickAdd(true);
        openQuickForm('bucket');
      },
    },
  ];

  const navItems = Array.from(document.querySelectorAll('.sidebar .nav-item[href]'))
    .filter((link) => link.getAttribute('href') && link.getAttribute('href') !== '#')
    .map((link) => ({
      label: link.textContent.replace(/\s+/g, ' ').trim(),
      meta: 'Navigation',
      icon: link.querySelector('i')?.className || 'fas fa-arrow-right',
      action: () => {
        navigateInApp(link.getAttribute('href'));
      },
    }));

  navItems.push(
    {
      label: 'Open Finance Analytics',
      meta: 'Insights',
      icon: 'fas fa-chart-pie',
      action: () => {
        navigateInApp(`${PAGE_ROUTES.finance}#finance-analytics`);
      },
    },
    {
      label: 'Sign Out',
      meta: 'Session',
      icon: 'fas fa-right-from-bracket',
      action: () => signOut(),
    }
  );

  const shortcuts = [
    {
      label: 'Open Tasks',
      meta: 'Navigation',
      icon: 'fas fa-list-check',
      action: () => {
        navigateInApp(PAGE_ROUTES.reminders);
      },
    },
    {
      label: 'Open Goals',
      meta: 'Navigation',
      icon: 'fas fa-star',
      action: () => {
        navigateInApp(PAGE_ROUTES.bucket);
      },
    },
    {
      label: 'Open Calendar',
      meta: 'Navigation',
      icon: 'far fa-calendar',
      action: () => {
        navigateInApp(PAGE_ROUTES.calendar);
      },
    },
    {
      label: 'Open Finance',
      meta: 'Navigation',
      icon: 'fas fa-wallet',
      action: () => {
        navigateInApp(PAGE_ROUTES.finance);
      },
    },
    {
      label: 'Search Tasks',
      meta: 'Search',
      icon: 'fas fa-magnifying-glass',
      action: () => {
        navigateInApp(PAGE_ROUTES.reminders);
      },
    },
    {
      label: 'Search Goals',
      meta: 'Search',
      icon: 'fas fa-magnifying-glass',
      action: () => {
        navigateInApp(PAGE_ROUTES.bucket);
      },
    },
    {
      label: 'Search Notes',
      meta: 'Search',
      icon: 'fas fa-magnifying-glass',
      action: () => {
        navigateInApp(PAGE_ROUTES.diary);
      },
    },
  ];

  return [...pageItems, ...quickItems, ...shortcuts, ...navItems];
}

function closeCommandPalette() {
  const panel = document.getElementById('global-command-panel');
  const search = document.querySelector('.topbar-search');
  const input = document.querySelector('.topbar-search input');
  const overlay = document.getElementById('command-palette-overlay');
  const overlayInput = document.getElementById('command-palette-input');
  if (panel) panel.hidden = true;
  if (search) search.classList.remove('panel-open');
  if (input) input.setAttribute('aria-expanded', 'false');
  if (overlay) {
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
  }
  if (overlayInput) overlayInput.blur();
  uiState.commandSelection = -1;
}

function updateCommandPaletteSelection() {
  const panel = document.getElementById('global-command-panel');
  const overlay = document.getElementById('command-palette-overlay');
  const overlayList = document.getElementById('command-palette-list');
  if (overlay && !overlay.classList.contains('hidden') && overlayList) {
    overlayList.querySelectorAll('.command-item').forEach((item, index) => {
      item.classList.toggle('active', index === uiState.commandSelection);
    });
  }
  if (panel) {
    panel.querySelectorAll('.search-panel-item').forEach((item, index) => {
      item.classList.toggle('active', index === uiState.commandSelection);
    });
  }
}

function highlightMatch(text = '', query = '') {
  const safeText = escapeHtml(text);
  const normalized = query.trim();
  if (!normalized) return safeText;
  const escapedQuery = normalized.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return safeText.replace(new RegExp(`(${escapedQuery})`, 'ig'), '<mark class="search-mark">$1</mark>');
}

function normalizeSearchIcon(icon = '') {
  const iconClass = String(icon || '').trim();
  if (!iconClass) return 'fas fa-circle';
  return iconClass.includes(' ') ? iconClass : `fas ${iconClass}`;
}

function buildSearchSuggestions(query = '') {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];

  return buildCommandPaletteItems()
    .filter((item) => item.meta === 'Pages' || item.meta === 'Actions')
    .filter((item) => `${item.label} ${item.meta}`.toLowerCase().includes(normalized))
    .slice(0, 6)
    .map((item) => ({
      kind: 'command',
      title: item.label,
      preview: item.meta === 'Pages' ? 'Jump to page' : 'Quick action',
      group: item.meta,
      icon: item.icon,
      action: item.action,
    }));
}

function renderCommandPaletteOverlay(query = '') {
  const list = document.getElementById('command-palette-list');
  if (!list) return;
  const normalized = query.trim().toLowerCase();
  const items = buildCommandPaletteItems().filter((item) => {
    if (!normalized) return true;
    return `${item.label} ${item.meta}`.toLowerCase().includes(normalized);
  });
  uiState.commandItems = items.slice(0, 10);
  uiState.commandSelection = uiState.commandItems.length ? 0 : -1;

  if (!uiState.commandItems.length) {
    list.innerHTML = '<div class="search-panel-empty">No matching commands.</div>';
    return;
  }

  list.innerHTML = uiState.commandItems.map((item, index) => `
    <button class="command-item${index === 0 ? ' active' : ''}" type="button" data-command-index="${index}">
      <span>
        <div class="command-item-title">${highlightMatch(item.label, query)}</div>
        <div class="command-item-meta">${highlightMatch(item.meta, query)}</div>
      </span>
      <i class="${item.icon}"></i>
    </button>
  `).join('');
}

function filterCommands(query = '') {
  renderCommandPaletteOverlay(query);
}

function openCommandPalette() {
  const overlay = document.getElementById('command-palette-overlay');
  const input = document.getElementById('command-palette-input');
  if (!overlay || !input) return;
  closeNotifications();
  closeModal('quick-add-modal-overlay');
  overlay.classList.remove('hidden');
  overlay.setAttribute('aria-hidden', 'false');
  input.value = '';
  filterCommands('');
  setTimeout(() => input.focus(), 0);
}

function renderCommandPalette(query = '') {
  const panel = document.getElementById('global-command-panel');
  const search = document.querySelector('.topbar-search');
  const input = document.querySelector('.topbar-search input');
  if (!panel || !search || !input) return;

  const normalized = query.trim().toLowerCase();
  if (normalized.length >= 2) {
    panel.hidden = true;
    search.classList.remove('panel-open');
    input.setAttribute('aria-expanded', 'false');
    return;
  }
  const items = buildCommandPaletteItems().filter((item) => {
    if (!normalized) return true;
    return `${item.label} ${item.meta}`.toLowerCase().includes(normalized);
  });

  uiState.commandItems = items.slice(0, 8);
  uiState.commandSelection = uiState.commandItems.length ? 0 : -1;

  if (!uiState.commandItems.length) {
    panel.innerHTML = '<div class="search-panel-empty">No matching commands. Try finance, diary, analytics, or settings.</div>';
  } else {
    panel.innerHTML = uiState.commandItems.map((item, index) => `
      <button class="search-panel-item${index === 0 ? ' active' : ''}" type="button" data-command-index="${index}">
        <span class="search-panel-icon"><i class="${item.icon}"></i></span>
        <span class="search-panel-copy">
          <span class="search-panel-title">${highlightMatch(item.label, query)}</span>
          <span class="search-panel-meta">${highlightMatch(item.meta, query)}</span>
        </span>
        <span class="search-panel-arrow"><i class="fas fa-arrow-right"></i></span>
      </button>
    `).join('');
  }

  panel.hidden = false;
  search.classList.add('panel-open');
  input.setAttribute('aria-expanded', 'true');
}

function executeCommandPaletteSelection(index = uiState.commandSelection) {
  const item = uiState.commandItems[index];
  if (!item) return;
  closeCommandPalette();
  item.action();
}

function moveCommandPaletteSelection(offset) {
  if (!uiState.commandItems.length) return;
  const total = uiState.commandItems.length;
  uiState.commandSelection = (uiState.commandSelection + offset + total) % total;
  updateCommandPaletteSelection();
}

function setupCommandPalette() {
  const search = document.querySelector('.topbar-search');
  const input = search?.querySelector('input');
  if (!search || !input || document.getElementById('global-command-panel')) return;

  input.placeholder = 'Search anything or jump with a command';
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('aria-expanded', 'false');

  const shortcut = document.createElement('span');
  shortcut.className = 'search-shortcut';
  shortcut.textContent = 'Ctrl+K';
  search.appendChild(shortcut);

  const panel = document.createElement('div');
  panel.id = 'global-command-panel';
  panel.className = 'topbar-search-panel';
  panel.hidden = true;
  search.appendChild(panel);

  input.addEventListener('focus', () => renderCommandPalette(input.value));
  input.addEventListener('input', () => renderCommandPalette(input.value));
  input.addEventListener('keydown', (event) => {
    const usingSearchResults = input.value.trim().length >= 2;
    if (event.key === 'ArrowDown') {
      if (usingSearchResults) return;
      event.preventDefault();
      renderCommandPalette(input.value);
      moveCommandPaletteSelection(1);
      return;
    }
    if (event.key === 'ArrowUp') {
      if (usingSearchResults) return;
      event.preventDefault();
      renderCommandPalette(input.value);
      moveCommandPaletteSelection(-1);
      return;
    }
    if (event.key === 'Enter') {
      if (usingSearchResults) return;
      if (!panel.hidden) {
        event.preventDefault();
        executeCommandPaletteSelection();
      }
      return;
    }
    if (event.key === 'Escape') {
      closeCommandPalette();
      input.blur();
    }
  });

  panel.addEventListener('click', (event) => {
    const actionButton = event.target.closest('.search-panel-item');
    if (!actionButton) return;
    const index = Number(actionButton.dataset.commandIndex);
    if (Number.isInteger(index)) executeCommandPaletteSelection(index);
  });

  document.addEventListener('click', (event) => {
    if (!search.contains(event.target)) closeCommandPalette();
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      const overlay = document.getElementById('command-palette-overlay');
      if (overlay) {
        openCommandPalette();
      } else {
        input.focus();
        input.select();
        renderCommandPalette(input.value);
      }
      return;
    }
    if (event.key === 'Escape') {
      closeCommandPalette();
      closeNotifications();
      closeModal('quick-add-modal-overlay');
      closeSidebarDrawer();
    }
  });
}

function renderSearchResults(results, container, query) {
  if (!container) return;
  const suggestions = buildSearchSuggestions(query);
  const contentResults = (results || []).map((result) => ({
    kind: 'result',
    title: result.title || '',
    preview: result.preview || '',
    group: result.group || result.type || '',
    icon: normalizeSearchIcon(result.icon || 'fa-circle'),
    url: result.url || '#',
  }));
  const combined = [...suggestions, ...contentResults].slice(0, 12);
  uiState.searchItems = combined;

  if (!combined.length) {
    container.innerHTML = `<div class="search-empty">No results for "${escapeHtml(query)}"</div>`;
    container.classList.remove('hidden');
    return;
  }

  container.innerHTML = combined.map((item, index) => {
    const icon = escapeHtml(normalizeSearchIcon(item.icon));
    const body = `
      <span class="search-result-icon"><i class="${icon}"></i></span>
      <span class="search-result-body">
        <span class="search-result-title">${highlightMatch(item.title || '', query)}</span>
        <span class="search-result-preview">${highlightMatch(item.preview || '', query)}</span>
      </span>
      <span class="search-result-type">${escapeHtml(item.group || '')}</span>
    `;

    if (item.kind === 'command') {
      return `<button class="search-result-item" type="button" data-search-index="${index}">${body}</button>`;
    }

    return `<a class="search-result-item" href="${escapeHtml(item.url || '#')}" data-inapp-nav="true">${body}</a>`;
  }).join('');
  container.classList.remove('hidden');
  enhanceInAppNavLinks(container);
}

function executeSearchSuggestion(index) {
  const item = uiState.searchItems[index];
  if (!item || item.kind !== 'command' || typeof item.action !== 'function') return;
  const searchResults = document.getElementById('global-search-results');
  const input = document.getElementById('global-search-input');
  if (searchResults) searchResults.classList.add('hidden');
  if (input) {
    input.value = '';
    input.blur();
  }
  item.action();
}

function initGlobalSearch() {
  const search = document.querySelector('.topbar-search');
  const input = search?.querySelector('input');
  if (!search || !input || search.dataset.globalSearchBound === '1') return;

  search.dataset.globalSearchBound = '1';
  search.style.position = 'relative';

  const searchResults = document.createElement('div');
  searchResults.className = 'search-results-dropdown hidden';
  searchResults.id = 'global-search-results';
  search.appendChild(searchResults);
  searchResults.addEventListener('click', (event) => {
    const actionButton = event.target.closest('[data-search-index]');
    if (!actionButton) return;
    event.preventDefault();
    executeSearchSuggestion(Number(actionButton.dataset.searchIndex));
  });

  const runSearch = debounce(async (query) => {
    try {
      globalSearchAbortController = new AbortController();
      const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
        signal: globalSearchAbortController.signal,
      });
      const data = await response.json();
      renderSearchResults(data.results || [], searchResults, query);
    } catch (error) {
      if (error?.name !== 'AbortError') {
        console.warn('Search error', error);
      }
    } finally {
      globalSearchAbortController = null;
    }
  }, 250);

  input.addEventListener('input', () => {
    const query = input.value.trim();
    const commandPanel = document.getElementById('global-command-panel');
    if (globalSearchAbortController) {
      globalSearchAbortController.abort();
      globalSearchAbortController = null;
    }
    if (query.length < 2) {
      runSearch.cancel();
      searchResults.classList.add('hidden');
      if (document.activeElement === input && commandPanel) renderCommandPalette(query);
      return;
    }

    if (commandPanel) {
      commandPanel.hidden = true;
      search.classList.remove('panel-open');
      input.setAttribute('aria-expanded', 'false');
    }

    runSearch(query);
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.topbar-search')) {
      searchResults.classList.add('hidden');
    }
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      searchResults.classList.add('hidden');
      input.blur();
      return;
    }
    if (event.key === 'Enter' && !searchResults.classList.contains('hidden')) {
      const firstLink = searchResults.querySelector('.search-result-item');
      if (firstLink) {
        event.preventDefault();
        firstLink.click();
      }
    }
  });
}

function initKeyboardShortcuts() {
  if (document.body?.dataset.keyboardShortcutsBound === '1') return;
  if (document.body) document.body.dataset.keyboardShortcutsBound = '1';

  const clearShortcutGroup = () => {
    uiState.shortcutGroup = '';
    if (uiState.shortcutGroupTimer) {
      clearTimeout(uiState.shortcutGroupTimer);
      uiState.shortcutGroupTimer = null;
    }
  };

  const armShortcutGroup = () => {
    clearShortcutGroup();
    uiState.shortcutGroup = 'g';
    uiState.shortcutGroupTimer = window.setTimeout(clearShortcutGroup, 900);
  };

  const getNavigableItems = () => Array.from(document.querySelectorAll('.task-item, .reminder-focus-item, .notif-item'))
    .filter((item) => item.offsetParent !== null)
    .map((item) => {
      if (!item.hasAttribute('tabindex')) item.setAttribute('tabindex', '0');
      return item;
    });

  document.addEventListener('keydown', (event) => {
    if (isTypingContext()) return;

    const key = event.key.toLowerCase();
    if (uiState.shortcutGroup === 'g') {
      const destinations = {
        d: PAGE_ROUTES.dashboard,
        f: PAGE_ROUTES.finance,
        r: PAGE_ROUTES.reminders,
        p: PAGE_ROUTES.projects,
        b: PAGE_ROUTES.bucket,
        c: PAGE_ROUTES.calendar,
        e: PAGE_ROUTES.education,
        s: PAGE_ROUTES.settings,
      };
      clearShortcutGroup();
      if (destinations[key]) {
        event.preventDefault();
        navigateInApp(destinations[key]);
        return;
      }
    }

    if (key === 'g' && !event.metaKey && !event.ctrlKey && !event.altKey && !event.shiftKey) {
      armShortcutGroup();
      return;
    }

    if (key === 'j') {
      event.preventDefault();
      const items = getNavigableItems();
      if (!items.length) return;
      const currentIndex = items.indexOf(document.activeElement);
      const next = currentIndex >= 0 ? items[currentIndex + 1] : items[0];
      if (next) next.focus();
      return;
    }

    if (key === 'k') {
      event.preventDefault();
      const items = getNavigableItems();
      if (!items.length) return;
      const currentIndex = items.indexOf(document.activeElement);
      const prev = currentIndex >= 0 ? items[currentIndex - 1] : items[items.length - 1];
      if (prev) prev.focus();
      return;
    }

    if (key === 'n' && !event.metaKey && !event.ctrlKey) {
      event.preventDefault();
      toggleQuickAdd(true);
      return;
    }

    if (event.key === '/') {
      event.preventDefault();
      const searchInput = document.querySelector('.topbar-search input');
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
      return;
    }

    if (event.key === 'Escape') {
      clearShortcutGroup();
    }
  });

  const searchInput = document.querySelector('.topbar-search input');
  if (searchInput) searchInput.setAttribute('placeholder', 'Search... (press /)');
}

function attachSpotlightEffects(root = document) {
  const targets = root.querySelectorAll('.dash-card, .metric-link-card, .item-card, .finance-stat-card, .bucket-cat, .diary-editor, .modal-card');
  targets.forEach((card) => {
    if (card.dataset.spotlightBound === '1') return;
    card.dataset.spotlightBound = '1';

    card.addEventListener('pointermove', (event) => {
      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      card.style.setProperty('--spot-x', `${x}px`);
      card.style.setProperty('--spot-y', `${y}px`);
      card.classList.add('has-spotlight');
    });

    card.addEventListener('pointerleave', () => {
      card.classList.remove('has-spotlight');
    });
  });
}

function setupRevealEffects() {
  const revealTargets = document.querySelectorAll(
    '.dash-card, .metric-link-card, .bucket-goal-card, .media-stat, .finance-stat-card'
  );
  if ('IntersectionObserver' in window && !revealObserver) {
    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const delayIndex = Number(entry.target.dataset.revealIndex || 0);
        entry.target.style.setProperty('--reveal-delay', `${delayIndex * 0.065}s`);
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
  }

  revealTargets.forEach((target, index) => {
    if (!target.classList.contains('reveal-block')) {
      target.classList.add('reveal-block');
    }
    if (!target.dataset.revealIndex) target.dataset.revealIndex = index;
    if (target.classList.contains('is-visible')) return;
    if (revealObserver) revealObserver.observe(target);
    else target.classList.add('is-visible');
  });
}

function easeOutQuart(t) {
  return 1 - Math.pow(1 - t, 4);
}

function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function animateNumberCounter(el) {
  if (el.dataset.counted === '1') return;
  const text = (el.textContent || '').trim();
  const match = text.match(/-?[\d,.]+/);
  if (!match) return;

  const raw = match[0];
  const startIndex = text.indexOf(raw);
  const prefix = text.slice(0, startIndex);
  const suffix = text.slice(startIndex + raw.length);
  const value = Number(raw.replace(/,/g, ''));
  if (!Number.isFinite(value)) return;
  const decimals = raw.includes('.') ? raw.split('.')[1].length : 0;
  const locale = prefix.toUpperCase().includes('KES') ? 'en-KE' : undefined;

  const formatValue = (val) => val.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  el.dataset.counted = '1';
  if (prefersReducedMotion()) {
    el.textContent = `${prefix}${formatValue(value)}${suffix}`;
    return;
  }

  const startTime = performance.now();
  const duration = 1200;

  const tick = (now) => {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = easeOutQuart(progress);
    const current = value * eased;
    el.textContent = `${prefix}${formatValue(current)}${suffix}`;
    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      el.textContent = `${prefix}${formatValue(value)}${suffix}`;
    }
  };

  requestAnimationFrame(tick);
}

function setupNumberCounters() {
  const targets = document.querySelectorAll('.metric-value, .media-stat-value, .finance-amount');
  if (!targets.length) return;
  if ('IntersectionObserver' in window && !numberObserver) {
    numberObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animateNumberCounter(entry.target);
        numberObserver.unobserve(entry.target);
      });
    }, { threshold: 0.2 });
  }

  targets.forEach((el) => {
    if (el.dataset.countBound === '1') return;
    el.dataset.countBound = '1';
    if (numberObserver) numberObserver.observe(el);
    else animateNumberCounter(el);
  });
}

function animateProgressCounter(fill) {
  if (fill.dataset.progressAnimated === '1') return;
  fill.dataset.progressAnimated = '1';
  fill.classList.remove('is-animated');
  void fill.offsetWidth;
  fill.classList.add('is-animated');

  const track = fill.closest('.progress-track');
  const labelContainer = fill.closest('.bucket-progress')
    || track?.parentElement?.querySelector('.progress-label')
    || fill.closest('.progress-label');
  const label = labelContainer?.querySelector('.progress-percent')
    || labelContainer?.querySelector('span:last-child');
  if (!label) return;
  const labelText = String(label.textContent || '').trim();
  const hasPercent = labelText.includes('%');
  if (!label.classList.contains('progress-percent') && !hasPercent) return;

  let target = Number.parseFloat(labelText.replace('%', ''));
  if (!Number.isFinite(target)) {
    target = Number.parseFloat(String(fill.style.width || '').replace('%', ''));
  }
  if (!Number.isFinite(target)) return;
  target = Math.max(0, Math.min(100, target));
  if (prefersReducedMotion()) {
    label.textContent = `${Math.round(target)}%`;
    return;
  }

  const startTime = performance.now();
  const duration = 900;
  const tick = (now) => {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = easeOutQuart(progress);
    const current = Math.round(target * eased);
    label.textContent = `${current}%`;
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function setupProgressCounters() {
  const fills = document.querySelectorAll('.progress-fill');
  if (!fills.length) return;
  if ('IntersectionObserver' in window && !progressObserver) {
    progressObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animateProgressCounter(entry.target);
        progressObserver.unobserve(entry.target);
      });
    }, { threshold: 0.25 });
  }

  fills.forEach((fill) => {
    if (fill.dataset.progressBound === '1') return;
    fill.dataset.progressBound = '1';
    if (progressObserver) progressObserver.observe(fill);
    else animateProgressCounter(fill);
  });
}

function setupButtonRipples() {
  if (document.documentElement.dataset.ripplesReady === '1') return;
  document.documentElement.dataset.ripplesReady = '1';
  const targets = '.btn-primary, .btn-add, .btn-outline, .ca-btn-primary, .ca-btn-danger, .ca-settings-option-btn';

  document.addEventListener('pointerdown', (event) => {
    const btn = event.target.closest(targets);
    if (!btn || prefersReducedMotion()) return;

    const rect = btn.getBoundingClientRect();
    const x = (((event.clientX - rect.left) / rect.width) * 100).toFixed(1);
    const y = (((event.clientY - rect.top) / rect.height) * 100).toFixed(1);
    btn.style.setProperty('--ripple-x', `${x}%`);
    btn.style.setProperty('--ripple-y', `${y}%`);
    btn.classList.add('rippling');

    const ripple = document.createElement('span');
    ripple.className = 'ripple-circle';
    const size = Math.max(rect.width, rect.height) * 2;
    Object.assign(ripple.style, {
      position: 'absolute',
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: '50%',
      background: 'hsl(0 0% 100% / 0.20)',
      left: `${event.clientX - rect.left - size / 2}px`,
      top: `${event.clientY - rect.top - size / 2}px`,
      pointerEvents: 'none',
      zIndex: '0',
      transform: 'scale(0)',
    });

    btn.appendChild(ripple);
    ripple.animate(
      [{ transform: 'scale(0)', opacity: 1 }, { transform: 'scale(1)', opacity: 0 }],
      { duration: 550, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
    ).finished.then(() => {
      ripple.remove();
      btn.classList.remove('rippling');
    });
  });
}

function initRipples() {
  setupButtonRipples();
}

function initCardTilt(root = document) {
  const cards = root.querySelectorAll?.('.dash-card, .metric-link-card, .item-card, .bucket-goal-card') || [];
  const TILT_MAX = 6;
  cards.forEach((card) => {
    if (card.dataset.tiltBound === '1') return;
    card.dataset.tiltBound = '1';
    let rafId = null;

    card.addEventListener('mousemove', (event) => {
      if (prefersReducedMotion() || window.innerWidth < 768) return;
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const rect = card.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = (event.clientX - cx) / (rect.width / 2);
        const dy = (event.clientY - cy) / (rect.height / 2);
        card.style.setProperty('--tilt-x', `${(-dy * TILT_MAX).toFixed(2)}deg`);
        card.style.setProperty('--tilt-y', `${(dx * TILT_MAX).toFixed(2)}deg`);
        card.classList.add('is-hovered');
      });
    });

    card.addEventListener('mouseleave', () => {
      cancelAnimationFrame(rafId);
      card.style.setProperty('--tilt-x', '0deg');
      card.style.setProperty('--tilt-y', '0deg');
      card.classList.remove('is-hovered');
    });
  });
}

function initMagneticButtons(root = document) {
  if (window.innerWidth < 768 || prefersReducedMotion()) return;
  const targets = root.querySelectorAll?.('.btn-primary, .ca-btn-primary, .topbar-profile, .user-avatar') || [];
  const STRENGTH = 0.18;
  targets.forEach((el) => {
    if (el.dataset.magneticBound === '1') return;
    el.dataset.magneticBound = '1';
    let rafId = null;

    el.addEventListener('mousemove', (event) => {
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = (event.clientX - cx) * STRENGTH;
        const dy = (event.clientY - cy) * STRENGTH;
        el.style.transform = `translate(${dx}px, ${dy}px)`;
      });
    });

    el.addEventListener('mouseleave', () => {
      cancelAnimationFrame(rafId);
      el.style.transform = '';
    });
  });
}

function initScrollTopbar() {
  if (document.documentElement.dataset.scrollTopbarReady === '1') return;
  document.documentElement.dataset.scrollTopbarReady = '1';
  let ticking = false;
  const update = () => {
    document.body.classList.toggle('is-scrolled', window.scrollY > 20);
    ticking = false;
  };
  update();
  window.addEventListener('scroll', () => {
    if (ticking) return;
    requestAnimationFrame(update);
    ticking = true;
  }, { passive: true });
}

function initProgressBarAnimations(root = document) {
  const bars = root.querySelectorAll?.('.progress-fill, .ca-progress-bar-fill') || [];
  if (!bars.length) return;
  if (prefersReducedMotion()) {
    bars.forEach((bar) => bar.classList.add('is-animated'));
    return;
  }

  if (!('IntersectionObserver' in window)) {
    bars.forEach((bar) => bar.classList.add('is-animated'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-animated');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.2 });

  bars.forEach((bar) => {
    if (bar.dataset.progressVisualBound === '1') return;
    bar.dataset.progressVisualBound = '1';
    observer.observe(bar);
  });
}

function initTabIndicators(root = document) {
  const bars = root.querySelectorAll?.('.tab-bar, .finance-tab-bar, .media-tab-bar, .education-tab-bar') || [];

  function syncTabIndicator(bar) {
    const active = bar.querySelector('.tab-btn.active');
    if (!active) return;
    const barRect = bar.getBoundingClientRect();
    const btnRect = active.getBoundingClientRect();
    bar.style.setProperty('--tab-indicator-x', `${btnRect.left - barRect.left - 4 + bar.scrollLeft}px`);
    bar.style.setProperty('--tab-indicator-width', `${btnRect.width}px`);
  }

  bars.forEach((bar) => {
    syncTabIndicator(bar);
    if (bar.dataset.tabIndicatorBound === '1') return;
    bar.dataset.tabIndicatorBound = '1';
    bar.addEventListener('click', () => requestAnimationFrame(() => syncTabIndicator(bar)));
    bar.addEventListener('scroll', () => requestAnimationFrame(() => syncTabIndicator(bar)), { passive: true });
  });

  if (typeof window.switchTab === 'function' && !window.switchTab._synced) {
    const originalSwitchTab = window.switchTab;
    window.switchTab = function syncedSwitchTab(...args) {
      originalSwitchTab(...args);
      requestAnimationFrame(() => document.querySelectorAll('.tab-bar, .finance-tab-bar, .media-tab-bar, .education-tab-bar').forEach(syncTabIndicator));
    };
    window.switchTab._synced = true;
  }

  if (document.documentElement.dataset.tabResizeReady !== '1') {
    document.documentElement.dataset.tabResizeReady = '1';
    window.addEventListener('resize', debounce(() => {
      document.querySelectorAll('.tab-bar, .finance-tab-bar, .media-tab-bar, .education-tab-bar').forEach(syncTabIndicator);
    }, 120));
  }
}

function initScrollAnimations(root = document) {
  initObserverAnimations(root);
  initProgressBarAnimations(root);
}

function showSkeletonFor(containerSelector, rows = 3) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  const skeletons = Array.from({ length: rows }, () => `
    <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--color-border-subtle)">
      <div class="skeleton skeleton-avatar"></div>
      <div style="flex:1">
        <div class="skeleton skeleton-line" style="width:60%"></div>
        <div class="skeleton skeleton-line" style="width:40%"></div>
      </div>
    </div>
  `).join('');
  container.innerHTML = `<div class="skeleton-container">${skeletons}</div>`;
}

function clearSkeleton(containerSelector) {
  const skeleton = document.querySelector(`${containerSelector} .skeleton-container`);
  if (!skeleton) return;
  skeleton.style.transition = 'opacity 0.2s';
  skeleton.style.opacity = '0';
  setTimeout(() => skeleton.remove(), 200);
}

function setupScrollSpy() {
  const navItems = Array.from(document.querySelectorAll('.sidebar .nav-item'));
  const sectionMap = scrollSpyMap;
  sectionMap.clear();

  const resolveTarget = (targetId) => {
    if (!targetId) return null;
    const node = document.getElementById(targetId);
    if (!node) return null;
    if (node.classList.contains('tab-btn')) {
      const onclick = node.getAttribute('onclick') || '';
      const match = onclick.match(/switchTab\\('([^']+)'\\s*,\\s*'([^']+)'\\)/);
      if (match) {
        const panel = document.getElementById(`${match[1]}-${match[2]}`);
        if (panel) return panel;
      }
    }
    return node;
  };

  navItems.forEach((item) => {
    const explicitTarget = item.dataset.scrollTarget;
    let targetId = explicitTarget;
    if (!targetId) {
      const href = item.getAttribute('href') || '';
      const hashIndex = href.indexOf('#');
      if (hashIndex !== -1) targetId = href.slice(hashIndex + 1);
    }
    const section = resolveTarget(targetId);
    if (!section) return;
    sectionMap.set(section, item);
  });

  if (!sectionMap.size) return;
  if (!scrollSpyObserver) {
    scrollSpyObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navItems.forEach((item) => item.classList.remove('section-active'));
        const navItem = scrollSpyMap.get(entry.target);
        if (navItem) navItem.classList.add('section-active');
      });
    }, { threshold: 0.35, rootMargin: '-20% 0px -55% 0px' });
  }

  sectionMap.forEach((_item, section) => {
    if (section.dataset.scrollSpyBound === '1') return;
    section.dataset.scrollSpyBound = '1';
    scrollSpyObserver.observe(section);
  });
}

function setupShortcutHints() {
  const quickAddBtn = document.getElementById('quick-add-btn');
  if (quickAddBtn) quickAddBtn.setAttribute('title', 'Quick Add (N)');
  const notifBtn = document.getElementById('notifications-btn');
  if (notifBtn) notifBtn.setAttribute('title', 'Notifications');
}

function setupCommandPaletteHint() {
  const wrap = document.querySelector('.topbar-search');
  if (!wrap) return;
  try {
    if (localStorage.getItem('cmdHintSeen') === '1') return;
  } catch (err) {
    // Ignore storage issues.
  }

  const badge = document.createElement('span');
  badge.className = 'cmd-hint-badge';
  badge.textContent = 'Ctrl+K';
  wrap.appendChild(badge);
  requestAnimationFrame(() => badge.classList.add('is-visible'));

  setTimeout(() => badge.classList.remove('is-visible'), 2600);
  setTimeout(() => {
    badge.remove();
    try {
      localStorage.setItem('cmdHintSeen', '1');
    } catch (err) {
      // Ignore storage issues.
    }
  }, 3000);
}

function resetIdleTimer() {
  document.body.classList.remove('is-idle');
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    document.body.classList.add('is-idle');
  }, 180000);
}

function setupIdleDetection() {
  const events = ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'];
  events.forEach((eventName) => {
    document.addEventListener(eventName, resetIdleTimer, { passive: true });
  });
  resetIdleTimer();
}

function refreshVisualEnhancements() {
  attachSpotlightEffects();
  initObserverAnimations();
  runCounterAnimations();
  initProgressBarAnimations();
  initCardTilt();
  initMagneticButtons();
  initTabIndicators();
  setupButtonRipples();
}

function runCounterAnimations(root = document) {
  root.querySelectorAll?.('.metric-value, .college-stat-value, .media-stat-value, .finance-amount').forEach((el) => {
    const raw = (el.dataset.counterValue || el.textContent || '').trim();
    if (!raw || /queued|Nothing|Loading/i.test(raw)) return;
    if (el.dataset.animatedRaw === raw) return;

    const match = raw.match(/^([^0-9\-]*)(-?[\d,\.]+)(.*)$/);
    if (!match) return;

    const prefix = match[1];
    const target = parseFloat(match[2].replace(/,/g, ''));
    const suffix = match[3];
    const decimals = (match[2].split('.')[1] || '').length;
    if (!Number.isFinite(target)) return;

    el.dataset.animatedRaw = raw;
    const format = (value) => {
      const normalized = Math.abs(value) < 0.000001 ? 0 : value;
      return `${prefix}${normalized.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}${suffix}`;
    };

    if (prefersReducedMotion()) {
      el.textContent = format(target);
      return;
    }

    const startTime = performance.now();
    const duration = 1400;
    const springEase = (t) => {
      const c4 = (2 * Math.PI) / 2.8;
      if (t === 0 || t === 1) return t;
      return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
    };

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const value = target * springEase(progress);
      el.textContent = format(value);
      if (progress < 1) requestAnimationFrame(tick);
      else el.textContent = format(target);
    };
    requestAnimationFrame(tick);
  });
}

function initObserverAnimations(root = document) {
  const targets = [
    '.dash-card',
    '.metric-link-card',
    '.bucket-goal-card',
    '.item-card',
    '.notification-feed-item',
    '.settings-accordion-item',
    '.ca-settings-section-card',
    '.animate-ready',
    '.education-level-card',
    '.education-scholarship-card',
    '.compact-list-item',
  ];
  const elements = root.querySelectorAll?.(targets.join(', ')) || [];
  if (!elements.length) return;

  elements.forEach((el) => el.classList.add('animate-ready'));
  if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
    elements.forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (!entry.isIntersecting) return;
      const delay = Math.min(index * 40, 300);
      setTimeout(() => {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }, delay);
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -32px 0px' });

  elements.forEach((el) => {
    if (el.classList.contains('is-visible')) return;
    observer.observe(el);
  });
}

function destroyChartCollection(collection = {}) {
  Object.values(collection).forEach((chart) => {
    if (!chart || typeof chart.destroy !== 'function') return;
    try {
      chart.destroy();
    } catch (err) {
      // Ignore teardown failures for stale chart instances.
    }
  });
}

function resetPageSetupState(pageKey = getActivePage()) {
  if (pageKey === 'finance') {
    destroyChartCollection(financeState.chartInstances);
    financeState.chartInstances = {};
    financeState.isSetup = false;
    return;
  }

  if (pageKey === 'projects') {
    destroyChartCollection(projectsState.chartInstances);
    projectsState.chartInstances = {};
    projectsState.isSetup = false;
    return;
  }

  if (pageKey === 'personal') {
    Object.values(personalState.autosaveTimers || {}).forEach((timer) => clearTimeout(timer));
    personalState.autosaveTimers = {};
    personalState.isSetup = false;
    return;
  }

  if (pageKey === 'education') {
    educationState.isSetup = false;
  }
}

function reinitializeActivePage(root = document, { resetState = false, loadData = true } = {}) {
  const pageRoot = getCurrentPageRoot(root);
  const pageKey = pageRoot?.dataset?.pageKey || document.body?.dataset?.page || 'dashboard';
  const previousPageKey = document.body?.dataset?.page || pageKey;

  if (resetState) {
    if (previousPageKey && previousPageKey !== pageKey) resetPageSetupState(previousPageKey);
    resetPageSetupState(pageKey);
  }

  updateShellPageState(root);
  enhanceInAppNavLinks(root);
  closeSidebarDrawer();
  setBodyScrollState();
  wrapTablesForMobile(root);
  updateCommonAppProgress(root);

  if (isAuthenticated()) {
    if (!isPersonalPage()) setupPageFormPersistence();
    setupUploadZones();
  }

  renderDashboardCalendar();
  animateProgressBars();
  runCounterAnimations();
  initObserverAnimations();
  refreshVisualEnhancements();
  initBucketPage();
  initCalendarPage();
  initEducationCommandCenter();
  setupNotificationCenterPage();

  if (loadData && isAuthenticated()) {
    loadUnlockedPageData();
  }
}

function setupHtmxNavigation() {
  if (!window.htmx || document.body.dataset.htmxNavReady === '1') return;
  document.body.dataset.htmxNavReady = '1';

  document.body.addEventListener('htmx:beforeRequest', (event) => {
    if (event.target?.id !== 'main-content-swap' && event.detail?.target?.id !== 'main-content-swap') return;
    closeNotifications();
    closeCommandPalette();
  });

  document.body.addEventListener('htmx:afterSwap', (event) => {
    const target = event.target || event.detail?.target;
    if (target?.id !== 'main-content-swap') return;
    reinitializeActivePage(target, { resetState: true, loadData: isAuthenticated() });
    requestAnimationFrame(() => {
      initObserverAnimations(target);
      initCardTilt(target);
      initMagneticButtons(target);
      initTabIndicators(target);
      initProgressBarAnimations(target);
      runCounterAnimations(target);
      setupButtonRipples();
      wrapTablesForMobile(target);
    });
  });
}

function initBucketPage() {
  if (getActivePage() !== 'bucket') return;
  const pageRoot = document.getElementById('page-bucket') || document;
  updateCategoryCounts();
  const active = pageRoot.querySelector('.bucket-cat.active') || pageRoot.querySelector('.bucket-cat');
  if (active) filterBucket(active);
  animateProgressBars();
  setupProgressCounters();

  const bucketForm = pageRoot.querySelector('#bucket-goal-form');
  if (bucketForm && bucketForm.dataset.ajax === 'true' && bucketForm.dataset.bound !== 'true') {
    bucketForm.dataset.bound = 'true';
    bucketForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const endpoint = bucketForm.getAttribute('action');
      if (!endpoint) return;
      const formData = new FormData(bucketForm);
      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            Accept: 'application/json',
          },
          body: formData,
          credentials: 'same-origin',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          showToast(data.error || 'Unable to save goal');
          return;
        }
        closeModal('bucket-goal-modal-overlay');
        window.location.reload();
      } catch (err) {
        showToast(err.message || 'Unable to save goal');
      }
    });
  }

  pageRoot.querySelectorAll('[data-close-modal]').forEach((el) => {
    if (el.dataset.closeBound === 'true') return;
    el.dataset.closeBound = 'true';
    el.addEventListener('click', () => closeModal(el.dataset.closeModal));
  });
  pageRoot.querySelectorAll('.modal-overlay').forEach((overlay) => {
    if (overlay.dataset.overlayBound === 'true') return;
    overlay.dataset.overlayBound = 'true';
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) overlay.classList.add('hidden');
    });
  });
}

function initCalendarPage() {
  const pageRoot = getCurrentPageRoot();
  if (getActivePage() !== 'calendar' || !pageRoot || pageRoot.dataset.calendarReady === '1') return;
  pageRoot.dataset.calendarReady = '1';
      const grid = document.getElementById('cal-grid');
      const monthLabel = document.getElementById('cal-month-label');
      const today = new Date();
      let currentYear = today.getFullYear();
      let currentMonth = today.getMonth() + 1;
      let allEvents = [];
  
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  
      function updateLabel() {
        if (monthLabel) {
          monthLabel.textContent = `${monthNames[currentMonth - 1]} ${currentYear}`;
        }
      }
  
      async function loadCalendar() {
        if (!grid) return;
        grid.innerHTML = '<div class="cal-loading">Loading...</div>';
        try {
          const response = await fetch(`/api/calendar/events/?year=${currentYear}&month=${currentMonth}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
          });
          const data = await response.json();
          allEvents = data.events || [];
          renderCalendar();
        } catch (error) {
          grid.innerHTML = '<div class="cal-loading">Failed to load events.</div>';
        }
      }
  
      function renderCalendar() {
        if (!grid) return;
        grid.innerHTML = '';
        const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();
        const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
        const prevMonthDays = new Date(currentYear, currentMonth - 1, 0).getDate();
  
        for (let i = firstDay - 1; i >= 0; i -= 1) {
          const day = document.createElement('div');
          day.className = 'cal-day other-month';
          day.innerHTML = `<div class="cal-day-num">${prevMonthDays - i}</div>`;
          grid.appendChild(day);
        }
  
        for (let dayNumber = 1; dayNumber <= daysInMonth; dayNumber += 1) {
          const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(dayNumber).padStart(2, '0')}`;
          const isToday = dayNumber === today.getDate() && currentMonth === today.getMonth() + 1 && currentYear === today.getFullYear();
          const dayEvents = allEvents.filter((event) => event.date === dateStr);
  
          const day = document.createElement('div');
          day.className = `cal-day${isToday ? ' today' : ''}`;
          day.dataset.date = dateStr;
  
          let pillsHtml = dayEvents.slice(0, 3).map((event) =>
            `<div class="cal-event-pill" style="background:${event.color}22;color:${event.color};" title="${event.title}">${event.title}</div>`
          ).join('');
          if (dayEvents.length > 3) {
            pillsHtml += `<div class="cal-event-more">+${dayEvents.length - 3} more</div>`;
          }
  
          day.innerHTML = `<div class="cal-day-num">${dayNumber}</div>${pillsHtml}`;
          day.addEventListener('click', () => showDayDetail(dateStr, dayEvents));
          grid.appendChild(day);
        }
  
        const totalCells = firstDay + daysInMonth;
        const remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
        for (let nextDay = 1; nextDay <= remaining; nextDay += 1) {
          const day = document.createElement('div');
          day.className = 'cal-day other-month';
          day.innerHTML = `<div class="cal-day-num">${nextDay}</div>`;
          grid.appendChild(day);
        }
      }
  
      function showDayDetail(dateStr, events) {
        const panel = document.getElementById('cal-event-detail');
        const list = document.getElementById('cal-detail-list');
        const dateLabel = document.getElementById('cal-detail-date');
        const parsed = new Date(`${dateStr}T00:00:00`);
        if (dateLabel) {
          dateLabel.textContent = parsed.toLocaleDateString('en-KE', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          });
        }
        if (!list || !panel) return;
        if (!events.length) {
          list.innerHTML = '<p class="cal-empty-detail">No events on this day.</p>';
        } else {
          list.innerHTML = events.map((event) => `
            <div class="cal-event-detail-item">
              <div class="cal-event-dot" style="background:${event.color};"></div>
              <div>
                <a href="${event.url}" class="cal-event-link" data-inapp-nav="true">${event.title}</a>
                <div class="cal-event-meta">${event.type}${event.is_done ? ' - Done' : ''}</div>
              </div>
            </div>
          `).join('');
        }
        panel.style.display = 'block';
        enhanceInAppNavLinks(list);
      }
  
      document.getElementById('cal-prev')?.addEventListener('click', () => {
        currentMonth -= 1;
        if (currentMonth < 1) {
          currentMonth = 12;
          currentYear -= 1;
        }
        updateLabel();
        loadCalendar();
      });
  
      document.getElementById('cal-next')?.addEventListener('click', () => {
        currentMonth += 1;
        if (currentMonth > 12) {
          currentMonth = 1;
          currentYear += 1;
        }
        updateLabel();
        loadCalendar();
      });
  
      document.getElementById('cal-today')?.addEventListener('click', () => {
        currentYear = today.getFullYear();
        currentMonth = today.getMonth() + 1;
        updateLabel();
        loadCalendar();
      });
  
      updateLabel();
      loadCalendar();
}

function initEducationCommandCenter() {
  const pageRoot = getCurrentPageRoot();
  if (getActivePage() !== 'education' || !pageRoot || pageRoot.dataset.educationCommandCenterReady === '1') return;
  pageRoot.dataset.educationCommandCenterReady = '1';
    const initializedEduTabs = new Set();
    const directionPanel = document.getElementById('edu-direction');
    const knowledgePanel = document.getElementById('edu-knowledge');
    const actionPanel = document.getElementById('edu-action');
    const optimizationPanel = document.getElementById('edu-optimization');
    const collegePanel = document.getElementById('edu-college');
  
    const dayConfig = [
      { key: 'monday', label: 'Mon' },
      { key: 'tuesday', label: 'Tue' },
      { key: 'wednesday', label: 'Wed' },
      { key: 'thursday', label: 'Thu' },
      { key: 'friday', label: 'Fri' },
      { key: 'saturday', label: 'Sat' },
      { key: 'sunday', label: 'Sun' },
    ];
  
    const paraCategories = [
      { key: 'projects', label: 'Projects', icon: '📁' },
      { key: 'areas', label: 'Areas', icon: '🧭' },
      { key: 'resources', label: 'Resources', icon: '📚' },
      { key: 'archive', label: 'Archive', icon: '🗄️' },
    ];
  
    const collegeColumns = [
      { key: 'researching', label: 'Researching', statuses: ['researching'] },
      { key: 'applied', label: 'Applied', statuses: ['applied'] },
      { key: 'interview', label: 'Interview', statuses: ['interview'] },
      { key: 'offer_received', label: 'Offer Received', statuses: ['offer_received'] },
      { key: 'decision_made', label: 'Decision Made', statuses: ['accepted', 'rejected', 'withdrawn', 'deferred'] },
    ];
  
    const statusLabels = {
      researching: 'Researching',
      applied: 'Applied',
      interview: 'Interview',
      offer_received: 'Offer Received',
      accepted: 'Accepted',
      rejected: 'Rejected',
      withdrawn: 'Withdrawn',
      deferred: 'Deferred',
      not_started: 'Not Started',
      draft: 'Draft',
      reviewed: 'Reviewed',
      final: 'Final',
      drafting: 'Drafting',
      reviewing: 'Reviewing',
      active: 'Active',
      paused: 'Paused',
      archived: 'Archived',
      book: 'Book',
      course: 'Course',
      podcast: 'Podcast',
      youtube: 'YouTube',
      mentor: 'Mentor',
      tool: 'Tool',
      other: 'Other',
    };
  
    const defaultCollegeRequirements = [
      'Personal Statement',
      'CV',
      'Transcripts',
      'Recommendations',
      'English Test Score',
      'Financial Proof',
    ];
  
    const uiState = {
      roadmapInlineOpen: false,
      timeBlockEditor: { dayKey: '', id: '', startTime: '', endTime: '', subject: '', isDeepWork: true },
      paraDrag: null,
      collegeDragAppId: '',
      reflectionOpenIds: new Set(),
      expandedCollegeApps: new Set(),
    };
  
    function cloneValue(value) {
      if (value === undefined || value === null) return value;
      if (Array.isArray(value) || typeof value === 'object') {
        return JSON.parse(JSON.stringify(value));
      }
      return value;
    }
  
    function saveToLS(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        console.warn(`Unable to save ${key}`, error);
      }
      return value;
    }
  
    function loadFromLS(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw === null ? cloneValue(fallback) : JSON.parse(raw);
      } catch (error) {
        console.warn(`Unable to load ${key}`, error);
        return cloneValue(fallback);
      }
    }
  
    window.saveToLS = saveToLS;
    window.loadFromLS = loadFromLS;
  
    function notify(message) {
      if (window.showToast) {
        window.showToast(message);
      }
    }
  
    function escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
  
    function createId(prefix) {
      return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    }
  
    function formatDate(dateString) {
      if (!dateString) return '—';
      const date = new Date(dateString);
      if (Number.isNaN(date.getTime())) return '—';
      return new Intl.DateTimeFormat(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      }).format(date);
    }
  
    function formatDateTime(dateString) {
      if (!dateString) return '—';
      const date = new Date(dateString);
      if (Number.isNaN(date.getTime())) return '—';
      return new Intl.DateTimeFormat(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }).format(date);
    }
  
    function isoNow() {
      return new Date().toISOString();
    }
  
    function todayISO() {
      return new Date().toISOString().slice(0, 10);
    }
  
    function truncateText(text, maxLength) {
      const safe = String(text ?? '').trim();
      if (!safe) return '—';
      return safe.length > maxLength ? `${safe.slice(0, maxLength - 1)}…` : safe;
    }
  
    function wordCount(text) {
      const safe = String(text ?? '').trim();
      return safe ? safe.split(/\s+/).length : 0;
    }
  
    function daysUntil(dateString) {
      if (!dateString) return null;
      const target = new Date(dateString);
      if (Number.isNaN(target.getTime())) return null;
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const end = new Date(target.getFullYear(), target.getMonth(), target.getDate());
      return Math.ceil((end - start) / 86400000);
    }
  
    function calculateHours(startTime, endTime) {
      if (!startTime || !endTime) return 0;
      const [startHour, startMinute] = startTime.split(':').map(Number);
      const [endHour, endMinute] = endTime.split(':').map(Number);
      if ([startHour, startMinute, endHour, endMinute].some(Number.isNaN)) return 0;
      const startTotal = (startHour * 60) + startMinute;
      const endTotal = (endHour * 60) + endMinute;
      if (endTotal <= startTotal) return 0;
      return (endTotal - startTotal) / 60;
    }
  
    function statusLabel(value) {
      return statusLabels[value] || value || 'Unknown';
    }
  
    function blankParaData() {
      return {
        projects: [],
        areas: [],
        resources: [],
        archive: [],
      };
    }
  
    function blankTimeBlocks() {
      return dayConfig.reduce((accumulator, day) => {
        accumulator[day.key] = [];
        return accumulator;
      }, {});
    }
  
    function normalizeTimeBlocks(data) {
      const base = blankTimeBlocks();
      dayConfig.forEach((day) => {
        base[day.key] = Array.isArray(data?.[day.key]) ? data[day.key] : [];
      });
      return base;
    }
  
    function getSkillInventory() {
      return loadFromLS('skill_inventory', []);
    }
  
    function saveSkillInventory(skills) {
      return saveToLS('skill_inventory', skills);
    }
  
    function getGrowthRoadmap() {
      return loadFromLS('growth_roadmap', {
        shortVision: '',
        longVision: '',
        milestones: [],
      });
    }
  
    function saveGrowthRoadmap(roadmap) {
      return saveToLS('growth_roadmap', roadmap);
    }
  
    function getCaptureInbox() {
      return loadFromLS('capture_inbox', []);
    }
  
    function saveCaptureInbox(items) {
      return saveToLS('capture_inbox', items);
    }
  
    function getParaKnowledgeBase() {
      return Object.assign(blankParaData(), loadFromLS('para_knowledge_base', blankParaData()));
    }
  
    function saveParaKnowledgeBase(data) {
      return saveToLS('para_knowledge_base', data);
    }
  
    function getFeynmanLog() {
      return loadFromLS('feynman_log', []);
    }
  
    function saveFeynmanLog(entries) {
      return saveToLS('feynman_log', entries);
    }
  
    function getLearningTimeBlocks() {
      return normalizeTimeBlocks(loadFromLS('learning_time_blocks', blankTimeBlocks()));
    }
  
    function saveLearningTimeBlocks(blocks) {
      return saveToLS('learning_time_blocks', normalizeTimeBlocks(blocks));
    }
  
    function getLearningBalance() {
      return loadFromLS('learning_balance', { doing: 0, others: 0, formal: 0 });
    }
  
    function saveLearningBalance(balance) {
      return saveToLS('learning_balance', balance);
    }
  
    function getMicroRoutines() {
      return loadFromLS('micro_routines', []);
    }
  
    function saveMicroRoutines(routines) {
      return saveToLS('micro_routines', routines);
    }
  
    function getWeeklyReflections() {
      return loadFromLS('weekly_reflections', []);
    }
  
    function saveWeeklyReflections(reflections) {
      return saveToLS('weekly_reflections', reflections);
    }
  
    function getSkillChecklists() {
      return loadFromLS('skill_checklists', {});
    }
  
    function saveSkillChecklists(checklists) {
      return saveToLS('skill_checklists', checklists);
    }
  
    function getResourceAudit() {
      return loadFromLS('resource_audit', []);
    }
  
    function saveResourceAudit(resources) {
      return saveToLS('resource_audit', resources);
    }
  
    function getCollegeApplications() {
      return loadFromLS('college_applications', []);
    }
  
    function saveCollegeApplications(applications) {
      return saveToLS('college_applications', applications);
    }
  
    function getCollegeEssays() {
      return loadFromLS('college_essays', []);
    }
  
    function saveCollegeEssays(essays) {
      return saveToLS('college_essays', essays);
    }
  
    function normalizeCollegeRequirements(requirements) {
      const list = Array.isArray(requirements) ? requirements : [];
      return list.map((requirement) => ({
        id: requirement.id || createId('college-req'),
        name: requirement.name || 'Requirement',
        completed: Boolean(requirement.completed),
        linkedDocumentId: requirement.linkedDocumentId || '',
        linkedDocumentTitle: requirement.linkedDocumentTitle || '',
      }));
    }
  
    function ensureCollegeRequirements(app) {
      if (Array.isArray(app.requirements) && app.requirements.length) {
        return normalizeCollegeRequirements(app.requirements);
      }
      return defaultCollegeRequirements.map((name) => ({
        id: createId('college-req'),
        name,
        completed: false,
        linkedDocumentId: '',
        linkedDocumentTitle: '',
      }));
    }
  
    function getRequirementProgress(application) {
      const requirements = ensureCollegeRequirements(application);
      const completed = requirements.filter((requirement) => requirement.completed).length;
      return {
        total: requirements.length,
        completed,
        percent: requirements.length ? Math.round((completed / requirements.length) * 100) : 0,
      };
    }
  
    function getEducationDocuments() {
      try {
        if (typeof educationState !== 'undefined' && Array.isArray(educationState.documents) && educationState.documents.length) {
          return educationState.documents.map((document) => ({
            id: String(document.id),
            title: document.title || 'Document',
            label: `${document.title || 'Document'} (${document.version || 'v1'})`,
          }));
        }
      } catch (error) {
        console.warn('Document state unavailable', error);
      }
  
      return Array.from(document.querySelectorAll('#document-table-body tr')).map((row, index) => {
        const title = row.children[0]?.textContent?.trim();
        const version = row.children[2]?.textContent?.trim() || 'v1';
        if (!title || title.includes('No documents uploaded yet.')) return null;
        return {
          id: `document-row-${index}`,
          title,
          label: `${title} (${version})`,
        };
      }).filter(Boolean);
    }
  
    function getScholarshipOptions() {
      try {
        if (typeof educationState !== 'undefined' && Array.isArray(educationState.scholarships) && educationState.scholarships.length) {
          return educationState.scholarships.map((scholarship) => scholarship.name).filter(Boolean);
        }
      } catch (error) {
        console.warn('Scholarship state unavailable', error);
      }
  
      return Array.from(document.querySelectorAll('#scholarship-grid .education-title'))
        .map((item) => item.textContent.trim())
        .filter(Boolean);
    }
  
    function buildRequirementDocumentOptions(selectedId) {
      const documents = getEducationDocuments();
      const emptyLabel = documents.length ? 'None linked' : 'No vault docs yet';
      const options = [`<option value="">${escapeHtml(emptyLabel)}</option>`];
      documents.forEach((document) => {
        options.push(`<option value="${escapeHtml(document.id)}" ${String(selectedId) === String(document.id) ? 'selected' : ''}>${escapeHtml(document.label)}</option>`);
      });
      return options.join('');
    }
  
    function populateScholarshipDatalist() {
      const datalist = document.getElementById('college-scholarship-options');
      if (!datalist) return;
      datalist.innerHTML = getScholarshipOptions().map((option) => `<option value="${escapeHtml(option)}"></option>`).join('');
    }
  
    function populateCollegeEssayOptions(selectedApplicationId) {
      const select = document.getElementById('college-essay-application-id');
      if (!select) return;
      const applications = getCollegeApplications();
      if (!applications.length) {
        select.innerHTML = '<option value="">Add a college application first</option>';
        return;
      }
      select.innerHTML = applications.map((application) => `<option value="${escapeHtml(application.id)}" ${String(selectedApplicationId) === String(application.id) ? 'selected' : ''}>${escapeHtml(application.universityName)} · ${escapeHtml(application.program)}</option>`).join('');
    }
  
    function deadlineClass(daysLeft) {
      if (daysLeft === null) return 'safe';
      if (daysLeft <= 7) return 'urgent';
      if (daysLeft <= 30) return 'warning';
      return 'safe';
    }
  
    function collegeStatusClass(status) {
      if (status === 'accepted') return 'accepted';
      if (status === 'rejected' || status === 'withdrawn') return 'rejected';
      if (status === 'offer_received') return 'offer';
      if (status === 'interview') return 'interview';
      return 'pending';
    }
  
    function countryToFlag(country) {
      const normalized = String(country || '').trim();
      if (!normalized) return '🌍';
      const lookup = {
        kenya: 'KE',
        uganda: 'UG',
        tanzania: 'TZ',
        rwanda: 'RW',
        ethiopia: 'ET',
        ghana: 'GH',
        nigeria: 'NG',
        south_africa: 'ZA',
        'south africa': 'ZA',
        usa: 'US',
        us: 'US',
        'united states': 'US',
        'united states of america': 'US',
        uk: 'GB',
        gb: 'GB',
        'united kingdom': 'GB',
        england: 'GB',
        canada: 'CA',
        australia: 'AU',
        new_zealand: 'NZ',
        germany: 'DE',
        france: 'FR',
        italy: 'IT',
        spain: 'ES',
        netherlands: 'NL',
        china: 'CN',
        japan: 'JP',
        india: 'IN',
        singapore: 'SG',
        ireland: 'IE',
        sweden: 'SE',
        norway: 'NO',
        finland: 'FI',
        switzerland: 'CH',
      };
      const key = normalized.toLowerCase().replace(/\s+/g, '_');
      const code = /^[A-Za-z]{2}$/.test(normalized) ? normalized.toUpperCase() : lookup[key];
      if (!code || !/^[A-Z]{2}$/.test(code)) return '🌍';
      return String.fromCodePoint(...code.split('').map((char) => 127397 + char.charCodeAt()));
    }
  
    function universityCode(name) {
      const safe = String(name || '').trim();
      if (!safe) return 'APP';
      const words = safe.split(/\s+/).filter(Boolean);
      if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
      return words.slice(0, 3).map((word) => word[0]).join('').toUpperCase();
    }
  
    function mapStatusToColumn(status) {
      const match = collegeColumns.find((column) => column.statuses.includes(status));
      return match ? match.key : 'researching';
    }
  
    function mapColumnToStatus(columnKey, currentStatus) {
      if (columnKey === 'decision_made') {
        return ['accepted', 'rejected', 'withdrawn', 'deferred'].includes(currentStatus) ? currentStatus : 'accepted';
      }
      return columnKey;
    }
  
    function renderSkillInventory() {
      const grid = document.getElementById('skill-inventory-grid');
      if (!grid) return;
      const skills = getSkillInventory();
  
      if (!skills.length) {
        grid.innerHTML = '<div class="education-empty-state">Add your first skill to start mapping your growth.</div>';
        return;
      }
  
      const levelOptions = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
      const categoryOptions = ['Technical', 'Soft', 'Creative', 'Domain'];
  
      grid.innerHTML = skills.map((skill) => `
        <article class="learning-skill-card">
          <div class="learning-skill-name">${escapeHtml(skill.name)}</div>
          <div class="learning-skill-meta">
            <span class="learning-skill-badge">${escapeHtml(skill.targetLevel || 'Target TBD')}</span>
            <span class="learning-skill-badge">${escapeHtml(skill.category || 'General')}</span>
            ${skill.isGap ? '<span class="learning-skill-badge gap">Gap</span>' : ''}
          </div>
          <div class="education-skill-card-grid">
            <div class="form-field">
              <label for="skill-current-${escapeHtml(skill.id)}">Current Level</label>
              <select id="skill-current-${escapeHtml(skill.id)}" data-skill-field="currentLevel" data-skill-id="${escapeHtml(skill.id)}">
                ${levelOptions.map((option) => `<option value="${option}" ${skill.currentLevel === option ? 'selected' : ''}>${option}</option>`).join('')}
              </select>
            </div>
            <div class="form-field">
              <label for="skill-category-${escapeHtml(skill.id)}">Category</label>
              <select id="skill-category-${escapeHtml(skill.id)}" data-skill-field="category" data-skill-id="${escapeHtml(skill.id)}">
                ${categoryOptions.map((option) => `<option value="${option}" ${skill.category === option ? 'selected' : ''}>${option}</option>`).join('')}
              </select>
            </div>
          </div>
          <label class="education-inline-check" for="skill-gap-${escapeHtml(skill.id)}">
            <input id="skill-gap-${escapeHtml(skill.id)}" type="checkbox" data-skill-field="isGap" data-skill-id="${escapeHtml(skill.id)}" ${skill.isGap ? 'checked' : ''}>
            <span>Is a Gap</span>
          </label>
          ${skill.notes ? `<div class="education-support-copy">${escapeHtml(skill.notes)}</div>` : '<div class="education-support-copy">Add notes to clarify the next leap for this skill.</div>'}
          <div class="education-card-actions">
            <button class="btn-outline btn-mini" type="button" data-skill-edit="${escapeHtml(skill.id)}">Edit</button>
            <button class="btn-outline btn-mini danger" type="button" data-skill-delete="${escapeHtml(skill.id)}">Delete</button>
          </div>
        </article>
      `).join('');
    }
  
    function openSkillModal(skill) {
      const set = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.value = value ?? '';
      };
      set('skill-id', skill?.id || '');
      set('skill-name', skill?.name || '');
      set('skill-category', skill?.category || 'Technical');
      set('skill-current-level', skill?.currentLevel || 'Beginner');
      set('skill-target-level', skill?.targetLevel || 'Intermediate');
      set('skill-notes', skill?.notes || '');
      const gap = document.getElementById('skill-gap');
      if (gap) gap.checked = Boolean(skill?.isGap);
      const title = document.getElementById('skill-modal-title');
      if (title) title.textContent = skill ? 'Edit Skill' : 'Add Skill';
      populateScholarshipDatalist();
      if (window.openModal) window.openModal('skill-modal-overlay');
    }
  
    function handleSkillSubmit(event) {
      event.preventDefault();
      const skills = getSkillInventory();
      const skillId = document.getElementById('skill-id')?.value || createId('skill');
      const skill = {
        id: skillId,
        name: document.getElementById('skill-name')?.value?.trim() || '',
        category: document.getElementById('skill-category')?.value || 'Technical',
        currentLevel: document.getElementById('skill-current-level')?.value || 'Beginner',
        targetLevel: document.getElementById('skill-target-level')?.value || 'Intermediate',
        isGap: Boolean(document.getElementById('skill-gap')?.checked),
        notes: document.getElementById('skill-notes')?.value?.trim() || '',
      };
  
      if (!skill.name) {
        notify('Skill name is required.');
        return;
      }
  
      const index = skills.findIndex((item) => item.id === skillId);
      if (index >= 0) skills[index] = skill;
      else skills.unshift(skill);
      saveSkillInventory(skills);
      if (window.closeModal) window.closeModal('skill-modal-overlay');
      renderSkillInventory();
      renderSkillChecklists();
      notify(index >= 0 ? 'Skill updated.' : 'Skill added.');
    }
  
    function renderRoadmap() {
      const roadmap = getGrowthRoadmap();
      const shortInput = document.getElementById('roadmap-short');
      const longInput = document.getElementById('roadmap-long');
      if (shortInput) shortInput.value = roadmap.shortVision || '';
      if (longInput) longInput.value = roadmap.longVision || '';
  
      const body = document.getElementById('roadmap-milestone-body');
      if (!body) return;
  
      if (!roadmap.milestones.length) {
        body.innerHTML = '<tr><td colspan="4" class="table-empty">No milestones yet. Add one to make the vision tangible.</td></tr>';
      } else {
        body.innerHTML = roadmap.milestones.map((milestone) => `
          <tr>
            <td>${escapeHtml(milestone.name)}</td>
            <td>${escapeHtml(formatDate(milestone.targetDate))}</td>
            <td>
              <label class="education-inline-check" for="roadmap-done-${escapeHtml(milestone.id)}">
                <input id="roadmap-done-${escapeHtml(milestone.id)}" type="checkbox" data-roadmap-toggle="${escapeHtml(milestone.id)}" ${milestone.done ? 'checked' : ''}>
                <span>${milestone.done ? 'Done' : 'Pending'}</span>
              </label>
            </td>
            <td class="action-cell">
              <button class="btn-outline btn-mini danger" type="button" data-roadmap-delete="${escapeHtml(milestone.id)}">Delete</button>
            </td>
          </tr>
        `).join('');
      }
  
      const inlineForm = document.getElementById('roadmap-inline-form');
      if (inlineForm) inlineForm.classList.toggle('hidden', !uiState.roadmapInlineOpen);
    }
  
    function roadmapWithCurrentInputs() {
      const roadmap = getGrowthRoadmap();
      const shortInput = document.getElementById('roadmap-short');
      const longInput = document.getElementById('roadmap-long');
      roadmap.shortVision = shortInput ? shortInput.value.trim() : (roadmap.shortVision || '');
      roadmap.longVision = longInput ? longInput.value.trim() : (roadmap.longVision || '');
      return roadmap;
    }
  
    function saveRoadmapText() {
      const roadmap = roadmapWithCurrentInputs();
      saveGrowthRoadmap(roadmap);
      notify('Growth roadmap saved.');
    }
  
    function addRoadmapMilestone() {
      const name = document.getElementById('roadmap-milestone-name')?.value?.trim() || '';
      const targetDate = document.getElementById('roadmap-milestone-date')?.value || '';
      if (!name) {
        notify('Milestone name is required.');
        return;
      }
      const roadmap = roadmapWithCurrentInputs();
      roadmap.milestones.unshift({
        id: createId('roadmap'),
        name,
        targetDate,
        done: false,
      });
      saveGrowthRoadmap(roadmap);
      uiState.roadmapInlineOpen = false;
      const milestoneName = document.getElementById('roadmap-milestone-name');
      const milestoneDate = document.getElementById('roadmap-milestone-date');
      if (milestoneName) milestoneName.value = '';
      if (milestoneDate) milestoneDate.value = '';
      renderRoadmap();
      notify('Milestone added.');
    }
  
    function initDirectionTab() {
      if (directionPanel && !directionPanel.dataset.bound) {
        directionPanel.dataset.bound = '1';
        document.getElementById('save-learning-why-btn')?.addEventListener('click', () => {
          saveToLS('learning_why', document.getElementById('learning-why-statement')?.value || '');
          notify('Learning why saved.');
        });
        document.getElementById('add-skill-btn')?.addEventListener('click', () => openSkillModal(null));
        document.getElementById('save-roadmap-btn')?.addEventListener('click', saveRoadmapText);
        document.getElementById('add-roadmap-milestone-btn')?.addEventListener('click', () => {
          uiState.roadmapInlineOpen = true;
          renderRoadmap();
        });
        document.getElementById('cancel-roadmap-milestone-btn')?.addEventListener('click', () => {
          uiState.roadmapInlineOpen = false;
          renderRoadmap();
        });
        document.getElementById('save-roadmap-milestone-btn')?.addEventListener('click', addRoadmapMilestone);
        document.getElementById('skill-modal-form')?.addEventListener('submit', handleSkillSubmit);
  
        directionPanel.addEventListener('click', (event) => {
          const skillEdit = event.target.closest('[data-skill-edit]');
          if (skillEdit) {
            const skill = getSkillInventory().find((item) => item.id === skillEdit.dataset.skillEdit);
            openSkillModal(skill || null);
            return;
          }
  
          const skillDelete = event.target.closest('[data-skill-delete]');
          if (skillDelete) {
            const skills = getSkillInventory().filter((item) => item.id !== skillDelete.dataset.skillDelete);
            saveSkillInventory(skills);
            const checklists = getSkillChecklists();
            delete checklists[skillDelete.dataset.skillDelete];
            saveSkillChecklists(checklists);
            renderSkillInventory();
            renderSkillChecklists();
            notify('Skill removed.');
            return;
          }
  
          const roadmapDelete = event.target.closest('[data-roadmap-delete]');
          if (roadmapDelete) {
            const roadmap = roadmapWithCurrentInputs();
            roadmap.milestones = roadmap.milestones.filter((item) => item.id !== roadmapDelete.dataset.roadmapDelete);
            saveGrowthRoadmap(roadmap);
            renderRoadmap();
            notify('Milestone removed.');
          }
        });
  
        directionPanel.addEventListener('change', (event) => {
          const skillField = event.target.dataset.skillField;
          const skillId = event.target.dataset.skillId;
          if (skillField && skillId) {
            const skills = getSkillInventory();
            const skill = skills.find((item) => item.id === skillId);
            if (!skill) return;
            skill[skillField] = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
            saveSkillInventory(skills);
            renderSkillInventory();
            renderSkillChecklists();
            return;
          }
  
          const roadmapToggle = event.target.dataset.roadmapToggle;
          if (roadmapToggle) {
            const roadmap = roadmapWithCurrentInputs();
            const milestone = roadmap.milestones.find((item) => item.id === roadmapToggle);
            if (!milestone) return;
            milestone.done = event.target.checked;
            saveGrowthRoadmap(roadmap);
            renderRoadmap();
          }
        });
      }
  
      const whyInput = document.getElementById('learning-why-statement');
      if (whyInput) whyInput.value = loadFromLS('learning_why', '');
      renderSkillInventory();
      renderRoadmap();
    }
  
    function syncCaptureWithPara(captureId, categoryKey) {
      const inbox = getCaptureInbox();
      const para = getParaKnowledgeBase();
      const capture = inbox.find((item) => item.id === captureId);
      Object.keys(para).forEach((key) => {
        para[key] = para[key].filter((note) => note.captureId !== captureId);
      });
  
      if (capture && categoryKey) {
        para[categoryKey].unshift({
          id: captureId,
          captureId,
          text: capture.text,
          source: capture.source,
          type: capture.type,
          timestamp: capture.timestamp,
          origin: 'capture',
        });
      }
  
      saveCaptureInbox(inbox);
      saveParaKnowledgeBase(para);
    }
  
    function renderCaptureInbox() {
      const list = document.getElementById('capture-inbox-list');
      if (!list) return;
      const captures = getCaptureInbox();
  
      if (!captures.length) {
        list.innerHTML = '<div class="education-empty-state">Your capture inbox is empty. Start dropping in ideas and insights.</div>';
        return;
      }
  
      list.innerHTML = captures.map((item) => `
        <div class="capture-item">
          <span class="capture-type-badge">${escapeHtml(item.type)}</span>
          <div class="education-capture-copy">
            <div class="education-capture-text">${escapeHtml(item.text)}</div>
            <div class="education-capture-meta">${escapeHtml(item.source || 'No source')} · ${escapeHtml(formatDateTime(item.timestamp))}</div>
          </div>
          <div class="education-capture-actions">
            <div class="form-field">
              <label for="capture-para-${escapeHtml(item.id)}">Move to PARA</label>
              <select id="capture-para-${escapeHtml(item.id)}" data-capture-para="${escapeHtml(item.id)}">
                <option value="">Unassigned</option>
                ${paraCategories.map((category) => `<option value="${category.key}" ${item.paraCategory === category.key ? 'selected' : ''}>${category.label}</option>`).join('')}
              </select>
            </div>
            <button class="btn-outline btn-mini danger" type="button" data-capture-delete="${escapeHtml(item.id)}">Delete</button>
          </div>
        </div>
      `).join('');
    }
  
    function renderParaKnowledgeBase() {
      const para = getParaKnowledgeBase();
      paraCategories.forEach((category) => {
        const count = document.getElementById(`para-${category.key}-count`);
        const list = document.getElementById(`para-${category.key}-list`);
        if (count) count.textContent = String((para[category.key] || []).length);
        if (!list) return;
  
        const notes = para[category.key] || [];
        if (!notes.length) {
          list.innerHTML = '<div class="education-empty-state education-empty-state--compact">Nothing here yet. Drag a note in or add one directly.</div>';
          return;
        }
  
        list.innerHTML = notes.map((note) => `
          <div class="para-note-item" draggable="true" data-para-note-id="${escapeHtml(note.id)}" data-para-category="${escapeHtml(category.key)}">
            <div class="education-para-note-text">${escapeHtml(note.text)}</div>
            <div class="education-para-note-meta">${escapeHtml(note.source || note.type || 'Note')}</div>
            <button class="btn-outline btn-mini danger" type="button" data-para-delete="${escapeHtml(note.id)}">Delete</button>
          </div>
        `).join('');
      });
    }
  
    function renderFeynmanLog() {
      const list = document.getElementById('feynman-log-list');
      if (!list) return;
      const entries = getFeynmanLog();
      if (!entries.length) {
        list.innerHTML = '<div class="education-empty-state">No Feynman practice entries yet.</div>';
        return;
      }
  
      list.innerHTML = entries.map((entry) => `
        <article class="education-feynman-log-item">
          <div class="education-feynman-log-head">
            <div>
              <div class="education-feynman-log-title">${escapeHtml(entry.concept)}</div>
              <div class="education-feynman-log-date">${escapeHtml(formatDate(entry.savedAt))}</div>
            </div>
          </div>
          <div class="education-support-copy"><strong>Plain language:</strong> ${escapeHtml(truncateText(entry.explanation, 160))}</div>
        </article>
      `).join('');
    }
  
    function initKnowledgeTab() {
      if (knowledgePanel && !knowledgePanel.dataset.bound) {
        knowledgePanel.dataset.bound = '1';
        document.getElementById('capture-submit-btn')?.addEventListener('click', () => {
          const text = document.getElementById('capture-input')?.value?.trim() || '';
          if (!text) {
            notify('Capture text is required.');
            return;
          }
          const captures = getCaptureInbox();
          captures.unshift({
            id: createId('capture'),
            text,
            source: document.getElementById('capture-source')?.value?.trim() || '',
            type: document.getElementById('capture-type')?.value || 'Thought',
            timestamp: isoNow(),
            paraCategory: '',
          });
          saveCaptureInbox(captures);
          const captureInput = document.getElementById('capture-input');
          const captureSource = document.getElementById('capture-source');
          const captureType = document.getElementById('capture-type');
          if (captureInput) captureInput.value = '';
          if (captureSource) captureSource.value = '';
          if (captureType) captureType.value = 'Book Quote';
          renderCaptureInbox();
          renderParaKnowledgeBase();
          notify('Captured to inbox.');
        });
  
        document.getElementById('feynman-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const concept = document.getElementById('feynman-concept')?.value?.trim() || '';
          if (!concept) {
            notify('Concept is required.');
            return;
          }
          const entries = getFeynmanLog();
          entries.unshift({
            id: createId('feynman'),
            concept,
            explanation: document.getElementById('feynman-plain-language')?.value?.trim() || '',
            gaps: document.getElementById('feynman-gaps')?.value?.trim() || '',
            simplified: document.getElementById('feynman-simplified')?.value?.trim() || '',
            savedAt: todayISO(),
          });
          saveFeynmanLog(entries);
          event.target.reset();
          renderFeynmanLog();
          notify('Feynman practice saved.');
        });
  
        knowledgePanel.addEventListener('click', (event) => {
          const captureDelete = event.target.closest('[data-capture-delete]');
          if (captureDelete) {
            const captureId = captureDelete.dataset.captureDelete;
            saveCaptureInbox(getCaptureInbox().filter((item) => item.id !== captureId));
            const para = getParaKnowledgeBase();
            Object.keys(para).forEach((key) => {
              para[key] = para[key].filter((item) => item.captureId !== captureId && item.id !== captureId);
            });
            saveParaKnowledgeBase(para);
            renderCaptureInbox();
            renderParaKnowledgeBase();
            notify('Capture removed.');
            return;
          }
  
          const paraAdd = event.target.closest('[data-para-add]');
          if (paraAdd) {
            const category = paraAdd.dataset.paraAdd;
            const text = window.prompt(`Add a note directly to ${statusLabel(category)}:`);
            if (!text || !text.trim()) return;
            const para = getParaKnowledgeBase();
            para[category].unshift({
              id: createId('para'),
              text: text.trim(),
              source: 'Direct note',
              type: 'Other',
              timestamp: isoNow(),
              origin: 'manual',
            });
            saveParaKnowledgeBase(para);
            renderParaKnowledgeBase();
            notify('Note added to PARA.');
            return;
          }
  
          const paraDelete = event.target.closest('[data-para-delete]');
          if (paraDelete) {
            const para = getParaKnowledgeBase();
            let removedNote = null;
            Object.keys(para).forEach((key) => {
              const existing = para[key].find((item) => item.id === paraDelete.dataset.paraDelete);
              if (existing) removedNote = existing;
              para[key] = para[key].filter((item) => item.id !== paraDelete.dataset.paraDelete);
            });
            if (removedNote?.captureId) {
              const captures = getCaptureInbox();
              const capture = captures.find((item) => item.id === removedNote.captureId);
              if (capture) capture.paraCategory = '';
              saveCaptureInbox(captures);
              renderCaptureInbox();
            }
            saveParaKnowledgeBase(para);
            renderParaKnowledgeBase();
            notify('PARA note removed.');
          }
        });
  
        knowledgePanel.addEventListener('change', (event) => {
          const captureId = event.target.dataset.capturePara;
          if (!captureId) return;
          const captures = getCaptureInbox();
          const capture = captures.find((item) => item.id === captureId);
          if (!capture) return;
          capture.paraCategory = event.target.value;
          saveCaptureInbox(captures);
          syncCaptureWithPara(captureId, event.target.value);
          renderCaptureInbox();
          renderParaKnowledgeBase();
        });
  
        knowledgePanel.addEventListener('dragstart', (event) => {
          const note = event.target.closest('[data-para-note-id]');
          if (!note) return;
          uiState.paraDrag = {
            noteId: note.dataset.paraNoteId,
            fromCategory: note.dataset.paraCategory,
          };
          event.dataTransfer?.setData('text/plain', note.dataset.paraNoteId);
        });
  
        knowledgePanel.addEventListener('dragover', (event) => {
          const zone = event.target.closest('[data-para-category]');
          if (!zone) return;
          event.preventDefault();
          zone.classList.add('education-drop-active');
        });
  
        knowledgePanel.addEventListener('dragleave', (event) => {
          const zone = event.target.closest('[data-para-category]');
          if (!zone) return;
          zone.classList.remove('education-drop-active');
        });
  
        knowledgePanel.addEventListener('drop', (event) => {
          const zone = event.target.closest('[data-para-category]');
          if (!zone || !uiState.paraDrag) return;
          event.preventDefault();
          zone.classList.remove('education-drop-active');
          const toCategory = zone.dataset.paraCategory;
          const para = getParaKnowledgeBase();
          let movingNote = null;
          Object.keys(para).forEach((key) => {
            const found = para[key].find((item) => item.id === uiState.paraDrag.noteId);
            if (found) movingNote = found;
            para[key] = para[key].filter((item) => item.id !== uiState.paraDrag.noteId);
          });
          if (movingNote) {
            para[toCategory].unshift(movingNote);
            if (movingNote.captureId) {
              const captures = getCaptureInbox();
              const capture = captures.find((item) => item.id === movingNote.captureId);
              if (capture) capture.paraCategory = toCategory;
              saveCaptureInbox(captures);
              renderCaptureInbox();
            }
            saveParaKnowledgeBase(para);
            renderParaKnowledgeBase();
          }
          uiState.paraDrag = null;
        });
      }
  
      renderCaptureInbox();
      renderParaKnowledgeBase();
      renderFeynmanLog();
    }
  
    function renderLearningTimeBlocks() {
      const grid = document.getElementById('learning-time-block-grid');
      const summary = document.getElementById('learning-deep-work-summary');
      if (!grid) return;
      const blocksByDay = getLearningTimeBlocks();
      const totalDeepWork = dayConfig.reduce((sum, day) => {
        return sum + blocksByDay[day.key].reduce((daySum, block) => daySum + (block.isDeepWork ? calculateHours(block.startTime, block.endTime) : 0), 0);
      }, 0);
  
      if (summary) {
        summary.textContent = `Total deep work hours this week: ${totalDeepWork.toFixed(1)} hrs`;
      }
  
      grid.innerHTML = dayConfig.map((day) => {
        const blocks = blocksByDay[day.key]
          .slice()
          .sort((left, right) => String(left.startTime || '').localeCompare(String(right.startTime || '')));
        const isEditing = uiState.timeBlockEditor.dayKey === day.key;
        return `
          <section class="education-time-day-card">
            <div class="education-time-day-head">
              <div class="education-time-day-label">${day.label}</div>
              <button class="btn-outline btn-mini" type="button" data-time-block-add="${day.key}">Add Time Block</button>
            </div>
            <div class="education-time-block-list">
              ${blocks.length ? blocks.map((block) => `
                <div class="education-time-block-item">
                  <div>
                    <div class="education-time-block-subject">${escapeHtml(block.subject)}</div>
                    <div class="education-time-block-meta">${escapeHtml(block.startTime)} - ${escapeHtml(block.endTime)}${block.isDeepWork ? ' · Deep Work' : ''}</div>
                  </div>
                  <div class="education-card-actions">
                    <button class="btn-outline btn-mini" type="button" data-time-block-edit="${escapeHtml(block.id)}" data-time-block-day="${day.key}">Edit</button>
                    <button class="btn-outline btn-mini danger" type="button" data-time-block-delete="${escapeHtml(block.id)}" data-time-block-day="${day.key}">Delete</button>
                  </div>
                </div>
              `).join('') : '<div class="education-empty-state education-empty-state--compact">No time blocks yet.</div>'}
            </div>
            ${isEditing ? `
              <div class="education-time-block-editor">
                <div class="form-field">
                  <label for="time-block-start-${day.key}">Start Time</label>
                  <input id="time-block-start-${day.key}" type="time" value="${escapeHtml(uiState.timeBlockEditor.startTime || '')}">
                </div>
                <div class="form-field">
                  <label for="time-block-end-${day.key}">End Time</label>
                  <input id="time-block-end-${day.key}" type="time" value="${escapeHtml(uiState.timeBlockEditor.endTime || '')}">
                </div>
                <div class="form-field">
                  <label for="time-block-subject-${day.key}">Subject / Topic</label>
                  <input id="time-block-subject-${day.key}" type="text" value="${escapeHtml(uiState.timeBlockEditor.subject || '')}">
                </div>
                <label class="education-inline-check" for="time-block-deep-${day.key}">
                  <input id="time-block-deep-${day.key}" type="checkbox" ${uiState.timeBlockEditor.isDeepWork ? 'checked' : ''}>
                  <span>Deep Work</span>
                </label>
                <div class="education-card-actions">
                  <button class="btn-outline btn-mini" type="button" data-time-block-cancel="${day.key}">Cancel</button>
                  <button class="btn-primary btn-mini" type="button" data-time-block-save="${day.key}" data-time-block-id="${escapeHtml(uiState.timeBlockEditor.id || '')}">Save</button>
                </div>
              </div>
            ` : ''}
          </section>
        `;
      }).join('');
    }
  
    function openTimeBlockEditor(dayKey, block) {
      uiState.timeBlockEditor = {
        dayKey,
        id: block?.id || '',
        startTime: block?.startTime || '',
        endTime: block?.endTime || '',
        subject: block?.subject || '',
        isDeepWork: block ? Boolean(block.isDeepWork) : true,
      };
      renderLearningTimeBlocks();
    }
  
    function saveTimeBlock(dayKey, blockId) {
      const startTime = document.getElementById(`time-block-start-${dayKey}`)?.value || '';
      const endTime = document.getElementById(`time-block-end-${dayKey}`)?.value || '';
      const subject = document.getElementById(`time-block-subject-${dayKey}`)?.value?.trim() || '';
      const isDeepWork = Boolean(document.getElementById(`time-block-deep-${dayKey}`)?.checked);
  
      if (!startTime || !endTime || !subject) {
        notify('Start time, end time, and subject are required.');
        return;
      }
  
      const blocks = getLearningTimeBlocks();
      const list = blocks[dayKey] || [];
      const nextBlock = {
        id: blockId || createId('block'),
        startTime,
        endTime,
        subject,
        isDeepWork,
      };
      const index = list.findIndex((item) => item.id === nextBlock.id);
      if (index >= 0) list[index] = nextBlock;
      else list.unshift(nextBlock);
      blocks[dayKey] = list;
      saveLearningTimeBlocks(blocks);
      uiState.timeBlockEditor = { dayKey: '', id: '', startTime: '', endTime: '', subject: '', isDeepWork: true };
      renderLearningTimeBlocks();
      notify(index >= 0 ? 'Time block updated.' : 'Time block added.');
    }
  
    function updateLearningBalanceChart() {
      const doing = Number(document.getElementById('learning-balance-doing')?.value || 0);
      const others = Number(document.getElementById('learning-balance-others')?.value || 0);
      const formal = Number(document.getElementById('learning-balance-formal')?.value || 0);
      const total = doing + others + formal;
      const p1 = total ? (doing / total) * 100 : 70;
      const p2 = total ? (others / total) * 100 : 20;
      const donut = document.getElementById('learning-balance-donut');
      if (donut) {
        donut.style.background = `conic-gradient(var(--olive) 0% ${p1}%, var(--sage) ${p1}% ${p1 + p2}%, var(--ivory-soft) ${p1 + p2}% 100%)`;
      }
      document.getElementById('learning-balance-doing-label').textContent = `Doing: ${doing} hrs`;
      document.getElementById('learning-balance-others-label').textContent = `From Others: ${others} hrs`;
      document.getElementById('learning-balance-formal-label').textContent = `Formal Study: ${formal} hrs`;
      saveLearningBalance({ doing, others, formal });
    }
  
    function renderMicroRoutines() {
      const list = document.getElementById('micro-routine-list');
      if (!list) return;
      const routines = getMicroRoutines();
      if (!routines.length) {
        list.innerHTML = '<div class="education-empty-state">Add a small routine and let the streak compound.</div>';
        return;
      }
      list.innerHTML = routines.map((routine) => `
        <div class="micro-routine-item">
          <div class="routine-streak">${escapeHtml(routine.streak || 0)}</div>
          <div class="routine-name">${escapeHtml(routine.name)}</div>
          <div class="routine-trigger">${escapeHtml(routine.trigger)} · ${escapeHtml(routine.frequency)}</div>
          <div class="education-card-actions">
            <button class="btn-primary btn-mini" type="button" data-routine-today="${escapeHtml(routine.id)}">✓ Today</button>
            <button class="btn-outline btn-mini danger" type="button" data-routine-delete="${escapeHtml(routine.id)}">Delete</button>
          </div>
        </div>
      `).join('');
    }
  
    function initActionTab() {
      if (actionPanel && !actionPanel.dataset.bound) {
        actionPanel.dataset.bound = '1';
        const balance = getLearningBalance();
        const doingInput = document.getElementById('learning-balance-doing');
        const othersInput = document.getElementById('learning-balance-others');
        const formalInput = document.getElementById('learning-balance-formal');
        if (doingInput) doingInput.value = balance.doing;
        if (othersInput) othersInput.value = balance.others;
        if (formalInput) formalInput.value = balance.formal;
  
        ['learning-balance-doing', 'learning-balance-others', 'learning-balance-formal'].forEach((id) => {
          document.getElementById(id)?.addEventListener('input', updateLearningBalanceChart);
          document.getElementById(id)?.addEventListener('change', updateLearningBalanceChart);
        });
  
        document.getElementById('micro-routine-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const name = document.getElementById('micro-routine-name')?.value?.trim() || '';
          const trigger = document.getElementById('micro-routine-trigger')?.value?.trim() || '';
          const frequency = document.getElementById('micro-routine-frequency')?.value || 'Daily';
          if (!name || !trigger) {
            notify('Habit and trigger are required.');
            return;
          }
          const routines = getMicroRoutines();
          routines.unshift({
            id: createId('routine'),
            name,
            trigger,
            frequency,
            streak: 0,
          });
          saveMicroRoutines(routines);
          event.target.reset();
          renderMicroRoutines();
          notify('Micro-routine added.');
        });
  
        actionPanel.addEventListener('click', (event) => {
          const addBlock = event.target.closest('[data-time-block-add]');
          if (addBlock) {
            openTimeBlockEditor(addBlock.dataset.timeBlockAdd, null);
            return;
          }
  
          const editBlock = event.target.closest('[data-time-block-edit]');
          if (editBlock) {
            const blocks = getLearningTimeBlocks()[editBlock.dataset.timeBlockDay] || [];
            const block = blocks.find((item) => item.id === editBlock.dataset.timeBlockEdit);
            openTimeBlockEditor(editBlock.dataset.timeBlockDay, block || null);
            return;
          }
  
          const deleteBlock = event.target.closest('[data-time-block-delete]');
          if (deleteBlock) {
            const blocks = getLearningTimeBlocks();
            blocks[deleteBlock.dataset.timeBlockDay] = blocks[deleteBlock.dataset.timeBlockDay].filter((item) => item.id !== deleteBlock.dataset.timeBlockDelete);
            saveLearningTimeBlocks(blocks);
            renderLearningTimeBlocks();
            notify('Time block removed.');
            return;
          }
  
          const cancelBlock = event.target.closest('[data-time-block-cancel]');
          if (cancelBlock) {
            uiState.timeBlockEditor = { dayKey: '', id: '', startTime: '', endTime: '', subject: '', isDeepWork: true };
            renderLearningTimeBlocks();
            return;
          }
  
          const saveBlock = event.target.closest('[data-time-block-save]');
          if (saveBlock) {
            saveTimeBlock(saveBlock.dataset.timeBlockSave, saveBlock.dataset.timeBlockId || '');
            return;
          }
  
          const routineToday = event.target.closest('[data-routine-today]');
          if (routineToday) {
            const routines = getMicroRoutines();
            const routine = routines.find((item) => item.id === routineToday.dataset.routineToday);
            if (!routine) return;
            routine.streak = Number(routine.streak || 0) + 1;
            saveMicroRoutines(routines);
            renderMicroRoutines();
            notify('Streak updated.');
            return;
          }
  
          const routineDelete = event.target.closest('[data-routine-delete]');
          if (routineDelete) {
            saveMicroRoutines(getMicroRoutines().filter((item) => item.id !== routineDelete.dataset.routineDelete));
            renderMicroRoutines();
            notify('Routine removed.');
          }
        });
      }
  
      renderLearningTimeBlocks();
      updateLearningBalanceChart();
      renderMicroRoutines();
    }
  
    function renderReflectionLog() {
      const list = document.getElementById('reflection-log-list');
      if (!list) return;
      const reflections = getWeeklyReflections()
        .slice()
        .sort((left, right) => String(right.weekEnding || '').localeCompare(String(left.weekEnding || '')));
  
      if (!reflections.length) {
        list.innerHTML = '<div class="education-empty-state">Weekly reflections will appear here once you save your first one.</div>';
        return;
      }
  
      list.innerHTML = reflections.map((reflection) => `
        <article class="reflection-log-item">
          <div class="reflection-log-header" data-reflection-toggle="${escapeHtml(reflection.id)}">
            <div class="reflection-log-week">Week ending ${escapeHtml(formatDate(reflection.weekEnding))}</div>
            <div class="education-collapse-indicator">${uiState.reflectionOpenIds.has(reflection.id) ? '−' : '+'}</div>
          </div>
          <div class="reflection-log-body ${uiState.reflectionOpenIds.has(reflection.id) ? 'open' : ''}">
            <div class="reflection-section-label">What I Learned</div>
            <div>${escapeHtml(reflection.whatLearned || '—')}</div>
            <div class="reflection-section-label">What Went Well</div>
            <div>${escapeHtml(reflection.wentWell || '—')}</div>
            <div class="reflection-section-label">What to Improve</div>
            <div>${escapeHtml(reflection.toImprove || '—')}</div>
            <div class="reflection-section-label">Next Week's Focus</div>
            <div>${escapeHtml(reflection.nextWeekFocus || '—')}</div>
          </div>
        </article>
      `).join('');
    }
  
    function renderSkillChecklists() {
      const container = document.getElementById('skill-progress-list');
      if (!container) return;
      const skills = getSkillInventory();
      const checklists = getSkillChecklists();
  
      if (!skills.length) {
        container.innerHTML = '<div class="education-empty-state">Add skills in Direction to unlock checklist tracking here.</div>';
        return;
      }
  
      container.innerHTML = skills.map((skill) => {
        const milestones = Array.isArray(checklists[skill.id]) ? checklists[skill.id] : [];
        const completed = milestones.filter((item) => item.done).length;
        const percent = milestones.length ? Math.round((completed / milestones.length) * 100) : 0;
        return `
          <div class="education-skill-progress-card">
            <div class="education-skill-progress-head">
              <div>
                <div class="learning-skill-name">${escapeHtml(skill.name)}</div>
                <div class="education-support-copy">${completed} of ${milestones.length || 0} milestones complete</div>
              </div>
              <button class="btn-outline btn-mini" type="button" data-skill-checklist-add="${escapeHtml(skill.id)}">Add Milestone to Skill</button>
            </div>
            <div class="progress-track"><div class="progress-fill" style="transform: scaleX(1); width:${percent}%"></div></div>
            <div class="progress-label"><span>${percent}% complete</span><span>${escapeHtml(skill.targetLevel || 'Target TBD')}</span></div>
            <div class="education-checklist-list">
              ${milestones.length ? milestones.map((milestone) => `
                <div class="education-checklist-row">
                  <label class="education-inline-check" for="skill-check-${escapeHtml(milestone.id)}">
                    <input id="skill-check-${escapeHtml(milestone.id)}" type="checkbox" data-skill-check-toggle="${escapeHtml(skill.id)}:${escapeHtml(milestone.id)}" ${milestone.done ? 'checked' : ''}>
                    <span>${escapeHtml(milestone.name)}</span>
                  </label>
                  <button class="btn-outline btn-mini danger" type="button" data-skill-check-delete="${escapeHtml(skill.id)}:${escapeHtml(milestone.id)}">Delete</button>
                </div>
              `).join('') : '<div class="education-empty-state education-empty-state--compact">No milestones yet. Add the first proof point for this skill.</div>'}
            </div>
          </div>
        `;
      }).join('');
    }
  
    function renderResourceAuditTable() {
      const body = document.getElementById('resource-audit-table-body');
      if (!body) return;
      const resources = getResourceAudit().slice().sort((left, right) => String(left.name || '').localeCompare(String(right.name || '')));
      if (!resources.length) {
        body.innerHTML = '<tr><td colspan="7" class="table-empty">No resources added yet.</td></tr>';
        return;
      }
  
      body.innerHTML = resources.map((resource) => {
        const daysSinceReview = resource.lastReviewed ? daysUntil(resource.lastReviewed) : null;
        const dueForReview = resource.lastReviewed ? Math.abs(daysSinceReview) >= 30 && daysSinceReview <= 0 : false;
        const stars = resource.rating ? '★'.repeat(Math.max(0, Math.min(5, Number(resource.rating)))) : '—';
        return `
          <tr>
            <td>
              ${escapeHtml(resource.name)}
              ${dueForReview ? '<span class="resource-due-badge">Due for Review</span>' : ''}
            </td>
            <td>${escapeHtml(statusLabel(resource.resourceType))}</td>
            <td>${escapeHtml(statusLabel(resource.status))}</td>
            <td>${escapeHtml(formatDate(resource.lastReviewed))}</td>
            <td><span class="resource-stars">${escapeHtml(stars)}</span></td>
            <td>${escapeHtml(truncateText(resource.notes, 70))}</td>
            <td class="action-cell">
              <button class="btn-outline btn-mini" type="button" data-resource-edit="${escapeHtml(resource.id)}">Edit</button>
              <button class="btn-outline btn-mini danger" type="button" data-resource-delete="${escapeHtml(resource.id)}">Delete</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  
    function openResourceModal(resource) {
      const set = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.value = value ?? '';
      };
      set('resource-audit-id', resource?.id || '');
      set('resource-name', resource?.name || '');
      set('resource-type', resource?.resourceType || 'book');
      set('resource-status', resource?.status || 'active');
      set('resource-url', resource?.url || '');
      set('resource-rating', resource?.rating || '');
      set('resource-last-reviewed', resource?.lastReviewed || '');
      set('resource-notes', resource?.notes || '');
      const title = document.getElementById('resource-audit-modal-title');
      if (title) title.textContent = resource ? 'Edit Resource' : 'Add Resource';
      if (window.openModal) window.openModal('resource-audit-modal-overlay');
    }
  
    function initOptimizationTab() {
      if (optimizationPanel && !optimizationPanel.dataset.bound) {
        optimizationPanel.dataset.bound = '1';
        document.getElementById('add-resource-btn')?.addEventListener('click', () => openResourceModal(null));
        document.getElementById('resource-audit-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const resources = getResourceAudit();
          const resourceId = document.getElementById('resource-audit-id')?.value || createId('resource');
          const resource = {
            id: resourceId,
            name: document.getElementById('resource-name')?.value?.trim() || '',
            resourceType: document.getElementById('resource-type')?.value || 'book',
            status: document.getElementById('resource-status')?.value || 'active',
            url: document.getElementById('resource-url')?.value?.trim() || '',
            rating: document.getElementById('resource-rating')?.value || '',
            lastReviewed: document.getElementById('resource-last-reviewed')?.value || '',
            notes: document.getElementById('resource-notes')?.value?.trim() || '',
          };
          if (!resource.name) {
            notify('Resource name is required.');
            return;
          }
          const index = resources.findIndex((item) => item.id === resourceId);
          if (index >= 0) resources[index] = resource;
          else resources.unshift(resource);
          saveResourceAudit(resources);
          if (window.closeModal) window.closeModal('resource-audit-modal-overlay');
          renderResourceAuditTable();
          notify(index >= 0 ? 'Resource updated.' : 'Resource added.');
        });
  
        document.getElementById('reflection-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const weekEnding = document.getElementById('reflection-week-ending')?.value || '';
          if (!weekEnding) {
            notify('Week ending is required.');
            return;
          }
          const reflections = getWeeklyReflections();
          reflections.unshift({
            id: createId('reflection'),
            weekEnding,
            whatLearned: document.getElementById('reflection-what-learned')?.value?.trim() || '',
            wentWell: document.getElementById('reflection-went-well')?.value?.trim() || '',
            toImprove: document.getElementById('reflection-to-improve')?.value?.trim() || '',
            nextWeekFocus: document.getElementById('reflection-next-week-focus')?.value?.trim() || '',
          });
          saveWeeklyReflections(reflections);
          event.target.reset();
          renderReflectionLog();
          notify('Reflection saved.');
        });
  
        optimizationPanel.addEventListener('click', (event) => {
          const reflectionToggle = event.target.closest('[data-reflection-toggle]');
          if (reflectionToggle) {
            const reflectionId = reflectionToggle.dataset.reflectionToggle;
            if (uiState.reflectionOpenIds.has(reflectionId)) uiState.reflectionOpenIds.delete(reflectionId);
            else uiState.reflectionOpenIds.add(reflectionId);
            renderReflectionLog();
            return;
          }
  
          const checklistAdd = event.target.closest('[data-skill-checklist-add]');
          if (checklistAdd) {
            const skillId = checklistAdd.dataset.skillChecklistAdd;
            const milestoneName = window.prompt('Add a milestone for this skill:');
            if (!milestoneName || !milestoneName.trim()) return;
            const checklists = getSkillChecklists();
            if (!Array.isArray(checklists[skillId])) checklists[skillId] = [];
            checklists[skillId].push({
              id: createId('skill-check'),
              name: milestoneName.trim(),
              done: false,
            });
            saveSkillChecklists(checklists);
            renderSkillChecklists();
            notify('Skill milestone added.');
            return;
          }
  
          const checklistDelete = event.target.closest('[data-skill-check-delete]');
          if (checklistDelete) {
            const [skillId, milestoneId] = checklistDelete.dataset.skillCheckDelete.split(':');
            const checklists = getSkillChecklists();
            checklists[skillId] = (checklists[skillId] || []).filter((item) => item.id !== milestoneId);
            saveSkillChecklists(checklists);
            renderSkillChecklists();
            notify('Milestone removed.');
            return;
          }
  
          const resourceEdit = event.target.closest('[data-resource-edit]');
          if (resourceEdit) {
            const resource = getResourceAudit().find((item) => item.id === resourceEdit.dataset.resourceEdit);
            openResourceModal(resource || null);
            return;
          }
  
          const resourceDelete = event.target.closest('[data-resource-delete]');
          if (resourceDelete) {
            saveResourceAudit(getResourceAudit().filter((item) => item.id !== resourceDelete.dataset.resourceDelete));
            renderResourceAuditTable();
            notify('Resource deleted.');
          }
        });
  
        optimizationPanel.addEventListener('change', (event) => {
          const toggle = event.target.dataset.skillCheckToggle;
          if (!toggle) return;
          const [skillId, milestoneId] = toggle.split(':');
          const checklists = getSkillChecklists();
          const milestone = (checklists[skillId] || []).find((item) => item.id === milestoneId);
          if (!milestone) return;
          milestone.done = event.target.checked;
          saveSkillChecklists(checklists);
          renderSkillChecklists();
        });
      }
  
      renderReflectionLog();
      renderSkillChecklists();
      renderResourceAuditTable();
    }
  
    function renderCollegeStats() {
      const bar = document.getElementById('college-stats-bar');
      if (!bar) return;
      const applications = getCollegeApplications();
      const submitted = applications.filter((application) => application.status !== 'researching').length;
      const interviewStage = applications.filter((application) => application.status === 'interview').length;
      const accepted = applications.filter((application) => application.status === 'accepted').length;
      bar.innerHTML = [
        { label: 'Total Applications', value: applications.length },
        { label: 'Submitted', value: submitted },
        { label: 'Interview Stage', value: interviewStage },
        { label: 'Accepted', value: accepted },
      ].map((stat) => `
        <div class="college-stat-card">
          <div class="college-stat-label">${escapeHtml(stat.label)}</div>
          <div class="college-stat-value">${escapeHtml(stat.value)}</div>
        </div>
      `).join('');
    }
  
    function renderCollegePipeline() {
      const pipeline = document.getElementById('college-pipeline');
      if (!pipeline) return;
      const applications = getCollegeApplications().map((application) => ({
        ...application,
        requirements: ensureCollegeRequirements(application),
      }));
  
      pipeline.innerHTML = collegeColumns.map((column) => {
        const apps = applications.filter((application) => column.statuses.includes(application.status));
        return `
          <section class="college-pipeline-col" data-college-column="${column.key}">
            <div class="college-pipeline-col-header">
              <div class="college-col-title">${column.label}</div>
              <div class="college-col-count">${apps.length}</div>
            </div>
            ${apps.length ? apps.map((application) => {
              const progress = getRequirementProgress(application);
              const daysLeft = daysUntil(application.deadline);
              const expanded = uiState.expandedCollegeApps.has(application.id);
              return `
                <article class="college-app-card" draggable="true" data-college-app-id="${escapeHtml(application.id)}">
                  <div class="education-college-card-head">
                    <div>
                      <div class="college-app-uni">${countryToFlag(application.country)} ${escapeHtml(application.universityName)}</div>
                      <div class="college-app-program">${escapeHtml(application.program)}</div>
                    </div>
                    <span class="education-status-chip education-status-chip--${collegeStatusClass(application.status)}">${escapeHtml(statusLabel(application.status))}</span>
                  </div>
                  <div class="college-app-meta">
                    <span class="education-flag-pill">${escapeHtml(application.degreeLevel || 'Degree TBD')}</span>
                    <span class="college-deadline-chip ${deadlineClass(daysLeft)}">${application.deadline ? `Due ${escapeHtml(formatDate(application.deadline))}` : 'Deadline TBD'}</span>
                  </div>
                  <div class="education-college-card-meta">
                    <span>${escapeHtml(application.applicationRef || 'No reference')}</span>
                    <span>${application.country ? `${countryToFlag(application.country)} ${escapeHtml(application.country)}` : 'Country TBD'}</span>
                  </div>
                  <button class="btn-outline btn-mini education-college-toggle" type="button" data-college-toggle="${escapeHtml(application.id)}">${expanded ? 'Hide Details' : 'Show Details'}</button>
                  ${expanded ? `
                    <div class="education-college-card-details">
                      <div class="college-req-progress">
                        <div>${progress.completed} of ${progress.total} requirements completed.</div>
                        <div class="college-req-bar-wrap"><div class="college-req-bar" style="width:${progress.percent}%"></div></div>
                      </div>
                      <div class="education-college-req-list">
                        ${application.requirements.map((requirement) => `
                          <div class="education-college-req-item">
                            <label class="education-inline-check" for="college-req-${escapeHtml(requirement.id)}">
                              <input id="college-req-${escapeHtml(requirement.id)}" type="checkbox" data-college-req-toggle="${escapeHtml(application.id)}:${escapeHtml(requirement.id)}" ${requirement.completed ? 'checked' : ''}>
                              <span>${escapeHtml(requirement.name)}</span>
                            </label>
                            <div class="form-field">
                              <label for="college-req-doc-${escapeHtml(requirement.id)}">Linked Vault Doc</label>
                              <select id="college-req-doc-${escapeHtml(requirement.id)}" data-college-req-doc="${escapeHtml(application.id)}:${escapeHtml(requirement.id)}">
                                ${buildRequirementDocumentOptions(requirement.linkedDocumentId)}
                              </select>
                            </div>
                          </div>
                        `).join('')}
                      </div>
                      <div class="education-college-card-meta education-college-card-meta--stack">
                        <span>Personal Statement: ${escapeHtml(statusLabel(application.personalStatementStatus))}</span>
                        <span>Recommendations: ${escapeHtml(application.recLettersCollected || 0)} of ${escapeHtml(application.recLettersRequired || 0)}</span>
                        <span>Scholarship: ${escapeHtml(application.scholarshipLinked || 'None')}</span>
                        <span>Rank: ${escapeHtml(application.qsRank || '—')}</span>
                      </div>
                      ${application.notes ? `<div class="education-support-copy">${escapeHtml(application.notes)}</div>` : ''}
                      <div class="education-card-actions">
                        <button class="btn-outline btn-mini" type="button" data-college-edit="${escapeHtml(application.id)}">Edit</button>
                        <button class="btn-outline btn-mini danger" type="button" data-college-delete="${escapeHtml(application.id)}">Delete</button>
                      </div>
                    </div>
                  ` : ''}
                </article>
              `;
            }).join('') : '<div class="education-empty-state education-empty-state--compact">No applications in this stage yet.</div>'}
          </section>
        `;
      }).join('');
    }
  
    function renderCollegeDeadlines() {
      const strip = document.getElementById('college-deadline-strip');
      if (!strip) return;
      const upcoming = getCollegeApplications()
        .filter((application) => {
          const daysLeft = daysUntil(application.deadline);
          return daysLeft !== null && daysLeft >= 0 && daysLeft <= 90;
        })
        .sort((left, right) => String(left.deadline || '').localeCompare(String(right.deadline || '')));
  
      if (!upcoming.length) {
        strip.innerHTML = '<div class="education-empty-state">No application deadlines in the next 90 days.</div>';
        return;
      }
  
      strip.innerHTML = upcoming.map((application) => {
        const daysLeft = daysUntil(application.deadline);
        const chipClass = deadlineClass(daysLeft);
        return `
          <div class="deadline-chip-card ${chipClass}">
            <div class="deadline-uni-code">${escapeHtml(universityCode(application.universityName))}</div>
            <div class="deadline-days-left">${escapeHtml(daysLeft)}</div>
            <div class="deadline-days-label">${daysLeft === 1 ? 'day left' : 'days left'}</div>
          </div>
        `;
      }).join('');
    }
  
    function renderCollegeEssays() {
      const body = document.getElementById('college-essays-table-body');
      if (!body) return;
      const applications = getCollegeApplications();
      const appMap = applications.reduce((accumulator, application) => {
        accumulator[application.id] = application;
        return accumulator;
      }, {});
      const essays = getCollegeEssays().slice().sort((left, right) => String(right.lastEdited || '').localeCompare(String(left.lastEdited || '')));
      if (!essays.length) {
        body.innerHTML = '<tr><td colspan="6" class="table-empty">No essays tracked yet.</td></tr>';
        return;
      }
  
      body.innerHTML = essays.map((essay) => {
        const application = appMap[essay.applicationId];
        return `
          <tr>
            <td>${escapeHtml(application?.universityName || essay.universityName || 'Unknown')}</td>
            <td>${escapeHtml(truncateText(essay.prompt, 90))}</td>
            <td>${escapeHtml(essay.wordLimit ? `${wordCount(essay.draftContent)} / ${essay.wordLimit}` : wordCount(essay.draftContent))}</td>
            <td>${escapeHtml(statusLabel(essay.status))}</td>
            <td>${escapeHtml(formatDate(essay.lastEdited))}</td>
            <td class="action-cell">
              <button class="btn-outline btn-mini" type="button" data-college-essay-edit="${escapeHtml(essay.id)}">Edit</button>
              <button class="btn-outline btn-mini danger" type="button" data-college-essay-delete="${escapeHtml(essay.id)}">Delete</button>
            </td>
          </tr>
        `;
      }).join('');
    }
  
    function renderCollegeTabViews() {
      renderCollegeStats();
      renderCollegePipeline();
      renderCollegeDeadlines();
      renderCollegeEssays();
    }
  
    function openCollegeAppModal(application) {
      populateScholarshipDatalist();
      const set = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.value = value ?? '';
      };
      set('college-app-id', application?.id || '');
      set('college-university-name', application?.universityName || '');
      set('college-program', application?.program || '');
      set('college-degree-level', application?.degreeLevel || 'bachelor');
      set('college-country', application?.country || '');
      set('college-deadline', application?.deadline || '');
      set('college-start-date', application?.startDate || '');
      set('college-application-status', application?.status || 'researching');
      set('college-portal-url', application?.portalUrl || '');
      set('college-application-ref', application?.applicationRef || '');
      set('college-tuition-fee', application?.tuitionFee || '');
      set('college-scholarship-linked', application?.scholarshipLinked || '');
      set('college-acceptance-rate', application?.acceptanceRate || '');
      set('college-qs-rank', application?.qsRank || '');
      set('college-personal-statement-status', application?.personalStatementStatus || 'not_started');
      set('college-rec-letters-required', application?.recLettersRequired || 0);
      set('college-rec-letters-collected', application?.recLettersCollected || 0);
      set('college-notes', application?.notes || '');
      const title = document.getElementById('college-app-modal-title');
      if (title) title.textContent = application ? 'Edit College Application' : 'Add College Application';
      if (window.openModal) window.openModal('college-app-modal-overlay');
    }
  
    function openCollegeEssayModal(essay) {
      populateCollegeEssayOptions(essay?.applicationId || '');
      const applications = getCollegeApplications();
      if (!applications.length && !essay) {
        notify('Add a college application before adding essays.');
        return;
      }
      const set = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.value = value ?? '';
      };
      set('college-essay-id', essay?.id || '');
      set('college-essay-status', essay?.status || 'not_started');
      set('college-essay-prompt', essay?.prompt || '');
      set('college-essay-word-limit', essay?.wordLimit || '');
      set('college-essay-draft-content', essay?.draftContent || '');
      const title = document.getElementById('college-essay-modal-title');
      if (title) title.textContent = essay ? 'Edit Essay' : 'Add Essay';
      if (window.openModal) window.openModal('college-essay-modal-overlay');
    }
  
    function initCollegeTab() {
      if (collegePanel && !collegePanel.dataset.bound) {
        collegePanel.dataset.bound = '1';
  
        document.getElementById('add-college-app-btn')?.addEventListener('click', () => openCollegeAppModal(null));
        document.getElementById('add-college-essay-btn')?.addEventListener('click', () => openCollegeEssayModal(null));
  
        document.getElementById('college-app-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const applications = getCollegeApplications();
          const applicationId = document.getElementById('college-app-id')?.value || createId('college-app');
          const existing = applications.find((item) => item.id === applicationId);
          const application = {
            id: applicationId,
            universityName: document.getElementById('college-university-name')?.value?.trim() || '',
            program: document.getElementById('college-program')?.value?.trim() || '',
            degreeLevel: document.getElementById('college-degree-level')?.value || 'bachelor',
            country: document.getElementById('college-country')?.value?.trim() || '',
            deadline: document.getElementById('college-deadline')?.value || '',
            startDate: document.getElementById('college-start-date')?.value || '',
            status: document.getElementById('college-application-status')?.value || 'researching',
            portalUrl: document.getElementById('college-portal-url')?.value?.trim() || '',
            applicationRef: document.getElementById('college-application-ref')?.value?.trim() || '',
            tuitionFee: document.getElementById('college-tuition-fee')?.value || '',
            scholarshipLinked: document.getElementById('college-scholarship-linked')?.value?.trim() || '',
            acceptanceRate: document.getElementById('college-acceptance-rate')?.value || '',
            qsRank: document.getElementById('college-qs-rank')?.value || '',
            personalStatementStatus: document.getElementById('college-personal-statement-status')?.value || 'not_started',
            recLettersRequired: document.getElementById('college-rec-letters-required')?.value || 0,
            recLettersCollected: document.getElementById('college-rec-letters-collected')?.value || 0,
            notes: document.getElementById('college-notes')?.value?.trim() || '',
            requirements: ensureCollegeRequirements(existing || {}),
          };
          if (!application.universityName || !application.program) {
            notify('University name and program are required.');
            return;
          }
          const index = applications.findIndex((item) => item.id === applicationId);
          if (index >= 0) applications[index] = application;
          else applications.unshift(application);
          saveCollegeApplications(applications);
          if (window.closeModal) window.closeModal('college-app-modal-overlay');
          renderCollegeTabViews();
          populateCollegeEssayOptions('');
          notify(index >= 0 ? 'Application updated.' : 'Application added.');
        });
  
        document.getElementById('college-essay-form')?.addEventListener('submit', (event) => {
          event.preventDefault();
          const applicationId = document.getElementById('college-essay-application-id')?.value || '';
          if (!applicationId) {
            notify('Select a university first.');
            return;
          }
          const applications = getCollegeApplications();
          const application = applications.find((item) => item.id === applicationId);
          if (!application) {
            notify('Selected application could not be found.');
            return;
          }
          const essays = getCollegeEssays();
          const essayId = document.getElementById('college-essay-id')?.value || createId('essay');
          const essay = {
            id: essayId,
            applicationId,
            universityName: application.universityName,
            prompt: document.getElementById('college-essay-prompt')?.value?.trim() || '',
            wordLimit: document.getElementById('college-essay-word-limit')?.value || '',
            status: document.getElementById('college-essay-status')?.value || 'not_started',
            draftContent: document.getElementById('college-essay-draft-content')?.value || '',
            lastEdited: todayISO(),
          };
          if (!essay.prompt) {
            notify('Essay prompt is required.');
            return;
          }
          const index = essays.findIndex((item) => item.id === essayId);
          if (index >= 0) essays[index] = essay;
          else essays.unshift(essay);
          saveCollegeEssays(essays);
          if (window.closeModal) window.closeModal('college-essay-modal-overlay');
          renderCollegeEssays();
          notify(index >= 0 ? 'Essay updated.' : 'Essay added.');
        });
  
        collegePanel.addEventListener('click', (event) => {
          const toggle = event.target.closest('[data-college-toggle]');
          if (toggle) {
            const applicationId = toggle.dataset.collegeToggle;
            if (uiState.expandedCollegeApps.has(applicationId)) uiState.expandedCollegeApps.delete(applicationId);
            else uiState.expandedCollegeApps.add(applicationId);
            renderCollegePipeline();
            return;
          }
  
          const edit = event.target.closest('[data-college-edit]');
          if (edit) {
            const application = getCollegeApplications().find((item) => item.id === edit.dataset.collegeEdit);
            openCollegeAppModal(application || null);
            return;
          }
  
          const remove = event.target.closest('[data-college-delete]');
          if (remove) {
            const applications = getCollegeApplications().filter((item) => item.id !== remove.dataset.collegeDelete);
            const essays = getCollegeEssays().filter((item) => item.applicationId !== remove.dataset.collegeDelete);
            saveCollegeApplications(applications);
            saveCollegeEssays(essays);
            uiState.expandedCollegeApps.delete(remove.dataset.collegeDelete);
            renderCollegeTabViews();
            notify('Application deleted.');
            return;
          }
  
          const editEssay = event.target.closest('[data-college-essay-edit]');
          if (editEssay) {
            const essay = getCollegeEssays().find((item) => item.id === editEssay.dataset.collegeEssayEdit);
            openCollegeEssayModal(essay || null);
            return;
          }
  
          const deleteEssay = event.target.closest('[data-college-essay-delete]');
          if (deleteEssay) {
            saveCollegeEssays(getCollegeEssays().filter((item) => item.id !== deleteEssay.dataset.collegeEssayDelete));
            renderCollegeEssays();
            notify('Essay deleted.');
          }
        });
  
        collegePanel.addEventListener('change', (event) => {
          const toggle = event.target.dataset.collegeReqToggle;
          if (toggle) {
            const [applicationId, requirementId] = toggle.split(':');
            const applications = getCollegeApplications();
            const application = applications.find((item) => item.id === applicationId);
            if (!application) return;
            application.requirements = ensureCollegeRequirements(application).map((requirement) => {
              if (requirement.id !== requirementId) return requirement;
              return { ...requirement, completed: event.target.checked };
            });
            saveCollegeApplications(applications);
            renderCollegePipeline();
            return;
          }
  
          const docSelect = event.target.dataset.collegeReqDoc;
          if (!docSelect) return;
          const [applicationId, requirementId] = docSelect.split(':');
          const documents = getEducationDocuments();
          const selectedDocument = documents.find((document) => String(document.id) === String(event.target.value));
          const applications = getCollegeApplications();
          const application = applications.find((item) => item.id === applicationId);
          if (!application) return;
          application.requirements = ensureCollegeRequirements(application).map((requirement) => {
            if (requirement.id !== requirementId) return requirement;
            return {
              ...requirement,
              linkedDocumentId: event.target.value || '',
              linkedDocumentTitle: selectedDocument?.title || '',
            };
          });
          saveCollegeApplications(applications);
          renderCollegePipeline();
        });
  
        const pipeline = document.getElementById('college-pipeline');
        if (pipeline) {
          pipeline.addEventListener('dragstart', (event) => {
            const card = event.target.closest('[data-college-app-id]');
            if (!card) return;
            uiState.collegeDragAppId = card.dataset.collegeAppId;
            event.dataTransfer?.setData('text/plain', card.dataset.collegeAppId);
          });
          pipeline.addEventListener('dragover', (event) => {
            const column = event.target.closest('[data-college-column]');
            if (!column) return;
            event.preventDefault();
            column.classList.add('education-drop-active');
          });
          pipeline.addEventListener('dragleave', (event) => {
            const column = event.target.closest('[data-college-column]');
            if (!column) return;
            column.classList.remove('education-drop-active');
          });
          pipeline.addEventListener('drop', (event) => {
            const column = event.target.closest('[data-college-column]');
            if (!column) return;
            event.preventDefault();
            column.classList.remove('education-drop-active');
            const applicationId = uiState.collegeDragAppId || event.dataTransfer?.getData('text/plain');
            if (!applicationId) return;
            const applications = getCollegeApplications();
            const application = applications.find((item) => item.id === applicationId);
            if (!application) return;
            application.status = mapColumnToStatus(column.dataset.collegeColumn, application.status);
            saveCollegeApplications(applications);
            renderCollegeStats();
            renderCollegePipeline();
            notify('Application stage updated.');
            uiState.collegeDragAppId = '';
          });
        }
      }
  
      populateScholarshipDatalist();
      populateCollegeEssayOptions('');
      renderCollegeTabViews();
    }
  
    function maybeInitializeEducationTab(tabId) {
      const initializers = {
        direction: initDirectionTab,
        knowledge: initKnowledgeTab,
        action: initActionTab,
        optimization: initOptimizationTab,
        college: initCollegeTab,
      };
  
      if (!initializers[tabId]) return;
      if (!initializedEduTabs.has(tabId)) {
        initializers[tabId]();
        initializedEduTabs.add(tabId);
        return;
      }
  
      if (tabId === 'direction') {
        renderSkillInventory();
        renderRoadmap();
      } else if (tabId === 'knowledge') {
        renderCaptureInbox();
        renderParaKnowledgeBase();
        renderFeynmanLog();
      } else if (tabId === 'action') {
        renderLearningTimeBlocks();
        updateLearningBalanceChart();
        renderMicroRoutines();
      } else if (tabId === 'optimization') {
        renderReflectionLog();
        renderSkillChecklists();
        renderResourceAuditTable();
      } else if (tabId === 'college') {
        renderCollegeTabViews();
      }
    }
  
    const originalSwitchTab = window.switchTab;
    if (typeof originalSwitchTab === 'function') {
      window.switchTab = function wrappedSwitchTab(prefix, id) {
        originalSwitchTab(prefix, id);
        if (prefix === 'edu') maybeInitializeEducationTab(id);
      };
    }
}

function init() {
  updateClock();
  setInterval(updateClock, 1000);
  applyChartThemeDefaults();
  setupOtpUX();
  mountUIHelpers();
  initAccountSettingsUI();
  wrapTablesForMobile();
  updateCommonAppProgress();
  setFinanceRefreshIndicator(hasFinanceNeedsRefresh());
  setupMobileSidebar();
  setupCommandPalette();
  setupCommandPaletteOverlay();
  setupCommandPaletteHint();
  initGlobalSearch();
  initKeyboardShortcuts();
  setupNotifications();
  setupQuickAdd();
  setupShortcutHints();
  setupIdleDetection();
  setupScrollSpy();
  initScrollTopbar();
  setupHtmxNavigation();
  setBodyScrollState();
  window.addEventListener('scroll', setBodyScrollState, { passive: true });
  applyTheme(getCurrentTheme());
  initCardTilt();
  initMagneticButtons();
  initTabIndicators();
  initProgressBarAnimations();
  setupButtonRipples();

  if (isAuthenticated()) {
    openApp();
    reinitializeActivePage(document, { resetState: false, loadData: true });
  } else {
    closeApp();
    reinitializeActivePage(document, { resetState: false, loadData: false });
  }
}

document.addEventListener('DOMContentLoaded', init);

window.switchAuth = switchAuth;
window.handleSignup = handleSignup;
window.otpNext = otpNext;
window.otpVerify = otpVerify;
window.handleLogin = handleLogin;
window.signOut = signOut;
window.showPage = showPage;
window.goPersonalStep = goPersonalStep;
window.switchTab = switchTab;
window.toggleTask = toggleTask;
window.toggleCheck = toggleCheck;
window.selectMood = selectMood;
window.newDiaryEntry = newDiaryEntry;
window.filterBucket = filterBucket;
window.openAddGoalModal = openAddGoalModal;
window.updateCategoryCounts = updateCategoryCounts;
window.animateProgressBars = animateProgressBars;
window.showToast = showToast;
window.saveDiaryEntry = saveDiaryEntry;
window.saveProfileSettings = saveProfileSettings;
window.saveNotificationSettings = saveNotificationSettings;
window.prevDashboardMonth = prevDashboardMonth;
window.nextDashboardMonth = nextDashboardMonth;
window.openNotifications = openNotifications;
window.closeNotifications = closeNotifications;
window.toggleQuickAdd = toggleQuickAdd;
window.openQuickForm = openQuickForm;
window.openCommandPalette = openCommandPalette;
window.closeCommandPalette = closeCommandPalette;
window.filterCommands = filterCommands;
window.openModal = openModal;
window.closeModal = closeModal;
window.navigateInApp = navigateInApp;
window.toggleTheme = toggleTheme;
window.runCounterAnimations = runCounterAnimations;
window.initObserverAnimations = initObserverAnimations;
window.initCardTilt = initCardTilt;
window.initRipples = initRipples;
window.initScrollAnimations = initScrollAnimations;
window.initScrollTopbar = initScrollTopbar;
window.initTabIndicators = initTabIndicators;
window.initProgressBarAnimations = initProgressBarAnimations;
window.initMagneticButtons = initMagneticButtons;
window.showSkeletonFor = showSkeletonFor;
window.clearSkeleton = clearSkeleton;
window.getChartBaseConfig = getChartBaseConfig;
window.chartGradient = chartGradient;
