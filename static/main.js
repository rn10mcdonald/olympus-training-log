/* ──────────────────────────────────────────────────────────────────────────
   Olympus Training Log – main.js  v7
   ────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────────
const TRIP_MILES      = 306;
const SESSIONS_NEEDED = 6;
const WEEK_TARGET     = 3;

// ── Auth ──────────────────────────────────────────────────────────────────────
const AUTH_KEY = "olympus_token";
const AUTH_USER_KEY = "olympus_username";

function getToken() { return localStorage.getItem(AUTH_KEY); }
function getUsername() { return localStorage.getItem(AUTH_USER_KEY); }

function setAuth(token, username) {
  localStorage.setItem(AUTH_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, username);
}

function clearAuth() {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function showAuthOverlay() {
  document.getElementById("auth-overlay").hidden = false;
}

function hideAuthOverlay() {
  document.getElementById("auth-overlay").hidden = true;
}

// ── API helper ────────────────────────────────────────────────────────────────
async function api(url, data, method) {
  const m = method || (data !== undefined ? "POST" : "GET");
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  const opts = m !== "GET"
    ? { method: m, headers, body: data !== undefined ? JSON.stringify(data) : undefined }
    : { headers };
  const r = await fetch(url, opts);
  if (r.status === 401) {
    clearAuth();
    showAuthOverlay();
    throw new Error("Session expired — please sign in again");
  }
  if (!r.ok) {
    const text = await r.text();
    let msg = text;
    try { msg = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(msg || r.statusText);
  }
  return r.json();
}

// ── Toast queue ───────────────────────────────────────────────────────────────
const toastEl = document.getElementById("toast");
const _toastQueue = [];
let _toastActive = false;

function toast(msg, ms = 3500, type = "default") {
  _toastQueue.push({ msg, ms, type });
  if (!_toastActive) _drainToastQueue();
}

function _drainToastQueue() {
  if (!_toastQueue.length) { _toastActive = false; return; }
  _toastActive = true;
  const { msg, ms, type } = _toastQueue.shift();
  toastEl.textContent = msg;
  toastEl.className = "toast show" + (type !== "default" ? " toast-" + type : "");
  setTimeout(() => {
    toastEl.classList.remove("show");
    setTimeout(_drainToastQueue, 350);
  }, ms);
}

// ── Utility ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function encodeURIPath(path) {
  return String(path).split("/").map(encodeURIComponent).join("/");
}

function isoWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return [d.getUTCFullYear(), Math.ceil((((d - yearStart) / 86_400_000) + 1) / 7)];
}

// Pace helpers: "8:30" <-> 8.5 decimal minutes
function parsePace(str) {
  if (!str || !str.trim()) return null;
  const m = str.trim().match(/^(\d+):([0-5]\d)$/);
  if (!m) return null;
  return parseInt(m[1], 10) + parseInt(m[2], 10) / 60;
}

function formatPace(decMin) {
  if (decMin == null) return "";
  const min = Math.floor(decMin);
  const sec = Math.round((decMin - min) * 60);
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

// ── Drachma helpers ───────────────────────────────────────────────────────────
const BASE_WORKOUT_COINS   = 5.0;
const CUSTOM_WORKOUT_COINS = 3.0;

/** Convert lbs → kg and compute estimated workout Drachma, mirroring core.py logic. */
function estimateWorkoutCoins(lbs, stdKg) {
  // Preview for main lift only; full session will earn ~4× this
  // Formula: volume_lbs × 0.035, assuming a 5×5 set
  const weightLbs = (lbs > 0 ? lbs : (stdKg || 16) * 2.20462);
  const volume = weightLbs * 5 * 5;  // 5×5 representative set
  return Math.round(volume * 0.035 * 100) / 100;
}

// ── App state ─────────────────────────────────────────────────────────────────
let appState        = null;
let prevBadgeCount  = 0;
let historyFilter   = "all";
let previewedKey    = null;   // track key currently shown in preview dialog
let currentStdKg    = 16;     // std_kg of the currently displayed session

// ── Section navigation ────────────────────────────────────────────────────────
function switchSection(name) {
  document.querySelectorAll(".page-section").forEach(s =>
    s.classList.toggle("active", s.id === `section-${name}`));
  document.querySelectorAll(".nav-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.section === name));
}

// ── Full refresh ──────────────────────────────────────────────────────────────
async function refresh() {
  try {
    const [state, workout] = await Promise.all([
      api("/api/state"),
      api("/api/workout/today"),
    ]);
    appState = state;
    renderAll(state, workout);
    await populateTracks(state);
    prevBadgeCount = (state.badges || []).length;
  } catch (e) {
    toast("⚠ Error loading state: " + e.message);
  }
}

// ── Render all sections ───────────────────────────────────────────────────────
function renderAll(state, workout) {
  renderHeader(state);
  renderTrainSection(state, workout);
  renderCardioSection(state);
  renderVaultSection(state);
}

// ── Header ────────────────────────────────────────────────────────────────────
function renderHeader(state) {
  // Issue 3: prefer estate drachmae (source of truth) over legacy treasury
  const drachBanner = document.getElementById("drachma");
  if (drachBanner && !estateState) {
    drachBanner.textContent = (state.treasury || 0).toFixed(2);
  }
  // If estateState is loaded, renderEstateResources() handles #drachma instead

  const today = new Date();
  const [yr, wk] = isoWeek(today);
  const weekKey = `(${yr}, ${wk})`;
  const wkCount = Math.min((state.week_log || {})[weekKey] || 0, WEEK_TARGET);
  document.getElementById("week-count").textContent = `${wkCount}/${WEEK_TARGET}`;
}

// ── Train section ─────────────────────────────────────────────────────────────
function renderTrainSection(state, workout) {
  renderProgramTrack(state, workout);
  renderWorkout(workout);
}

// ── Program Track card ────────────────────────────────────────────────────────
function renderProgramTrack(state, workout) {
  const mc   = state.microcycle || {};
  const n    = (workout && workout.total_sessions) ? workout.total_sessions : SESSIONS_NEEDED;
  const done = Math.min(mc.sessions_completed || 0, n);

  const noState     = document.getElementById("no-program-state");
  const activeState = document.getElementById("active-program-state");
  const fractionEl  = document.getElementById("program-fraction");
  const nameEl      = document.getElementById("program-name-display");
  const nodesEl     = document.getElementById("session-nodes");
  const countdownEl = document.getElementById("program-countdown");

  if (!mc.start_date || !state.track) {
    if (noState)     noState.hidden     = false;
    if (activeState) activeState.hidden = true;
    if (fractionEl)  fractionEl.hidden  = true;
    return;
  }

  if (noState)     noState.hidden     = true;
  if (activeState) activeState.hidden = false;
  if (fractionEl) {
    fractionEl.hidden      = false;
    fractionEl.textContent = `${done} / ${n}`;
  }

  // Program name: prefer workout track_name, fall back to track key
  const trackName = (workout && workout.track_name) || state.track || "Active Program";
  if (nameEl) nameEl.textContent = trackName;

  // Replace progress bar with session nodes ● ● ○ ○ ○ ○
  const nodesHtml = Array.from({length: n}, (_, i) =>
    `<span class="session-node ${i < done ? "session-node-done" : "session-node-empty"}">${i < done ? "●" : "○"}</span>`
  ).join("");
  if (nodesEl) {
    nodesEl.innerHTML = `<div class="session-nodes-row">${nodesHtml}</div>`;
  }

  const remaining = Math.max(n - done, 0);
  if (countdownEl) {
    countdownEl.textContent = remaining > 0
      ? `${done} / ${n} sessions completed`
      : "🏅 Cycle complete — slay your monster!";
  }
}

/** Compact weight input HTML for a given movement key. */
function weightInputHtml(key) {
  return `<input type="number" class="movement-weight-input"
                 data-key="${key}" placeholder="lbs"
                 step="1" min="0" max="999" inputmode="decimal">`;
}

function renderWorkout(w) {
  const el        = document.getElementById("workout-display");
  const actionsEl = document.getElementById("workout-actions");

  if (!w || w.status === "no_track") {
    el.innerHTML = `<p class="dim-msg" style="margin-bottom:0">Choose a program above to see today's session.</p>`;
    if (actionsEl) actionsEl.style.display = "none";
    return;
  }
  if (w.status === "cycle_complete") {
    el.innerHTML = `<p class="dim-msg" style="margin-bottom:0">🏅 Cycle complete! Choose a new program to continue.</p>`;
    if (actionsEl) actionsEl.style.display = "none";
    return;
  }

  if (actionsEl) actionsEl.style.display = "";
  currentStdKg = w.std_kg || 16;
  const stdLbs = Math.round(currentStdKg * 2.20462);

  const accessoryRows = (w.accessory || []).map((a, i) => `
    <div class="workout-exercise-row">
      <span class="workout-exercise-name">${escHtml(a)}</span>
      ${weightInputHtml(`acc_${i}`)}
    </div>`).join("");

  el.innerHTML = `
    <div class="workout-card-header">
      <span class="workout-track-name">${escHtml(w.track_name || "Program")}</span>
      <span class="workout-session-chip">Session ${w.session_num} / ${w.total_sessions}</span>
    </div>

    <div class="workout-section">
      <div class="workout-section-header">Main Lift</div>
      <div class="workout-exercise-row workout-main-lift">
        <span class="workout-exercise-name">${escHtml(w.main)}</span>
        ${weightInputHtml("main")}
      </div>
    </div>

    ${accessoryRows ? `
    <div class="workout-section">
      <div class="workout-section-header">Accessories</div>
      ${accessoryRows}
    </div>` : ""}

    ${w.finisher ? `
    <div class="workout-section">
      <div class="workout-section-header">Finisher</div>
      <div class="workout-exercise-row">
        <span class="workout-exercise-name">${escHtml(w.finisher)}</span>
        ${weightInputHtml("finisher")}
      </div>
    </div>` : ""}

    <p class="weight-std-hint">Standard bell: ${stdLbs} lbs (${currentStdKg} kg)</p>`;
}

/** Live Drachma preview — driven by the main-lift weight input. */
function updateCoinPreview() {
  const preview = document.getElementById("weight-coins-preview");
  if (!preview) return;
  const mainInput = document.querySelector(
    "#workout-display .movement-weight-input[data-key='main']");
  const lbs = mainInput ? parseFloat(mainInput.value || 0) : 0;
  preview.textContent = `🪙 ${estimateWorkoutCoins(lbs, currentStdKg).toFixed(2)}`;
}

async function populateTracks(state) {
  try {
    const tracks = await api("/api/tracks");
    const sel    = document.getElementById("track-select");
    const curVal = sel.value;
    sel.innerHTML = "";
    for (const [key, name] of Object.entries(tracks)) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = name;
      sel.appendChild(opt);
    }
    // Restore selection — prefer current state track, fall back to previous selection
    if (state && state.track && tracks[state.track] !== undefined) {
      sel.value = state.track;
    } else if (curVal && tracks[curVal] !== undefined) {
      sel.value = curVal;
    }
    updateDeleteTrackBtn();
  } catch (_) {}
}

/** Show/hide the 🗑 delete button based on whether a custom track is selected. */
function updateDeleteTrackBtn() {
  const sel = document.getElementById("track-select");
  const btn = document.getElementById("delete-track-btn");
  if (btn) btn.style.display = sel.value.startsWith("custom_") ? "" : "none";
}

// ── Cardio section ────────────────────────────────────────────────────────────
function renderCardioSection(state) {
  const ruckMiles = state.total_ruck_miles  || 0;
  const runMiles  = state.total_run_miles   || 0;
  const walkMiles = state.total_walk_miles  || 0;
  const journey   = state.journey_miles     || 0;

  const totalRuckEl = document.getElementById("total-ruck-miles");
  const totalRunEl  = document.getElementById("total-run-miles");
  const totalWalkEl = document.getElementById("total-walk-miles");
  if (totalRuckEl) totalRuckEl.textContent = ruckMiles.toFixed(1) + " mi";
  if (totalRunEl)  totalRunEl.textContent  = runMiles.toFixed(1)  + " mi";
  if (totalWalkEl) totalWalkEl.textContent = walkMiles.toFixed(1) + " mi";

  const pct = Math.min((journey / TRIP_MILES) * 100, 100);
  const journeyBar = document.getElementById("journey-bar");
  const journeyFrac = document.getElementById("journey-fraction");
  if (journeyBar)  journeyBar.style.width = pct.toFixed(1) + "%";
  if (journeyFrac) journeyFrac.textContent = `${journey.toFixed(1)} / ${TRIP_MILES} mi`;

  const postcards = (state.badges || []).filter(b => b.type === "ruck_quest").reverse();
  const postcardsEl = document.getElementById("ruck-postcards");
  if (postcardsEl) postcardsEl.innerHTML =
    postcards.length
      ? postcards.map(b => postcardHtml(b)).join("")
      : `<p class="dim-msg">Log cardio miles to unlock journey waypoints.</p>`;
}

// ── Cardio type toggle ────────────────────────────────────────────────────────
let activeCardioType = "running";

function initCardioTypeRow() {
  const row = document.getElementById("cardio-type-row");
  if (!row) return;
  row.addEventListener("click", e => {
    const btn = e.target.closest(".cardio-type-btn");
    if (!btn) return;
    row.querySelectorAll(".cardio-type-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeCardioType = btn.dataset.type;
    // Show/hide weight field for ruck/hike
    const needsWeight = (activeCardioType === "rucking" || activeCardioType === "hiking");
    const wg = document.getElementById("cardio-weight-group");
    if (wg) wg.style.display = needsWeight ? "" : "none";
  });
}

function postcardHtml(b) {
  const imgEl = b.image_path
    ? `<img src="/img/${encodeURIPath(b.image_path)}" alt="${escHtml(b.stop || b.name)}"
           onerror="this.replaceWith(Object.assign(document.createElement('div'),
             {className:'postcard-placeholder',textContent:'📜'}))">`
    : `<div class="postcard-placeholder">📜</div>`;
  return `
    <div class="postcard">
      ${imgEl}
      <div>
        <div class="postcard-city">${escHtml(b.stop || b.name)}</div>
        ${b.caption ? `<div class="postcard-caption">${escHtml(b.caption)}</div>` : ""}
        <div class="postcard-date">${b.date || ""}</div>
      </div>
    </div>`;
}

// (renderRunSection / renderWalkSection replaced by renderCardioSection + loadHistory)

// ── Vault section ─────────────────────────────────────────────────────────────
function renderVaultSection(state) {
  const badges    = state.badges || [];
  const laurels   = [...badges].filter(b => b.type === "laurel").reverse();
  const postcards = [...badges].filter(b => b.type === "ruck_quest").reverse();

  // Monster trophies: load from estate trophy system (has buff data)
  api("/api/estate/trophies").then(data => {
    const trophies = (data.trophies || []).slice().reverse();
    document.getElementById("trophies-list").innerHTML = trophies.length
      ? trophies.map(t => trophyCardHtml(t)).join("")
      : `<div class="empty-msg">Complete a 6-session cycle to earn your first trophy.</div>`;
    renderTrophyBuffsSummary(data.buff_summary || []);
  }).catch(() => {
    // Fallback: legacy badges if estate API unavailable
    const legacyTrophies = [...badges].filter(b => b.type === "monster").reverse();
    document.getElementById("trophies-list").innerHTML = legacyTrophies.length
      ? legacyTrophies.map(b => badgeCardHtml(b)).join("")
      : `<div class="empty-msg">Complete a 6-session cycle to earn your first trophy.</div>`;
  });

  document.getElementById("laurels-list").innerHTML = laurels.length
    ? laurels.map(b => badgeCardHtml(b)).join("")
    : `<div class="empty-msg">Log 3 activities in a week to earn a Laurel.</div>`;

  document.getElementById("vault-postcards").innerHTML = postcards.length
    ? postcards.map(b => postcardHtml(b)).join("")
    : `<div class="empty-msg">Unlock waypoints by covering journey miles.</div>`;
}

// Render the stacked trophy buff summary chips above the grid
function renderTrophyBuffsSummary(buffSummary) {
  const el = document.getElementById("trophy-buffs-summary");
  if (!el) return;
  if (!buffSummary || buffSummary.length === 0) {
    el.innerHTML = "";
    return;
  }
  const BUFF_ICONS = {
    drachmae_gain:     "🪙",
    strength_rewards:  "💪",
    farm_production:   "🌾",
    creature_chance:   "🦅",
    campaign_strength: "⚔️",
    relic_chance:      "⚗️",
  };
  el.innerHTML = buffSummary.map(b => {
    const icon = BUFF_ICONS[b.buff_type] || "✨";
    return `<span class="trophy-buff-chip">
      <span class="trophy-buff-chip-icon">${icon}</span>
      ${escHtml(b.label)}
    </span>`;
  }).join("");
}

// Trophy card with buff label and rarity indicator
function trophyCardHtml(t) {
  const rarityColour = t.rarity_colour || "#a0a0a0";
  const buffLabel    = t.buff_label    || "";
  const emoji        = t.emoji         || "🏆";
  const date         = t.date_earned   || "";
  const rarity       = t.rarity_label  || (t.rarity || "").replace(/^./, c => c.toUpperCase());
  return `
    <div class="badge-card">
      <div class="badge-emoji">${emoji}</div>
      <div class="badge-name">${escHtml(t.name || "")}</div>
      <div class="trophy-buff-label">${escHtml(buffLabel)}</div>
      <div class="badge-date" style="display:flex;align-items:center;gap:4px;justify-content:center">
        <span class="trophy-rarity-dot" style="background:${rarityColour}"></span>
        ${escHtml(rarity)}
      </div>
      <div class="badge-date">${date}</div>
    </div>`;
}

function badgeCardHtml(b) {
  const isGilded = (b.name || "").includes("★");
  const imgEl = b.image_path
    ? `<img class="badge-img" src="/img/${encodeURIPath(b.image_path)}"
           alt="${escHtml(b.name)}"
           onerror="this.replaceWith(Object.assign(document.createElement('div'),
             {className:'badge-emoji',textContent:'🏆'}))">`
    : `<div class="badge-emoji">${b.type === "laurel" ? "🌿" : "🏆"}</div>`;
  return `
    <div class="badge-card${isGilded ? " gilded" : ""}">
      ${imgEl}
      <div class="badge-name">${escHtml(b.name)}</div>
      <div class="badge-date">${b.date || ""}</div>
    </div>`;
}

// ── History (from workouts table) ─────────────────────────────────────────────
async function loadHistory() {
  try {
    const data = await api("/api/workouts");
    // endpoint returns {workouts: [...]} — normalise to bare array
    const workouts = Array.isArray(data) ? data : (data.workouts || []);
    _recentWorkouts = workouts;
    renderActivityCalendar(workouts);
    renderHistoryList(workouts, historyFilter);
    renderRecentCardio();
  } catch (e) {
    console.error("History load failed:", e);
  }
}

function renderActivityCalendar(workouts) {
  const el = document.getElementById("activity-calendar");
  const labelEl = document.getElementById("calendar-week-label");
  if (!el) return;

  const today = new Date();
  // Find Monday of this week
  const dayOfWeek = today.getDay() || 7; // make Sunday = 7
  const monday = new Date(today);
  monday.setDate(today.getDate() - (dayOfWeek - 1));

  if (labelEl) {
    const monStr = monday.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const sunDate = new Date(monday); sunDate.setDate(monday.getDate() + 6);
    const sunStr = sunDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    labelEl.textContent = `${monStr} – ${sunStr}`;
  }

  // Build set of workout dates this week
  const workedDates = new Set((workouts || []).map(w => w.date));

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const todayStr = today.toISOString().slice(0, 10);

  const cells = days.map((day, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    const isToday  = dateStr === todayStr;
    const isDone   = workedDates.has(dateStr);
    const isFuture = dateStr > todayStr;
    let cls = "cal-day";
    if (isToday)  cls += " cal-today";
    if (isDone)   cls += " cal-done";
    if (isFuture) cls += " cal-future";
    return `<div class="${cls}">
      <span class="cal-label">${day}</span>
      <span class="cal-check">${isDone ? "✓" : (isFuture ? "" : "–")}</span>
    </div>`;
  }).join("");

  el.innerHTML = `<div class="cal-week">${cells}</div>`;
}

function workoutTypeLabel(type) {
  const labels = {
    strength:    "💪 Strength",
    running:     "🏃 Run",
    walking:     "🚶 Walk",
    rucking:     "🎒 Ruck",
    hiking:      "🥾 Hike",
    recommended: "⚔️ Program",
    custom:      "⚒️ Custom",
  };
  return labels[type] || type;
}

function workoutDetail(w) {
  // Issue 7: "Clean + Press / 5 × 5 @ 16kg" format for strength entries
  if (w.type === "strength" && w.movement) {
    const name = (_apiMovements || []).find(m => m.slug === w.movement)?.name
                 || w.movement.replace(/_/g, " ").replace(/\b./g, c => c.toUpperCase());
    const setsReps = (w.sets && w.reps) ? `${w.sets} × ${w.reps}` : "";
    const weight   = w.weight_kg ? `@ ${w.weight_kg} kg` : "";
    const coins    = w.drachmae_earned ? ` · 🪙 ${Number(w.drachmae_earned).toFixed(2)}` : "";
    return [name, setsReps, weight].filter(Boolean).join(" ") + coins;
  }
  const parts = [];
  if (w.movement) parts.push(w.movement.replace(/_/g, " "));
  else if (w.notes) parts.push(w.notes);
  if (w.weight_kg) parts.push(`${w.weight_kg} kg`);
  if (w.sets && w.reps) parts.push(`${w.sets}×${w.reps}`);
  if (w.distance_miles) parts.push(`${Number(w.distance_miles).toFixed(2)} mi`);
  if (w.duration_min) {
    const totalMin = Number(w.duration_min);
    const m = Math.floor(totalMin);
    const s = Math.round((totalMin - m) * 60);
    parts.push(s > 0 ? `${m}:${String(s).padStart(2,"0")}` : `${m} min`);
  }
  if (w.weight_lbs) parts.push(`${w.weight_lbs} lbs pack`);
  if (w.drachmae_earned) parts.push(`🪙 ${Number(w.drachmae_earned).toFixed(2)}`);
  return parts.join(" · ");
}

function renderWeightLog(workouts) {
  const el = document.getElementById("history-list");
  if (!el) return;

  const strengthWos = (workouts || []).filter(w =>
    w.type === "strength" && w.movement && w.weight_kg
  );

  if (!strengthWos.length) {
    el.innerHTML = '<div class="empty-msg">No weight training logged yet — get lifting!</div>';
    return;
  }

  // Group by movement slug; workouts arrive newest-first
  const byMovement = {};
  const movementOrder = [];
  for (const w of strengthWos) {
    if (!byMovement[w.movement]) {
      byMovement[w.movement] = [];
      movementOrder.push(w.movement);
    }
    byMovement[w.movement].push(w);
  }

  el.innerHTML = movementOrder.map(slug => {
    const entries = byMovement[slug]; // newest first
    const name = (_apiMovements || []).find(m => m.slug === slug)?.name || slug;
    const latest = entries[0];
    const latestKg = latest.weight_kg;

    // Show up to last 8 sessions oldest→newest as chips
    const shown = entries.slice(0, 8).reverse();
    const chips = shown.map(w => {
      const sr   = (w.sets && w.reps) ? `${w.sets}×${w.reps}` : "";
      const wt   = `${w.weight_kg}kg`;
      const date = w.date ? w.date.slice(5).replace("-", "/") : "";
      const parts = [date, sr ? `${sr} @` : "", wt].filter(Boolean).join(" ");
      const isLatest = w === latest;
      return `<span class="wlog-chip${isLatest ? " wlog-chip-latest" : ""}">${escHtml(parts)}</span>`;
    }).join("");

    return `
      <div class="wlog-movement">
        <div class="wlog-movement-header">
          <span class="wlog-movement-name">${escHtml(name)}</span>
          <span class="wlog-latest">${latestKg} kg</span>
        </div>
        <div class="wlog-sessions">${chips}</div>
      </div>`;
  }).join("");
}

function renderHistoryList(workouts, filter) {
  const el = document.getElementById("history-list");
  if (!el) return;

  if (filter === "weights") {
    renderWeightLog(workouts);
    return;
  }

  const filtered = (workouts || []).filter(w => {
    if (filter === "all") return true;
    return w.type === filter;
  });

  if (!filtered.length) {
    el.innerHTML = '<div class="empty-msg">No activity logged yet — get moving!</div>';
    return;
  }

  const byDate = {};
  for (const w of filtered) {
    if (!w.date) continue;
    (byDate[w.date] = byDate[w.date] || []).push(w);
  }

  const dates = Object.keys(byDate).sort().reverse();
  el.innerHTML = dates.map(date => `
    <div class="history-group">
      <div class="history-date">${date}</div>
      ${byDate[date].map(w => `
        <div class="history-entry">
          <div class="history-entry-main">
            <span class="history-kind">${escHtml(workoutTypeLabel(w.type))}</span>
            <span class="history-detail">${escHtml(workoutDetail(w))}</span>
          </div>
          <div class="history-actions">
            <button class="btn-ghost-sm history-edit-btn" data-id="${w.id}" title="Edit">✏️</button>
            <button class="btn-danger-sm history-delete-btn" data-id="${w.id}" data-drach="${w.drachmae_earned || 0}" title="Delete">🗑</button>
          </div>
        </div>`).join("")}
    </div>`).join("");

  // Wire up edit/delete buttons
  el.querySelectorAll(".history-delete-btn").forEach(btn => {
    btn.addEventListener("click", () => deleteWorkout(parseInt(btn.dataset.id, 10)));
  });
  el.querySelectorAll(".history-edit-btn").forEach(btn => {
    btn.addEventListener("click", () => editWorkout(parseInt(btn.dataset.id, 10), workouts));
  });
}

async function deleteWorkout(id) {
  if (!confirm("Delete this workout? Drachmae will be deducted.")) return;
  try {
    const r = await api(`/api/workout/${id}`, undefined, "DELETE");
    toast("🗑 Workout deleted.", 2500);
    if (r.state) { estateState = r.state; renderEstateResources(); }
    loadHistory();
  } catch (e) { toast("⚠ " + e.message); }
}

function editWorkout(id, workouts) {
  const w = (workouts || _recentWorkouts).find(x => x.id === id);
  if (!w) return;

  const el = document.getElementById("history-list");
  const entryEl = el?.querySelector(`.history-delete-btn[data-id="${id}"]`)?.closest(".history-entry");
  if (!entryEl) return;

  entryEl.innerHTML = `
    <div class="edit-workout-form">
      ${w.distance_miles != null ? `
        <div class="field-group">
          <label>Miles</label>
          <input type="number" id="edit-miles-${id}" value="${w.distance_miles}" step="0.01" min="0">
        </div>` : ""}
      ${w.weight_kg != null ? `
        <div class="field-group">
          <label>Weight (kg)</label>
          <input type="number" id="edit-kg-${id}" value="${w.weight_kg}" step="0.5" min="0">
        </div>` : ""}
      ${w.sets != null ? `
        <div class="field-group">
          <label>Sets</label>
          <input type="number" id="edit-sets-${id}" value="${w.sets}" step="1" min="1">
        </div>
        <div class="field-group">
          <label>Reps</label>
          <input type="number" id="edit-reps-${id}" value="${w.reps}" step="1" min="1">
        </div>` : ""}
      <div class="edit-workout-actions">
        <button class="btn-primary" id="save-edit-${id}">Save</button>
        <button class="btn-ghost" id="cancel-edit-${id}">Cancel</button>
      </div>
    </div>`;

  document.getElementById(`cancel-edit-${id}`)?.addEventListener("click", loadHistory);
  document.getElementById(`save-edit-${id}`)?.addEventListener("click", async () => {
    const updates = {};
    const milesEl = document.getElementById(`edit-miles-${id}`);
    const kgEl    = document.getElementById(`edit-kg-${id}`);
    const setsEl  = document.getElementById(`edit-sets-${id}`);
    const repsEl  = document.getElementById(`edit-reps-${id}`);
    if (milesEl) updates.distance_miles = parseFloat(milesEl.value);
    if (kgEl)    updates.weight_kg      = parseFloat(kgEl.value);
    if (setsEl)  updates.sets           = parseInt(setsEl.value, 10);
    if (repsEl)  updates.reps           = parseInt(repsEl.value, 10);
    try {
      const r = await api(`/api/workout/${id}`, updates, "PUT");
      toast("✏️ Workout updated.");
      if (r.state) { estateState = r.state; renderEstateResources(); }
      loadHistory();
    } catch (e) { toast("⚠ " + e.message); }
  });
}

// ── Track preview modal ───────────────────────────────────────────────────────
async function showTrackPreview() {
  const key = document.getElementById("track-select").value;
  if (!key) return;

  try {
    const track = await api(`/api/tracks/${key}`);
    previewedKey = key;
    document.getElementById("preview-track-name").textContent = track.name;

    const sessionsHtml = track.sessions.map((s, i) => `
      <div class="preview-session">
        <div class="preview-session-header">
          <span class="preview-session-num">S${i + 1}</span>
          <span class="preview-session-main">${escHtml(s.main)}</span>
          <span class="preview-session-chevron">›</span>
        </div>
        <div class="preview-session-body">
          <ul class="preview-accessories">
            ${(s.accessory || []).map(a => `<li>${escHtml(a)}</li>`).join("")}
          </ul>
          <div class="preview-finisher">⚡ ${escHtml(s.finisher || "")}</div>
        </div>
      </div>`).join("");

    document.getElementById("preview-sessions").innerHTML = sessionsHtml;

    document.querySelectorAll(".preview-session-header").forEach(h => {
      h.addEventListener("click", () => h.closest(".preview-session").classList.toggle("open"));
    });

    document.getElementById("preview-dialog").removeAttribute("hidden");
  } catch (e) {
    toast("⚠ " + e.message);
  }
}

function closePreviewDialog() {
  document.getElementById("preview-dialog").setAttribute("hidden", "");
  previewedKey = null;
}

async function startPreviewedTrack() {
  if (!previewedKey) return;
  closePreviewDialog();
  document.getElementById("track-select").value = previewedKey;
  await startTrack(previewedKey);
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function logRecommended() {
  const btn = document.getElementById("log-session-btn");
  const weights = {};
  document.querySelectorAll("#workout-display .movement-weight-input").forEach(inp => {
    const v = parseFloat(inp.value || 0);
    if (v > 0) weights[inp.dataset.key] = v;
  });
  const payload = Object.keys(weights).length > 0 ? { weights_lbs: weights } : {};

  if (btn) btn.disabled = true;
  try {
    const r = await api("/api/workout/recommended", payload);
    toast(r.msg || "⚔️ Session logged!", 3000, "drachmae");
    checkLaurelEvents(r.events);
    appState = r.state;
    // Issue 11/3: sync estate drachmae from volume-based reward
    if (r.estate_state) { estateState = r.estate_state; renderEstateResources(); }
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    loadHistory();
    // Show oracle dialogue popup if triggered
    if (r.oracle_event) showEventPopup(r.oracle_event);
  } catch (e) { toast("⚠ " + e.message); }
  finally { if (btn) btn.disabled = false; }
}

async function startTrack(key) {
  const k = key || document.getElementById("track-select").value;
  if (!k) return;
  try {
    const r = await api("/api/track/select", { key: k });
    toast(r.msg || "Track started!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    await populateTracks(appState);
  } catch (e) { toast("⚠ " + e.message); }
}

async function deleteCustomTrack() {
  const sel = document.getElementById("track-select");
  const key = sel.value;
  if (!key.startsWith("custom_")) return;
  const trackId = key.slice(7);
  const trackName = sel.options[sel.selectedIndex]?.text || "this cycle";
  if (!confirm(`Delete ${trackName}? This cannot be undone.`)) return;
  try {
    const r = await api(`/api/tracks/custom/${trackId}`, undefined, "DELETE");
    toast("🗑 Custom cycle deleted.");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    await populateTracks(appState);
  } catch (e) { toast("⚠ " + e.message); }
}

// ── Cardio logging (unified) ───────────────────────────────────────────────────
async function logCardio() {
  const miles    = parseFloat(document.getElementById("cardio-miles").value || 0);
  // Issue 6: min + sec inputs → decimal minutes
  const durMin   = parseFloat(document.getElementById("cardio-duration-min")?.value || 0) || 0;
  const durSec   = parseFloat(document.getElementById("cardio-duration-sec")?.value  || 0) || 0;
  const duration = (durMin > 0 || durSec > 0) ? durMin + durSec / 60 : null;
  const lbs      = parseFloat(document.getElementById("cardio-weight-lbs").value || 0) || null;

  if (!miles || miles <= 0) { toast("Enter a valid distance."); return; }

  const typeToEndpoint = {
    running: "/api/run",
    walking: "/api/walk",
    rucking: "/api/ruck",
    hiking:  "/api/hike",
  };
  const endpoint = typeToEndpoint[activeCardioType] || "/api/run";

  const payload = { miles };
  if (duration) payload.duration_min = duration;
  if (lbs && (activeCardioType === "rucking" || activeCardioType === "hiking")) payload.pounds = lbs;

  const emojis = { running: "🏃", walking: "🚶", rucking: "🎒", hiking: "🥾" };
  const emoji  = emojis[activeCardioType] || "🏃";

  try {
    const r = await api(endpoint, payload);
    toast(r.msg || `${emoji} Cardio logged!`, 3000, "drachmae");
    checkLaurelEvents(r.events);
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    document.getElementById("cardio-miles").value = "";
    const dMin = document.getElementById("cardio-duration-min");
    const dSec = document.getElementById("cardio-duration-sec");
    if (dMin) dMin.value = "";
    if (dSec) dSec.value = "";
    prevBadgeCount = (appState.badges || []).length;
    // loadHistory fetches workouts, then calls renderActivityCalendar + renderRecentCardio internally
    loadHistory();
    // Show oracle dialogue popup if triggered
    if (r.oracle_event) showEventPopup(r.oracle_event);
  } catch (e) { toast("⚠ " + e.message); }
}

// Render recent cardio items from the global workouts cache
let _recentWorkouts = [];

function renderRecentCardio() {
  const el = document.getElementById("recent-cardio");
  if (!el) return;
  const cardioTypes = new Set(["running", "walking", "rucking", "hiking"]);
  const recent = _recentWorkouts.filter(w => cardioTypes.has(w.type)).slice(0, 8);
  if (!recent.length) {
    el.innerHTML = '<p class="dim-msg">No cardio logged yet.</p>';
    return;
  }
  const typeEmoji = { running: "🏃", walking: "🚶", rucking: "🎒", hiking: "🥾" };
  el.innerHTML = recent.map(w => {
    const emoji   = typeEmoji[w.type] || "🏃";
    const miles   = w.distance_miles != null ? `${Number(w.distance_miles).toFixed(2)} mi` : "";
    const dur     = w.duration_min ? ` · ${w.duration_min} min` : "";
    const coins   = w.drachmae_earned != null ? ` · 🪙 ${Number(w.drachmae_earned).toFixed(2)}` : "";
    return `<div class="recent-run-item">
      <span class="run-miles-text">${emoji} ${miles}${dur}</span>
      <span class="run-date-text">${w.date || ""}${coins}</span>
    </div>`;
  }).join("");
}

// ── Program Picker ────────────────────────────────────────────────────────────
function openProgramPicker() {
  document.getElementById("program-picker-dialog").hidden = false;
}
function closeProgramPicker() {
  document.getElementById("program-picker-dialog").hidden = true;
}

// ── Custom Work (new categories + movements) ──────────────────────────────────
let _apiMovements    = null;    // from /api/movements
let _customCatFilter = "kettlebell";

// Hardcoded movement lists per category (API used for KB/Barbell/Bodyweight where possible)
const CUSTOM_WORK_MOVEMENTS = {
  kettlebell: null,  // filled from API: swing/snatch/clean/press/hinge/get_up/row/carry
  dumbbell: [
    "Dumbbell Press", "Dumbbell Row", "Dumbbell Curl", "Dumbbell Lunge",
    "Romanian Deadlift", "Lateral Raise", "Dumbbell Squat", "Dumbbell Fly",
    "Tricep Extension", "Dumbbell Shoulder Press", "Goblet Squat",
  ],
  barbell: null,     // filled from API: barbell category
  bodyweight: null,  // filled from API: bodyweight category
  yoga: [
    "Sun Salutation", "Warrior Flow", "Vinyasa Flow", "Mobility Flow",
    "Yin Yoga", "Hip Opening Flow", "Balance Flow", "Restorative Flow",
  ],
  pilates: [
    "Hundred", "Roll Up", "Teaser", "Core Series",
    "Single Leg Stretch", "Double Leg Stretch", "Spine Stretch", "Plank Series",
  ],
};

// Categories where weight input should be hidden
const NO_WEIGHT_CATS = new Set(["bodyweight", "yoga", "pilates"]);

const KB_API_CATS = new Set(["swing","snatch","clean","press","squat","hinge","get_up","row","carry"]);

async function initCustomWorkSelector() {
  if (!_apiMovements) {
    try { _apiMovements = await api("/api/movements"); } catch (_) { _apiMovements = []; }
  }
  // Populate movement lists from API (Issue 5: includes squat + dumbbell now)
  CUSTOM_WORK_MOVEMENTS.kettlebell = _apiMovements.filter(m => KB_API_CATS.has(m.category));
  CUSTOM_WORK_MOVEMENTS.dumbbell   = _apiMovements.filter(m => m.category === "dumbbell");
  CUSTOM_WORK_MOVEMENTS.barbell    = _apiMovements.filter(m => m.category === "barbell");
  CUSTOM_WORK_MOVEMENTS.bodyweight = _apiMovements.filter(m => m.category === "bodyweight");

  updateCustomMovementSelect();

  // Category pill clicks
  const catsEl = document.getElementById("custom-cats");
  if (catsEl) {
    catsEl.addEventListener("click", e => {
      const btn = e.target.closest(".cat-btn");
      if (!btn) return;
      _customCatFilter = btn.dataset.cat;
      // Update active state
      catsEl.querySelectorAll(".cat-btn").forEach(b =>
        b.classList.toggle("active", b.dataset.cat === _customCatFilter));
      updateCustomMovementSelect();
      // Toggle weight field
      const wg = document.getElementById("custom-weight-group");
      if (wg) wg.style.display = NO_WEIGHT_CATS.has(_customCatFilter) ? "none" : "";
    });
  }

  const sel = document.getElementById("custom-movement-select");
  if (sel) sel.addEventListener("change", updateCustomLastWeight);

  // Init weight field visibility
  const wg = document.getElementById("custom-weight-group");
  if (wg) wg.style.display = NO_WEIGHT_CATS.has(_customCatFilter) ? "none" : "";
}

function updateCustomMovementSelect() {
  const sel = document.getElementById("custom-movement-select");
  if (!sel) return;
  const list = CUSTOM_WORK_MOVEMENTS[_customCatFilter] || [];
  sel.innerHTML = list.length
    ? list.map(m => {
        const name = typeof m === "string" ? m : m.name;
        const slug = typeof m === "string" ? m.toLowerCase().replace(/\s+/g, "_") : m.slug;
        return `<option value="${escHtml(slug)}">${escHtml(name)}</option>`;
      }).join("")
    : '<option value="">No movements available</option>';
  updateCustomLastWeight();
}

async function updateCustomLastWeight() {
  const sel  = document.getElementById("custom-movement-select");
  const hint = document.getElementById("custom-last-weight");
  if (!sel || !hint) return;
  const slug = sel.value;
  if (!slug) { hint.textContent = ""; return; }
  // Try backend history first, fall back to localStorage
  try {
    const data = await api(`/api/movement_history/${encodeURIComponent(slug)}`);
    if (data.sets && data.reps) {
      const w = data.weight_kg ? ` @ ${data.weight_kg} kg` : "";
      hint.textContent = `Last: ${data.sets}×${data.reps}${w}`;
      return;
    }
  } catch (_) {}
  const last = localStorage.getItem("lastWeight_" + slug);
  hint.textContent = last ? `Last used: ${last} kg` : "";
}

// ── Multi-exercise session queue ──────────────────────────────────────────────
let _sessionQueue = [];   // [{movement, movementName, weightKg, sets, reps, needsWeight}]

function _readExerciseInputs() {
  const sel         = document.getElementById("custom-movement-select");
  const movement    = sel?.value || "";
  const movementName = sel?.options[sel?.selectedIndex]?.text || movement;
  const weightKg    = parseFloat(document.getElementById("custom-weight")?.value || 0);
  const sets        = parseInt(document.getElementById("custom-sets")?.value  || 0, 10);
  const reps        = parseInt(document.getElementById("custom-reps")?.value  || 0, 10);
  const needsWeight = !NO_WEIGHT_CATS.has(_customCatFilter);
  return { movement, movementName, weightKg, sets, reps, needsWeight };
}

function _validateExercise({ movement, weightKg, sets, reps, needsWeight }) {
  if (!movement)                           { toast("Select a movement.");  return false; }
  if (!sets  || sets  <= 0)                { toast("Enter sets.");         return false; }
  if (!reps  || reps  <= 0)                { toast("Enter reps.");         return false; }
  if (needsWeight && (!weightKg || weightKg <= 0)) { toast("Enter a weight."); return false; }
  return true;
}

function _clearExerciseInputs() {
  document.getElementById("custom-weight").value = "";
  document.getElementById("custom-sets").value   = "";
  document.getElementById("custom-reps").value   = "";
}

function renderSessionQueue() {
  const wrap   = document.getElementById("session-queue-wrap");
  const listEl = document.getElementById("session-queue-list");
  if (!wrap || !listEl) return;
  if (!_sessionQueue.length) { wrap.hidden = true; return; }
  wrap.hidden = false;
  listEl.innerHTML = _sessionQueue.map((ex, i) => {
    const wt = ex.needsWeight && ex.weightKg > 0 ? ` @ ${ex.weightKg} kg` : "";
    return `<li class="session-queue-item">
      <span>${escHtml(ex.movementName)} — ${ex.sets}×${ex.reps}${escHtml(wt)}</span>
      <button class="session-queue-remove" data-idx="${i}" title="Remove">✕</button>
    </li>`;
  }).join("");
  listEl.querySelectorAll(".session-queue-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      _sessionQueue.splice(parseInt(btn.dataset.idx, 10), 1);
      renderSessionQueue();
    });
  });
}

function addToSession() {
  const ex = _readExerciseInputs();
  if (!_validateExercise(ex)) return;
  if (ex.needsWeight && ex.weightKg > 0)
    localStorage.setItem("lastWeight_" + ex.movement, String(ex.weightKg));
  _sessionQueue.push(ex);
  renderSessionQueue();
  _clearExerciseInputs();
  toast(`Added: ${ex.movementName}`, 1500);
}

async function submitSession() {
  if (!_sessionQueue.length) { toast("Add exercises first."); return; }
  const btn = document.getElementById("submit-session-btn");
  if (btn) btn.disabled = true;
  try {
    let lastEstateState = null;
    let allEvents = [];
    for (const ex of _sessionQueue) {
      const payload = { movement: ex.movement, sets: ex.sets, reps: ex.reps };
      if (ex.needsWeight && ex.weightKg > 0) payload.weight_kg = ex.weightKg;
      const r = await api("/api/strength", payload);
      if (r.estate_state) lastEstateState = r.estate_state;
      allEvents = allEvents.concat(r.events || []);
      if (r.oracle_event) showEventPopup(r.oracle_event);
    }
    if (lastEstateState) { estateState = lastEstateState; renderEstateResources(); }
    checkLaurelEvents(allEvents);
    toast(`⚔️ Session logged — ${_sessionQueue.length} exercise${_sessionQueue.length > 1 ? "s" : ""}`, 3000, "drachmae");
    _sessionQueue = [];
    renderSessionQueue();
    _clearExerciseInputs();
    loadHistory();
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
  } catch (e) { toast("⚠ " + e.message); }
  finally { if (btn) btn.disabled = false; }
}

async function logExercise() {
  const ex = _readExerciseInputs();
  if (!_validateExercise(ex)) return;
  if (ex.needsWeight && ex.weightKg > 0) {
    localStorage.setItem("lastWeight_" + ex.movement, String(ex.weightKg));
    updateCustomLastWeight();
  }
  const btn = document.getElementById("log-exercise-btn");
  if (btn) btn.disabled = true;
  try {
    const payload = { movement: ex.movement, sets: ex.sets, reps: ex.reps };
    if (ex.needsWeight && ex.weightKg > 0) payload.weight_kg = ex.weightKg;
    const r = await api("/api/strength", payload);
    toast(r.msg || "💪 Exercise logged!", 3000, "drachmae");
    checkLaurelEvents(r.events);
    if (r.estate_state) { estateState = r.estate_state; renderEstateResources(); }
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    prevBadgeCount = (appState.badges || []).length;
    _clearExerciseInputs();
    loadHistory();
    if (r.oracle_event) showEventPopup(r.oracle_event);
  } catch (e) { toast("⚠ " + e.message); }
  finally { if (btn) btn.disabled = false; }
}

// ── Log by Time ───────────────────────────────────────────────────────────────
async function logTimed() {
  const btn            = document.getElementById("log-timed-btn");
  const workout_subtype = document.getElementById("timed-subtype")?.value || "general";
  const minutes        = parseFloat(document.getElementById("timed-duration-min")?.value || 0) || 0;
  const seconds        = parseFloat(document.getElementById("timed-duration-sec")?.value  || 0) || 0;

  if (minutes <= 0 && seconds <= 0) {
    toast("⚠ Enter a duration before logging.", 3000);
    return;
  }

  if (btn) btn.disabled = true;
  try {
    const r = await api("/api/workout/timed", { workout_subtype, minutes, seconds });
    toast(r.msg || "⏱ Session logged!", 3000, "drachmae");
    checkLaurelEvents(r.events);
    if (r.estate_state) { estateState = r.estate_state; renderEstateResources(); }
    if (r.trophy_award) showTrophyAwardBanner(r.trophy_award);
    // Clear inputs
    const minEl = document.getElementById("timed-duration-min");
    const secEl = document.getElementById("timed-duration-sec");
    if (minEl) minEl.value = "";
    if (secEl) secEl.value = "";
    loadHistory();
    if (r.oracle_event) showEventPopup(r.oracle_event);
  } catch (e) { toast("⚠ " + e.message); }
  finally { if (btn) btn.disabled = false; }
}

// ── Badge notification ────────────────────────────────────────────────────────
function checkNewBadges(state) {
  const count = (state.badges || []).length;
  if (count > prevBadgeCount && prevBadgeCount > 0) {
    const newest = state.badges[state.badges.length - 1];
    if (newest) toast(`🎉 ${newest.name} unlocked!`, 5000, "trophy");
  }
  prevBadgeCount = count;
}

// ── Laurel popup ──────────────────────────────────────────────────────────────
function checkLaurelEvents(events) {
  const laurelEvt = (events || []).find(e =>
    typeof e === "string" && e.toUpperCase().includes("LAUREL"));
  if (laurelEvt) showLaurelPopup(laurelEvt);
}

function showLaurelPopup(msg) {
  const popup = document.getElementById("laurel-popup");
  const msgEl = document.getElementById("laurel-popup-msg");
  if (!popup) return;
  if (msgEl) msgEl.textContent = msg;
  popup.hidden = false;
  // Re-fetch estate to get the updated laurel count — updates top banner + estate resources
  api("/api/estate/state").then(fresh => {
    estateState = fresh;
    renderEstateResources();
  }).catch(() => {});
  initBlessings().catch(() => {});
}

document.getElementById("laurel-popup-close")?.addEventListener("click", () => {
  const popup = document.getElementById("laurel-popup");
  if (popup) popup.hidden = true;
});

// ── Agora ─────────────────────────────────────────────────────────────────────
let _marketPrices = null;

// Advanced products are hidden until their production building is built
const ADVANCED_PRODUCT_GATE = {
  wine:      "winery",
  bread:     "bakery",
  olive_oil: "olive_press",
  mead:      "meadery",
};

async function initAgora() {
  try {
    if (!_marketPrices) {
      _marketPrices = await fetch("/static/market_prices.json").then(r => r.json());
    }
    renderAgora();
  } catch (e) {
    const el = document.getElementById("agora-grid");
    if (el) el.innerHTML = '<p class="dim-msg">Market unavailable.</p>';
  }
}

function renderAgora() {
  const el = document.getElementById("agora-grid");
  if (!el || !_marketPrices || !estateState) return;

  // Filter out advanced products whose production building hasn't been built yet
  const builtBuildings = new Set(estateState.processing_buildings || []);
  const resources = Object.entries(_marketPrices).filter(([key]) => {
    const gate = ADVANCED_PRODUCT_GATE[key];
    return !gate || builtBuildings.has(gate);
  });
  if (!resources.length) {
    el.innerHTML = '<p class="dim-msg">No goods available.</p>';
    return;
  }

  el.innerHTML = resources.map(([key, info]) => {
    const stock = estateState[key] ?? 0;
    return `<div class="agora-item">
      <div class="agora-item-icon">${info.emoji}</div>
      <div class="agora-item-info">
        <div class="agora-item-name">${escHtml(info.label)}</div>
        <div class="agora-item-stock sub-text">Stock: ${stock}</div>
        <div class="agora-item-price sub-text">🪙 ${info.price}/unit</div>
      </div>
      <div class="agora-sell-btns">
        <button class="btn-outline-sm agora-sell-btn"
                data-resource="${key}" data-qty="1" ${stock < 1 ? "disabled" : ""}>
          Sell 1
        </button>
        <button class="btn-outline-sm agora-sell-btn"
                data-resource="${key}" data-qty="all" ${stock < 1 ? "disabled" : ""}>
          All
        </button>
      </div>
    </div>`;
  }).join("");

  el.querySelectorAll(".agora-sell-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const resource = btn.dataset.resource;
      const qty      = btn.dataset.qty === "all"
        ? (estateState[resource] ?? 0)
        : 1;
      if (qty <= 0) return;
      btn.disabled = true;
      try {
        const r = await api("/api/estate/agora/sell", { resource, quantity: qty });
        estateState = r.state;
        renderEstateResources();
        const earned = (qty * (_marketPrices[resource]?.price || 0)).toFixed(2);
        toast(`🏛️ Sold ${qty} ${_marketPrices[resource]?.label || resource} for 🪙 ${earned}`, 3000, "drachmae");
        pushEstateLog(`🏛️ Sold ${qty} ${_marketPrices[resource]?.label || resource} → +${earned} 🪙`, "reward");
        renderAgora();
      } catch (e) {
        toast("⚠ " + e.message);
        btn.disabled = false;
      }
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// ── Cycle Builder ─────────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

// Builder state
let builderSessions        = [];   // array of session data objects
let builderActiveTab       = 0;    // which session tab is shown
let lastFocusedBuilderInput = null; // the input element last focused in the editor
let libActiveCategory      = "all";
let libSearchText          = "";
let movementsCache         = null; // fetched once from /api/movements

// Category display names
const LIB_CATEGORIES = [
  { key: "all",       label: "All"      },
  { key: "swing",     label: "Swing"    },
  { key: "snatch",    label: "Snatch"   },
  { key: "clean",     label: "Clean"    },
  { key: "press",     label: "Press"    },
  { key: "squat",     label: "Squat"    },
  { key: "hinge",     label: "Hinge"    },
  { key: "get_up",    label: "Get-Up"   },
  { key: "row",       label: "Row"      },
  { key: "carry",     label: "Carry"    },
  { key: "barbell",   label: "Barbell"  },
  { key: "bodyweight",label: "BW"       },
];

function blankSession() {
  return { main: "", std_kg: 16, acc_0: "", acc_1: "", acc_2: "", finisher: "" };
}

/** Open the builder dialog. Fetches movements if not yet cached. */
async function openBuilderDialog() {
  // Reset state
  builderSessions  = [blankSession()];
  builderActiveTab = 0;
  lastFocusedBuilderInput = null;

  // Reset footer name
  document.getElementById("builder-name").value = "";

  // Fetch movements (cached after first load)
  if (!movementsCache) {
    try {
      movementsCache = await api("/api/movements");
    } catch (_) {
      movementsCache = [];
    }
  }

  renderBuilderTabs();
  renderBuilderEditor();
  renderLibraryCats();
  renderLibraryGrid();

  document.getElementById("builder-dialog").removeAttribute("hidden");
}

function closeBuilderDialog() {
  document.getElementById("builder-dialog").setAttribute("hidden", "");
}

/** Render the session tab buttons (S1, S2… + Add). */
function renderBuilderTabs() {
  const container = document.getElementById("builder-tabs");
  let html = builderSessions.map((_, i) =>
    `<button class="builder-tab-btn${i === builderActiveTab ? " active" : ""}"
             data-tab="${i}">S${i + 1}</button>`
  ).join("");
  if (builderSessions.length < 6) {
    html += `<button class="builder-tab-add" id="builder-add-tab">+ Add</button>`;
  }
  container.innerHTML = html;
}

/** Read all input values for the currently active session into builderSessions. */
function readBuilderSessionInputs() {
  const s = builderSessions[builderActiveTab];
  if (!s) return;
  const editor = document.getElementById("builder-session-editor");
  editor.querySelectorAll("[data-slot]").forEach(el => {
    const slot = el.dataset.slot;
    s[slot] = el.value;
  });
}

/** Render the editor panel for the active session. */
function renderBuilderEditor() {
  const idx = builderActiveTab;
  const s   = builderSessions[idx];
  const editor = document.getElementById("builder-session-editor");

  const stdOptions = [8, 12, 16, 20, 24, 28, 32].map(kg =>
    `<option value="${kg}"${parseFloat(s.std_kg) === kg ? " selected" : ""}>${kg} kg</option>`
  ).join("") + `<option value="0"${parseFloat(s.std_kg) === 0 ? " selected" : ""}>BW</option>`;

  editor.innerHTML = `
    <div class="builder-sess-hdr">
      <span class="builder-sess-num">Session ${idx + 1} of ${builderSessions.length}</span>
      ${builderSessions.length > 1
        ? `<button class="builder-remove-btn" data-action="remove-session">🗑 Remove</button>`
        : ""}
    </div>

    <div class="builder-slot-row">
      <label>Main Movement *</label>
      <input type="text" class="builder-slot-input" data-slot="main"
             value="${escHtml(s.main)}" placeholder="e.g. KB Swing 5×15" autocomplete="off">
    </div>

    <div class="builder-slot-row">
      <label>Standard Bell Weight</label>
      <select class="builder-std-select" data-slot="std_kg">${stdOptions}</select>
    </div>

    <div class="builder-slot-row">
      <label>Accessory 1</label>
      <input type="text" class="builder-slot-input" data-slot="acc_0"
             value="${escHtml(s.acc_0)}" placeholder="Optional" autocomplete="off">
    </div>
    <div class="builder-slot-row">
      <label>Accessory 2</label>
      <input type="text" class="builder-slot-input" data-slot="acc_1"
             value="${escHtml(s.acc_1)}" placeholder="Optional" autocomplete="off">
    </div>
    <div class="builder-slot-row">
      <label>Accessory 3</label>
      <input type="text" class="builder-slot-input" data-slot="acc_2"
             value="${escHtml(s.acc_2)}" placeholder="Optional" autocomplete="off">
    </div>

    <div class="builder-slot-row">
      <label>Finisher</label>
      <input type="text" class="builder-slot-input" data-slot="finisher"
             value="${escHtml(s.finisher)}" placeholder="Optional" autocomplete="off">
    </div>`;

  // Track the last-focused input (for movement library insertion)
  editor.querySelectorAll(".builder-slot-input").forEach(inp => {
    inp.addEventListener("focus", () => {
      // Remove highlight from all, add to this one
      editor.querySelectorAll(".builder-slot-input").forEach(i =>
        i.classList.remove("focused-slot"));
      inp.classList.add("focused-slot");
      lastFocusedBuilderInput = inp;
    });
  });
}

/** Switch to a different session tab (saving current inputs first). */
function switchBuilderTab(idx) {
  readBuilderSessionInputs();
  builderActiveTab = idx;
  renderBuilderTabs();
  renderBuilderEditor();
  lastFocusedBuilderInput = null;
}

/** Add a new blank session. */
function addBuilderSession() {
  if (builderSessions.length >= 6) return;
  readBuilderSessionInputs();
  builderSessions.push(blankSession());
  builderActiveTab = builderSessions.length - 1;
  renderBuilderTabs();
  renderBuilderEditor();
  lastFocusedBuilderInput = null;
}

/** Remove the active session. */
function removeBuilderSession() {
  if (builderSessions.length <= 1) return;
  builderSessions.splice(builderActiveTab, 1);
  builderActiveTab = Math.min(builderActiveTab, builderSessions.length - 1);
  renderBuilderTabs();
  renderBuilderEditor();
  lastFocusedBuilderInput = null;
}

/** Render category filter pills. */
function renderLibraryCats() {
  const container = document.getElementById("lib-cats");
  container.innerHTML = LIB_CATEGORIES.map(c =>
    `<button class="lib-cat-btn${c.key === libActiveCategory ? " active" : ""}"
             data-cat="${c.key}">${c.label}</button>`
  ).join("");
}

/** Render the filtered movement pill grid. */
function renderLibraryGrid() {
  const container = document.getElementById("lib-grid");
  if (!movementsCache) {
    container.innerHTML = `<span style="color:var(--text-dim);font-size:.8rem">Loading…</span>`;
    return;
  }

  const search = libSearchText.trim().toLowerCase();
  const filtered = movementsCache.filter(m => {
    const catMatch  = libActiveCategory === "all" || m.category === libActiveCategory;
    const textMatch = !search || m.name.toLowerCase().includes(search);
    return catMatch && textMatch;
  });

  if (!filtered.length) {
    container.innerHTML = `<span style="color:var(--text-dim);font-size:.8rem;font-style:italic">No movements found.</span>`;
    return;
  }

  container.innerHTML = filtered.map(m =>
    `<button class="lib-movement-pill"
             data-slug="${m.slug}"
             data-name="${escHtml(m.name)}"
             data-hint="${escHtml(m.hint)}"
             title="${escHtml(m.name)} — ${escHtml(m.hint)}">${escHtml(m.name)}</button>`
  ).join("");
}

/** Insert a movement from the library into the last-focused builder slot. */
function insertMovement(name, hint) {
  if (!lastFocusedBuilderInput) {
    toast("Tap a slot above first, then pick a movement.");
    return;
  }
  const text = hint ? `${name} ${hint}` : name;
  lastFocusedBuilderInput.value = text;
  lastFocusedBuilderInput.focus();
  lastFocusedBuilderInput.classList.add("focused-slot");
  // Keep visual focus highlight
}

/** Validate builder state and save cycle via API, then start it. */
async function saveBuilderCycle() {
  // Flush current editor inputs
  readBuilderSessionInputs();

  const name = document.getElementById("builder-name").value.trim();
  if (!name) {
    document.getElementById("builder-name").focus();
    toast("Please name your cycle first.");
    return;
  }

  // Build session payload
  const sessions = builderSessions.map(s => ({
    main:      s.main.trim(),
    std_kg:    parseFloat(s.std_kg) || 16,
    accessory: [s.acc_0, s.acc_1, s.acc_2].filter(a => a.trim()),
    finisher:  s.finisher.trim(),
  }));

  const firstEmpty = sessions.findIndex(s => !s.main);
  if (firstEmpty >= 0) {
    switchBuilderTab(firstEmpty);
    toast(`Session ${firstEmpty + 1} needs a main movement.`);
    return;
  }

  try {
    const r = await api("/api/tracks/custom", { name, sessions });
    toast(`⚒ "${name}" saved! Starting now…`);
    appState = r.state;
    closeBuilderDialog();
    closeProgramPicker();

    // Start the new track immediately
    const trackKey = `custom_${r.track.id}`;
    await startTrack(trackKey);
    await populateTracks(appState);
    // Select the new track in the picker
    document.getElementById("track-select").value = trackKey;
    updateDeleteTrackBtn();
  } catch (e) {
    toast("⚠ " + e.message);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// ── Event wiring ──────────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

// Bottom nav
document.querySelectorAll(".nav-btn").forEach(btn =>
  btn.addEventListener("click", () => switchSection(btn.dataset.section)));

// Train section
document.getElementById("refresh-btn").addEventListener("click", refresh);
document.getElementById("log-session-btn")?.addEventListener("click", logRecommended);
document.getElementById("log-exercise-btn")?.addEventListener("click", logExercise);
document.getElementById("add-to-session-btn")?.addEventListener("click", addToSession);
document.getElementById("submit-session-btn")?.addEventListener("click", submitSession);

// Program picker
document.getElementById("choose-program-btn")?.addEventListener("click", openProgramPicker);
document.getElementById("change-program-btn")?.addEventListener("click", openProgramPicker);
document.getElementById("view-program-btn")?.addEventListener("click", showTrackPreview);
document.getElementById("close-program-picker-btn")?.addEventListener("click", closeProgramPicker);
document.getElementById("program-picker-dialog")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) closeProgramPicker();
});
document.getElementById("preview-track-btn").addEventListener("click", showTrackPreview);
document.getElementById("start-track-btn").addEventListener("click", async () => {
  await startTrack();
  closeProgramPicker();
});
document.getElementById("delete-track-btn").addEventListener("click", deleteCustomTrack);
document.getElementById("open-builder-btn").addEventListener("click", openBuilderDialog);
document.getElementById("track-select").addEventListener("change", updateDeleteTrackBtn);

// Log by Time
document.getElementById("log-timed-btn")?.addEventListener("click", logTimed);

// Cardio section
document.getElementById("log-cardio-btn")?.addEventListener("click", logCardio);

// Track preview dialog
document.getElementById("close-preview-btn").addEventListener("click", closePreviewDialog);
document.getElementById("cancel-preview-btn").addEventListener("click", closePreviewDialog);
document.getElementById("start-previewed-btn").addEventListener("click", startPreviewedTrack);
document.getElementById("preview-dialog").addEventListener("click", e => {
  if (e.target === e.currentTarget) closePreviewDialog();
});

// History filters
document.querySelectorAll(".filter-btn").forEach(btn =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    historyFilter = btn.dataset.filter;
    renderHistoryList(_recentWorkouts, historyFilter);
  }));

// Builder dialog — header/footer buttons
document.getElementById("close-builder-btn").addEventListener("click", closeBuilderDialog);
document.getElementById("cancel-builder-btn").addEventListener("click", closeBuilderDialog);
document.getElementById("save-builder-btn").addEventListener("click", saveBuilderCycle);
document.getElementById("builder-dialog").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeBuilderDialog();
});

// Builder dialog — event delegation for dynamic elements
document.getElementById("builder-tabs").addEventListener("click", e => {
  const tabBtn = e.target.closest(".builder-tab-btn");
  if (tabBtn) { switchBuilderTab(parseInt(tabBtn.dataset.tab, 10)); return; }
  if (e.target.id === "builder-add-tab" || e.target.closest("#builder-add-tab")) {
    addBuilderSession();
  }
});

document.getElementById("builder-session-editor").addEventListener("click", e => {
  const removeBtn = e.target.closest("[data-action='remove-session']");
  if (removeBtn) removeBuilderSession();
});

// Library category filter pills
document.getElementById("lib-cats").addEventListener("click", e => {
  const btn = e.target.closest(".lib-cat-btn");
  if (!btn) return;
  libActiveCategory = btn.dataset.cat;
  renderLibraryCats();
  renderLibraryGrid();
});

// Library search input
document.getElementById("lib-search").addEventListener("input", e => {
  libSearchText = e.target.value;
  renderLibraryGrid();
});

// Library movement pills — use mousedown to avoid blurring the focused slot input
document.getElementById("lib-grid").addEventListener("mousedown", e => {
  const pill = e.target.closest(".lib-movement-pill");
  if (!pill) return;
  e.preventDefault();   // prevent blur on focused slot input
  insertMovement(pill.dataset.name, pill.dataset.hint);
});
// Touch support for mobile
document.getElementById("lib-grid").addEventListener("touchend", e => {
  const pill = e.target.closest(".lib-movement-pill");
  if (!pill) return;
  e.preventDefault();
  insertMovement(pill.dataset.name, pill.dataset.hint);
});

// ══════════════════════════════════════════════════════════════════════════════
// ESTATE TAB  (Laurel of Olympus RPG)
// ══════════════════════════════════════════════════════════════════════════════

const ESTATE_COLS = 7;
const ESTATE_ROWS = 5;

const ESTATE_RES = [
  { key: "laurels",  icon: "🌿", label: "Laurels" },
  { key: "grain",    icon: "🌾", label: "Grain" },
  { key: "grapes",   icon: "🍇", label: "Grapes" },
  { key: "olives",   icon: "🫒", label: "Olives" },
  { key: "honey",    icon: "🍯", label: "Honey" },
  { key: "herbs",    icon: "🌱", label: "Herbs" },
];

const FARM_ICON = {
  grain_field: "🌾", vineyard: "🍇", olive_grove: "🫒",
  apiary: "🍯", herb_garden: "🌱",
};
const FARM_COLOR = {
  grain_field: "#7a5c10", vineyard: "#4b2a72", olive_grove: "#1a4a2a",
  apiary: "#7a4a00", herb_garden: "#0f4030", empty: "#0f1e2e",
};

let estateState = null;
let estateLog   = [];  // [{text, type, time}]  newest first

async function initEstate() {
  try {
    estateState = await api("/api/estate/state");
    renderEstateResources();
    renderEstateGridInteractive();
    // Load all estate sub-systems in parallel
    await Promise.allSettled([
      initSanctuary(),
      initRelics(),
      initArmy(),
      initVilla(),
      initProcessing(),
      initBlessings(),
      initAgora(),
      api("/api/estate/prophecy").then(scroll => {
        const previewEl = document.getElementById("prophecy-combined-preview");
        if (previewEl) previewEl.textContent = scroll.combined_title || "Unnamed Mortal";
      }),
    ]);
  } catch (e) {
    console.error("Estate init failed:", e);
  }
}

function renderEstateResources() {
  const el = document.getElementById("estate-resources");
  if (!el || !estateState) return;
  const formatted = (estateState.drachmae ?? 0).toFixed(2);
  const drachEl = document.getElementById("estate-drachma-pill");
  if (drachEl) drachEl.textContent = `🪙 ${formatted}`;
  // Keep top-banner drachma in sync (estate is the single source of truth)
  const bannerDrachEl = document.getElementById("drachma");
  if (bannerDrachEl) bannerDrachEl.textContent = formatted;
  // Keep top banner laurel count in sync
  const laurelCountEl = document.getElementById("laurel-count");
  if (laurelCountEl) laurelCountEl.textContent = estateState.laurels ?? 0;
  el.innerHTML = ESTATE_RES.map(r => {
    const val = estateState[r.key] ?? 0;
    return `<div class="estate-res-pill">
      <span class="estate-res-icon">${r.icon}</span>
      <span class="estate-res-val">${val}</span>
      <span class="estate-res-lbl">${r.label}</span>
    </div>`;
  }).join("");
}

function renderEstateGrid() {
  const el = document.getElementById("estate-grid");
  if (!el || !estateState) return;
  const farmMap = {};
  (estateState.farms || []).forEach(f => { farmMap[`${f.col},${f.row}`] = f; });
  let html = '<div class="estate-grid-inner">';
  for (let row = 0; row < ESTATE_ROWS; row++) {
    for (let col = 0; col < ESTATE_COLS; col++) {
      const farm  = farmMap[`${col},${row}`];
      const type  = farm ? farm.farm_type : "empty";
      const icon  = farm ? (FARM_ICON[type] || "🟩") : "";
      const lvl   = farm ? `L${farm.level || 1}` : "";
      const bg    = FARM_COLOR[type] || FARM_COLOR.empty;
      html += `<div class="estate-tile" style="background:${bg}" title="${type}">
        <span class="estate-tile-icon">${icon}</span>
        <span class="estate-tile-lvl">${lvl}</span>
      </div>`;
    }
  }
  html += "</div>";
  el.innerHTML = html;
}

function pushEstateLog(text, type = "system") {
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  estateLog.unshift({ text, type, time });
  if (estateLog.length > 60) estateLog.pop();
  renderEstateLog();
}

function renderEstateLog() {
  const el = document.getElementById("estate-event-log");
  if (!el) return;
  if (!estateLog.length) {
    el.innerHTML = '<p class="dim-msg">Log a workout to see events.</p>';
    return;
  }
  const COLOR = { reward: "var(--gold)", farm: "var(--success)", system: "var(--accent)" };
  el.innerHTML = estateLog.map(e =>
    `<div class="estate-log-row" style="color:${COLOR[e.type] || COLOR.system}">
      <span class="estate-log-time">${e.time}</span>
      <span>${escHtml(e.text)}</span>
    </div>`
  ).join("");
}

// ── Estate Event Popup ────────────────────────────────────────────────────────

const EVENT_TYPE_LABELS = {
  oracle:      "oracle",
  creature:    "encounter",
  merchant:    "merchant",
  philosopher: "philosophy",
  rare:        "rare event",
};

function showEventPopup(event) {
  if (!event) return;

  document.getElementById("event-icon").textContent       = event.icon  || "✨";
  document.getElementById("event-title").textContent      = event.title || "Something happens…";
  document.getElementById("event-type-badge").textContent = EVENT_TYPE_LABELS[event.type] || event.type;

  const linesEl = document.getElementById("event-lines");
  linesEl.innerHTML = (event.lines || [])
    .map(l => `<p class="event-line">${escHtml(l)}</p>`)
    .join("");

  const cardEl = document.getElementById("event-creature-card");
  if (event.creature) {
    document.getElementById("event-creature-rarity").textContent = event.creature.rarity;
    document.getElementById("event-creature-name").textContent   = event.creature.name;
    cardEl.hidden = false;
  } else {
    cardEl.hidden = true;
  }

  const overlay = document.getElementById("event-overlay");
  overlay.hidden = false;
  document.getElementById("event-dismiss-btn").focus();
}

function hideEventPopup() {
  document.getElementById("event-overlay").hidden = true;
}

// Show a temporary trophy award banner in the estate log area
function showTrophyAwardBanner(trophy) {
  const RARITY_COLOURS = {
    common:    "#a0a0a0",
    uncommon:  "#4fc35a",
    rare:      "#4a9eff",
    epic:      "#b44aff",
    legendary: "#ffd700",
  };
  const colour  = RARITY_COLOURS[trophy.rarity] || "#a0a0a0";
  const rarity  = (trophy.rarity || "").replace(/^./, c => c.toUpperCase());
  const buffLbl = trophy.buff_label || trophy.buff_type || "";

  const banner = document.createElement("div");
  banner.className = "trophy-award-banner";
  banner.innerHTML = `
    <div class="trophy-award-emoji">${trophy.emoji || "🏆"}</div>
    <div class="trophy-award-info">
      <div class="trophy-award-name">⚔️ Monster Slain! ${escHtml(trophy.name)}</div>
      <div class="trophy-award-buff">${escHtml(buffLbl)}</div>
      <div class="trophy-award-rarity" style="color:${colour}">${escHtml(rarity)}</div>
    </div>`;

  // Insert at top of estate log, or after estate resources
  const logEl = document.getElementById("estate-log");
  if (logEl) {
    logEl.prepend(banner);
  } else {
    const resEl = document.querySelector(".estate-resources, #estate-resources");
    if (resEl) resEl.after(banner);
  }
  // Auto-remove after 8s
  setTimeout(() => banner.remove(), 8000);
}

document.getElementById("event-dismiss-btn").addEventListener("click", hideEventPopup);
document.getElementById("event-overlay").addEventListener("click", e => {
  if (e.target === e.currentTarget) hideEventPopup();
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") hideEventPopup();
});

document.getElementById("simulate-workout-btn")?.addEventListener("click", async () => {
  const btn  = document.getElementById("simulate-workout-btn");
  const type = document.getElementById("estate-workout-type")?.value || "strength";
  btn.disabled = true;
  try {
    const res = await api("/api/estate/simulate-workout", { workout_type: type });
    estateState = res.state;
    renderEstateResources();
    renderEstateGridInteractive();
    (res.events || []).forEach(evt => {
      const t = evt.includes("Farm") || evt.includes("harvest") ? "farm"
              : evt.includes("drachma") || evt.includes("LAUREL")  ? "reward"
              : "system";
      pushEstateLog(evt, t);
    });
    toast(`⚔️ ${res.events?.[0] || "Workout logged!"}`);
    // Refresh sub-systems that may have changed
    initSanctuary();
    initBlessings();
    // Show relic find notification if one was discovered
    if (res.relic_find) {
      const r = res.relic_find;
      pushEstateLog(`⚗️ Relic found: ${r.name} (${r.rarity})!`, "reward");
      await initRelics();
    }
    // Show trophy award notification if a microcycle was completed
    if (res.trophy_award) {
      const t = res.trophy_award;
      pushEstateLog(`⚔️ Trophy earned: ${t.emoji} ${t.name} — ${t.buff_label || ""}`, "reward");
      showTrophyAwardBanner(t);
      // Refresh vault trophy list + buff summary
      renderVaultSection(appState || {});
    }
    // Show creature encounter first (player must decide before narrative event)
    if (res.creature_encounter) {
      showEncounterDialog(res.creature_encounter);
    } else if (res.event) {
      showEventPopup(res.event);
    }
    // Check barracks requirements after each workout (laurels/farms may have changed)
    if (!estateState?.barracks_built) {
      api("/api/estate/army").then(armyData => {
        renderBarracksRequirements({ state: estateState });
      }).catch(() => {});
    }
  } catch (e) {
    toast("Estate error: " + e.message, 4000);
  } finally {
    btn.disabled = false;
  }
});

// ══════════════════════════════════════════════════════════════════════════════
// SANCTUARY + RELICS
// ══════════════════════════════════════════════════════════════════════════════

const RARITY_ICONS = {
  common:    "🌿",
  rare:      "⚡",
  epic:      "🔥",
  legendary: "✨",
};

const RARITY_COLORS = {
  common:    "var(--success)",
  rare:      "var(--accent)",
  epic:      "#e06c1a",
  legendary: "var(--gold)",
};

// ── Sanctuary ─────────────────────────────────────────────────────────────────

async function initSanctuary() {
  try {
    const data = await api("/api/estate/sanctuary");
    renderSanctuary(data);
  } catch (e) {
    console.error("Sanctuary init failed:", e);
  }
}

function renderSanctuary(data) {
  const listEl  = document.getElementById("sanctuary-list");
  const countEl = document.getElementById("sanctuary-count");
  if (!listEl) return;

  const creatures = data.sanctuary || [];
  const capacity  = data.capacity  || 3;
  if (countEl) countEl.textContent = `${creatures.length} / ${capacity}`;

  if (!creatures.length) {
    listEl.innerHTML = '<p class="dim-msg">No creatures recruited yet. Complete outdoor workouts to encounter them.</p>';
    return;
  }

  listEl.innerHTML = creatures.map(c => {
    const rarityColor = RARITY_COLORS[c.rarity] || "var(--text)";
    const icon        = c.icon || RARITY_ICONS[c.rarity] || "🐾";
    return `<div class="creature-card">
      <div class="creature-card-icon" style="color:${rarityColor}">${icon}</div>
      <div class="creature-card-info">
        <div class="creature-card-name">${escHtml(c.name)}</div>
        <div class="creature-card-buff">✨ ${escHtml(c.buff_label || "Passive buff")}</div>
        <div class="creature-card-flavor">${escHtml(c.flavor || "")}</div>
      </div>
      <button class="btn-ghost-sm creature-release-btn"
              data-id="${escHtml(c.id)}"
              data-name="${escHtml(c.name)}"
              data-reward="${c.release_reward || 5}"
              title="Release — earn ${c.release_reward || 5} 🪙">
        ⚡ Release
      </button>
    </div>`;
  }).join("");

  // Release handlers
  listEl.querySelectorAll(".creature-release-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const cid    = btn.dataset.id;
      const name   = btn.dataset.name;
      const reward = btn.dataset.reward;
      btn.disabled = true;
      try {
        const res = await api("/api/estate/creature/release", { creature_id: cid });
        estateState = res.state;
        renderEstateResources();
        toast(`${name} released — +${reward} 🪙`);
        await initSanctuary();
      } catch (e) {
        toast("Release failed: " + e.message, 4000);
        btn.disabled = false;
      }
    });
  });
}

// ── Relic Inventory ───────────────────────────────────────────────────────────

async function initRelics() {
  try {
    const data = await api("/api/estate/relics");
    renderRelics(data);
  } catch (e) {
    console.error("Relics init failed:", e);
  }
}

function renderRelics(data) {
  const listEl  = document.getElementById("relics-list");
  const countEl = document.getElementById("relics-count");
  if (!listEl) return;

  const relics   = data.inventory || [];
  const capacity = data.capacity  || 10;
  if (countEl) countEl.textContent = `${relics.length} / ${capacity}`;

  if (!relics.length) {
    listEl.innerHTML = '<p class="dim-msg">No relics acquired yet. They are found through events and campaigns.</p>';
    return;
  }

  listEl.innerHTML = relics.map(r => {
    const rarityColor = RARITY_COLORS[r.rarity] || "var(--text)";
    const icon        = r.icon || "🔮";
    return `<div class="relic-card">
      <div class="relic-card-icon" style="color:${rarityColor}">${icon}</div>
      <div class="relic-card-info">
        <div class="relic-card-name">${escHtml(r.name)}</div>
        <div class="relic-card-buff">✨ ${escHtml(r.buff_label || "Passive buff")}</div>
        <div class="relic-card-flavor">${escHtml(r.flavor || "")}</div>
      </div>
    </div>`;
  }).join("");
}

// ── Creature Encounter Dialog ─────────────────────────────────────────────────

let _pendingEncounter = null;

function showEncounterDialog(creature) {
  if (!creature) return;
  _pendingEncounter = creature;

  const rarity      = creature.rarity || "common";
  const rarityColor = RARITY_COLORS[rarity] || "var(--text)";

  document.getElementById("encounter-rarity-badge").textContent        = rarity;
  document.getElementById("encounter-rarity-badge").style.color        = rarityColor;
  document.getElementById("encounter-rarity-badge").style.borderColor  = rarityColor;
  document.getElementById("encounter-icon").textContent                = creature.icon || RARITY_ICONS[rarity] || "🐾";
  document.getElementById("encounter-creature-name").textContent       = creature.name || "A Creature";
  document.getElementById("encounter-description").textContent         = creature.description || "";
  document.getElementById("encounter-buff-label").textContent          = creature.buff_label || "Passive buff";
  document.getElementById("encounter-flavor").textContent              = creature.flavor ? `"${creature.flavor}"` : "";
  document.getElementById("encounter-release-reward").textContent      = `(+${creature.release_reward || 5} 🪙)`;

  const recruitBtn = document.getElementById("encounter-recruit-btn");
  // Disable recruit if sanctuary is full (check estateState)
  if (estateState) {
    const sanctuary = estateState.sanctuary || [];
    const cap       = estateState.sanctuary_capacity || 3;
    if (sanctuary.length >= cap) {
      recruitBtn.disabled = true;
      recruitBtn.title    = "Sanctuary is full";
    } else {
      recruitBtn.disabled = false;
      recruitBtn.title    = "";
    }
  }

  document.getElementById("encounter-overlay").hidden = false;
  recruitBtn.focus();
}

function hideEncounterDialog() {
  document.getElementById("encounter-overlay").hidden = true;
  _pendingEncounter = null;
}

document.getElementById("encounter-recruit-btn")?.addEventListener("click", async () => {
  if (!_pendingEncounter) return;
  const btn = document.getElementById("encounter-recruit-btn");
  btn.disabled = true;
  try {
    const res = await api("/api/estate/creature/recruit", { creature_id: _pendingEncounter.id });
    estateState = res.state;
    renderEstateResources();
    toast(`🏛️ ${_pendingEncounter.name} welcomed into the sanctuary!`);
    hideEncounterDialog();
    await initSanctuary();
  } catch (e) {
    toast(e.message, 4000);
    btn.disabled = false;
  }
});

document.getElementById("encounter-release-btn")?.addEventListener("click", async () => {
  if (!_pendingEncounter) return;
  // Creature was encountered but not yet recruited — award release reward
  const reward = _pendingEncounter.release_reward || 5;
  try {
    // Add temporarily then release so the server awards coins cleanly
    await api("/api/estate/creature/recruit",  { creature_id: _pendingEncounter.id }).catch(() => {});
    const res = await api("/api/estate/creature/release", { creature_id: _pendingEncounter.id });
    if (res?.state) {
      estateState = res.state;
      renderEstateResources();
    }
  } catch (_) { /* non-fatal — coins already logged */ }
  toast(`⚡ ${_pendingEncounter.name} released — +${reward} 🪙`);
  hideEncounterDialog();
});

document.getElementById("encounter-skip-btn")?.addEventListener("click", hideEncounterDialog);
document.getElementById("encounter-overlay")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) hideEncounterDialog();
});

// ══════════════════════════════════════════════════════════════════════════════
// PROPHECY SCROLL
// ══════════════════════════════════════════════════════════════════════════════

const CATEGORY_ICONS = {
  consistency: "⏳",
  workout:     "⚔️",
  estate:      "🌾",
  legendary:   "✨",
  secret:      "🔒",
};

// Categories whose unearned titles are hidden (name + condition masked)
const HIDDEN_CATEGORIES = new Set(["legendary", "secret"]);

async function openProphecyScroll() {
  const overlay = document.getElementById("prophecy-overlay");
  overlay.hidden = false;
  document.getElementById("close-prophecy-btn").focus();

  // Show loading state
  document.getElementById("prophecy-dialog-title").textContent = "Loading…";
  document.getElementById("prophecy-categories").innerHTML =
    '<p class="dim-msg" style="padding:12px">Consulting the fates…</p>';

  try {
    const scroll = await api("/api/estate/prophecy");
    renderProphecyScroll(scroll);

    // Also update the estate state so laurels + titles reflect backend state
    if (estateState) {
      estateState.laurels         = scroll.laurels;
      estateState.oracle_phase    = scroll.oracle_phase;
      estateState.oracle_visits   = scroll.oracle_visits;
      estateState.titles_unlocked = (scroll.titles_by_category || [])
        .flatMap(c => c.titles.filter(t => t.unlocked).map(t => t.id));
      renderEstateResources();
    }

    // Update the preview chip in the estate card
    const previewEl = document.getElementById("prophecy-combined-preview");
    if (previewEl) previewEl.textContent = scroll.combined_title || "Unnamed Mortal";

  } catch (err) {
    toast("Prophecy error: " + err.message, 4000);
    overlay.hidden = true;
  }
}

function renderProphecyScroll(scroll) {
  // Title
  const combined = scroll.combined_title || "Unnamed Mortal";
  document.getElementById("prophecy-dialog-title").textContent = combined;

  // Oracle bar
  document.getElementById("prophecy-oracle-phase-name").textContent =
    scroll.oracle_phase_name || "Stranger";
  document.getElementById("prophecy-oracle-visits").textContent =
    `${scroll.oracle_visits || 0} visit${scroll.oracle_visits === 1 ? "" : "s"}`;

  // Laurels
  document.getElementById("prophecy-laurels").textContent = scroll.laurels ?? 0;

  // Categories
  const catsEl = document.getElementById("prophecy-categories");
  if (!scroll.titles_by_category || !scroll.titles_by_category.length) {
    catsEl.innerHTML = '<p class="dim-msg">No titles data.</p>';
    return;
  }

  catsEl.innerHTML = scroll.titles_by_category.map(cat => {
    const icon       = CATEGORY_ICONS[cat.category] || "📜";
    const unlockedN  = cat.titles.filter(t => t.unlocked).length;
    const total      = cat.titles.length;

    const isHiddenCat = HIDDEN_CATEGORIES.has(cat.category);

    const itemsHtml = cat.titles.map(t => {
      if (!t.unlocked && isHiddenCat) {
        // Mask unearned legendary / secret titles completely
        return `<li class="prophecy-title-item prophecy-title-hidden">
          <div class="prophecy-title-check"></div>
          <div class="prophecy-title-info">
            <span class="prophecy-title-name prophecy-title-redacted">??? Unknown Title</span>
            <span class="prophecy-title-condition prophecy-title-redacted">Complete hidden deeds to reveal</span>
          </div>
        </li>`;
      }
      const cls   = t.unlocked ? "prophecy-title-item unlocked" : "prophecy-title-item";
      const check = t.unlocked ? "✓" : "";
      return `<li class="${cls}">
        <div class="prophecy-title-check">${check}</div>
        <div class="prophecy-title-info">
          <span class="prophecy-title-name">${escHtml(t.name)}</span>
          <span class="prophecy-title-condition">${escHtml(t.condition)}</span>
        </div>
      </li>`;
    }).join("");

    // For hidden categories, only show unlocked count (not total — keep mysteries mysterious)
    const countLabel = isHiddenCat
      ? (unlockedN > 0 ? `${unlockedN} revealed` : "none revealed")
      : `${unlockedN} / ${total}`;

    return `<div class="prophecy-cat">
      <div class="prophecy-cat-header">
        <span class="prophecy-cat-name">${icon} ${escHtml(cat.label)}</span>
        <span class="prophecy-cat-count">${countLabel}</span>
      </div>
      <ul class="prophecy-title-list">${itemsHtml}</ul>
    </div>`;
  }).join("");
}

function closeProphecyScroll() {
  document.getElementById("prophecy-overlay").hidden = true;
}

// Prophecy scroll event listeners
document.getElementById("open-prophecy-btn")?.addEventListener("click", openProphecyScroll);
document.getElementById("close-prophecy-btn")?.addEventListener("click", closeProphecyScroll);
document.getElementById("cancel-prophecy-btn")?.addEventListener("click", closeProphecyScroll);
document.getElementById("prophecy-overlay")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) closeProphecyScroll();
});

// ══════════════════════════════════════════════════════════════════════════════
// ARMY + CAMPAIGN SYSTEMS
// ══════════════════════════════════════════════════════════════════════════════

const UNIT_ICONS = {
  hoplite:          "⚔️",
  archer:           "🏹",
  cavalry:          "🐴",
  myrmidon_captain: "🛡️",
};

// ── Army / Barracks ────────────────────────────────────────────────────────────

let _armyData = null;

async function initArmy() {
  try {
    _armyData = await api("/api/estate/army");
    renderArmy(_armyData);
  } catch (e) {
    console.error("Army init failed:", e);
  }
}

function renderArmy(data) {
  if (!data) return;

  const lockedEl  = document.getElementById("barracks-locked");
  const openEl    = document.getElementById("barracks-open");
  const pillEl    = document.getElementById("army-strength-pill");
  const countEl   = document.getElementById("army-count");
  const strEl     = document.getElementById("army-total-strength");
  const unitListEl = document.getElementById("army-unit-list");
  const recruitEl = document.getElementById("recruit-unit-list");
  const campaignsEl = document.getElementById("campaigns-won-preview");

  if (!lockedEl || !openEl) return;

  const built    = data.barracks_built;
  const units    = data.army          || [];
  const limit    = data.army_limit    || 10;
  const strength = data.army_strength || 0;
  const allUnits = data.all_units     || [];
  const won      = data.campaigns_won || 0;

  // Toggle barracks state
  lockedEl.hidden = built;
  openEl.hidden   = !built;

  if (pillEl) pillEl.textContent = `⚔️ ${strength} str`;
  if (campaignsEl) campaignsEl.textContent =
    won === 1 ? "1 victory" : `${won} victories`;

  if (!built) {
    // Show unlock requirements progress
    renderBarracksRequirements({ state: estateState });
    return;
  }

  if (countEl)  countEl.textContent  = `${units.length} / ${limit}`;
  if (strEl)    strEl.textContent    = strength;

  // Army unit list (collapsed by type)
  if (unitListEl) {
    if (!units.length) {
      unitListEl.innerHTML = '<p class="dim-msg">No soldiers recruited yet.</p>';
    } else {
      unitListEl.innerHTML = units.map(u => {
        const icon  = UNIT_ICONS[u.id] || "⚔️";
        const color = RARITY_COLORS[u.rarity] || "var(--text)";
        return `<div class="unit-card">
          <div class="unit-card-icon" style="color:${color}">${icon}</div>
          <div class="unit-card-info">
            <div class="unit-card-name">${escHtml(u.name)}
              <span class="unit-card-count">×${u.count}</span>
            </div>
            <div class="unit-card-stat">⚔️ ${u.total_strength} strength total</div>
            <div class="unit-card-flavor">${escHtml(u.description || "")}</div>
          </div>
          <button class="btn-ghost-sm unit-disband-btn"
                  data-id="${escHtml(u.id)}" data-name="${escHtml(u.name)}"
                  title="Disband one ${escHtml(u.name)}">
            Disband
          </button>
        </div>`;
      }).join("");

      // Disband handlers
      unitListEl.querySelectorAll(".unit-disband-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
          btn.disabled = true;
          try {
            const res = await api("/api/estate/army/disband", { unit_id: btn.dataset.id });
            estateState = res.state;
            renderEstateResources();
            toast(`${btn.dataset.name} disbanded.`);
            await initArmy();
          } catch (e) {
            toast("Disband failed: " + e.message, 4000);
            btn.disabled = false;
          }
        });
      });
    }
  }

  // Recruit panel
  if (recruitEl) {
    recruitEl.innerHTML = allUnits.map(u => {
      const icon  = UNIT_ICONS[u.id] || "⚔️";
      const color = RARITY_COLORS[u.rarity] || "var(--text)";
      return `<div class="recruit-card">
        <div class="recruit-card-icon" style="color:${color}">${icon}</div>
        <div class="recruit-card-info">
          <div class="recruit-card-name">${escHtml(u.name)}</div>
          <div class="recruit-card-stat">⚔️ ${u.strength} str</div>
          <div class="recruit-card-cost">${escHtml(u.cost_str)}</div>
        </div>
        <button class="btn-outline-sm recruit-unit-btn"
                data-id="${escHtml(u.id)}" data-name="${escHtml(u.name)}">
          +1
        </button>
      </div>`;
    }).join("");

    recruitEl.querySelectorAll(".recruit-unit-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const res = await api("/api/estate/army/recruit", { unit_id: btn.dataset.id });
          estateState = res.state;
          renderEstateResources();
          toast(`⚔️ ${btn.dataset.name} recruited!`);
          await initArmy();
        } catch (e) {
          toast(e.message, 4000);
          btn.disabled = false;
        }
      });
    });
  }
}

document.getElementById("build-barracks-btn")?.addEventListener("click", async () => {
  const btn = document.getElementById("build-barracks-btn");
  btn.disabled = true;
  try {
    const res = await api("/api/estate/barracks/build", {});
    estateState = res.state;
    renderEstateResources();
    toast("🏰 Barracks constructed! Soldiers may now be recruited.");
    await initArmy();
  } catch (e) {
    toast(e.message, 4000);
    btn.disabled = false;
  }
});

// ── Campaign Map ───────────────────────────────────────────────────────────────

async function openCampaignMap() {
  document.getElementById("campaign-overlay").hidden = false;
  document.getElementById("close-campaign-btn").focus();

  const listEl  = document.getElementById("campaign-region-list");
  const strengthEl = document.getElementById("campaign-army-strength-display");

  listEl.innerHTML = '<p class="dim-msg">Loading regions…</p>';
  try {
    const data = await api("/api/estate/army");
    _armyData  = data;
    const strength = data.army_strength || 0;
    if (strengthEl) strengthEl.textContent = strength;
    renderCampaignMap(data);
  } catch (e) {
    listEl.innerHTML = `<p class="dim-msg">Error: ${escHtml(e.message)}</p>`;
  }
}

function renderCampaignMap(data) {
  const listEl = document.getElementById("campaign-region-list");
  if (!listEl) return;

  const regions  = data.all_regions || [];
  const strength = data.army_strength || 0;

  if (!regions.length) {
    listEl.innerHTML = '<p class="dim-msg">No regions available.</p>';
    return;
  }

  listEl.innerHTML = regions.map(r => {
    const canWin   = strength > r.difficulty;
    const stateClass = canWin ? "region-card region-winnable" : "region-card region-tough";
    const indicator  = canWin ? "✅" : "⚠️";
    return `<div class="${stateClass}">
      <div class="region-card-header">
        <div class="region-card-info">
          <div class="region-card-name">${escHtml(r.name)}</div>
          <div class="region-card-desc">${escHtml(r.description)}</div>
        </div>
        <div class="region-card-difficulty">
          <span class="region-diff-label">Difficulty</span>
          <span class="region-diff-val">${r.difficulty}</span>
          <span class="region-diff-indicator">${indicator}</span>
        </div>
      </div>
      <div class="region-card-rewards">
        <span>🪙 ${r.reward_drachmae[0]}–${r.reward_drachmae[1]}</span>
        <span title="Relic chance">⚗️ ${Math.round(r.relic_chance * 100)}%</span>
        <span title="Creature chance">🐾 ${Math.round(r.creature_chance * 100)}%</span>
      </div>
      <button class="btn-primary launch-campaign-btn"
              data-id="${escHtml(r.id)}" data-name="${escHtml(r.name)}">
        ⚔️ Launch Campaign
      </button>
    </div>`;
  }).join("");

  listEl.querySelectorAll(".launch-campaign-btn").forEach(btn => {
    btn.addEventListener("click", () => launchCampaign(btn.dataset.id, btn.dataset.name));
  });
}

function closeCampaignMap() {
  document.getElementById("campaign-overlay").hidden = true;
}

async function launchCampaign(regionId, regionName) {
  const btn = document.querySelector(`.launch-campaign-btn[data-id="${regionId}"]`);
  if (btn) btn.disabled = true;
  try {
    const res = await api("/api/estate/campaign/launch", { region_id: regionId });
    estateState = res.state;
    renderEstateResources();

    const result = res.result;

    // Log campaign outcome to estate log
    const logType = result.victory ? "reward" : "system";
    pushEstateLog(
      result.victory
        ? `⚔️ Victory at ${result.region_name}! +${result.drachmae_earned?.toFixed(0)} 🪙`
        : `💀 Defeat at ${result.region_name}. Units lost: ${result.units_lost?.join(", ")}`,
      logType
    );

    if (result.title_unlocked) {
      pushEstateLog(`🏅 Title unlocked: ${result.title_unlocked}`, "reward");
      toast(`🏅 ${result.title_unlocked} — legendary title earned!`, 5000);
    }

    // Update army display + campaign count
    await initArmy();

    // Add relic feedback to result lines if it was auto-added
    if (result.relic_reward && !result.relic_reward.not_added) {
      await initRelics();
    }

    // Close campaign map first, then show result popup
    closeCampaignMap();

    // Show campaign result in event popup
    showEventPopup({
      type:  "campaign",
      icon:  result.icon,
      title: result.title,
      lines: result.lines,
    });

    // Show creature encounter dialog if creature found
    if (res.creature_encounter) {
      // Queue encounter after event popup is dismissed
      const origDismiss = document.getElementById("event-dismiss-btn").onclick;
      document.getElementById("event-dismiss-btn").addEventListener("click", function onDismiss() {
        document.getElementById("event-dismiss-btn").removeEventListener("click", onDismiss);
        showEncounterDialog(res.creature_encounter);
      }, { once: true });
    }

  } catch (e) {
    toast("Campaign failed: " + e.message, 4000);
    if (btn) btn.disabled = false;
  }
}

// Campaign dialog event listeners
document.getElementById("open-campaign-map-btn")?.addEventListener("click", openCampaignMap);
document.getElementById("close-campaign-btn")?.addEventListener("click", closeCampaignMap);
document.getElementById("cancel-campaign-btn")?.addEventListener("click", closeCampaignMap);
document.getElementById("campaign-overlay")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) closeCampaignMap();
});

// ── Extend EVENT_TYPE_LABELS for campaign ─────────────────────────────────────
EVENT_TYPE_LABELS["campaign"] = "campaign";

// ══════════════════════════════════════════════════════════════════════════════
// VILLA SYSTEM
// ══════════════════════════════════════════════════════════════════════════════

async function initVilla() {
  try {
    const data = await api("/api/estate/villa");
    renderVilla(data);
  } catch (e) {
    console.error("Villa init failed:", e);
  }
}

function renderVilla(data) {
  const bodyEl  = document.getElementById("villa-body");
  const chipEl  = document.getElementById("villa-level-chip");
  if (!bodyEl) return;

  const level      = data.villa_level || 1;
  const maxLevel   = data.max_level   || 3;
  const canUpgrade = level < maxLevel;  // computed — no explicit field
  const cost       = data.upgrade_cost || {};
  const armyLimit  = data.army_limit   || ({ 1: 10, 2: 20, 3: 30 }[level] || 10);

  if (chipEl) chipEl.textContent = `Level ${level}`;

  // Also update barracks requirements if the backend returned them
  if (data.barracks_unlock) {
    _renderBarracksRequirementsFromUnlock(data.barracks_unlock);
  }

  if (!canUpgrade) {
    bodyEl.innerHTML = `
      <div class="villa-status-row">
        <span class="villa-level-badge">🏛️ Level ${level}</span>
        <span class="sub-text">${level >= maxLevel ? "Fully upgraded" : ""}</span>
      </div>
      <p class="sub-text" style="margin-top:6px">Army capacity: ${armyLimit} units</p>`;
    return;
  }

  const RESOURCE_ICONS = { drachmae: "🪙", grain: "🌾", wine: "🍷", olives: "🫒", honey: "🍯" };
  const costParts = Object.entries(cost)
    .map(([k, v]) => `${RESOURCE_ICONS[k] || ""} ${v} ${k === "drachmae" ? "" : k}`.trim())
    .join(" · ");

  bodyEl.innerHTML = `
    <div class="villa-status-row">
      <span class="villa-level-badge">🏛️ Level ${level}</span>
      <span class="sub-text">Army capacity: ${armyLimit} units</span>
    </div>
    <div class="barracks-cost-row" style="margin-top:8px">
      <span class="barracks-cost-label">Upgrade to Level ${level + 1}:</span>
      <span class="barracks-cost-resources">${escHtml(costParts)}</span>
    </div>
    <button class="btn-primary" id="upgrade-villa-btn" style="margin-top:10px;width:100%">
      🏛️ Upgrade Villa → Level ${level + 1}
    </button>`;

  document.getElementById("upgrade-villa-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("upgrade-villa-btn");
    btn.disabled = true;
    try {
      const res = await api("/api/estate/villa/upgrade", {});
      estateState = res.state;
      renderEstateResources();
      toast(`🏛️ Villa upgraded to Level ${res.state.villa_level}!`);
      await Promise.allSettled([initVilla(), initArmy()]);
    } catch (e) {
      toast(e.message, 4000);
      btn.disabled = false;
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// PROCESSING BUILDINGS
// ══════════════════════════════════════════════════════════════════════════════

const PROCESSING_ICONS = {
  winery:      "🍷",
  bakery:      "🍞",
  olive_press: "🫒",
  meadery:     "🍯",
};

async function initProcessing() {
  try {
    const data = await api("/api/estate/processing");
    renderProcessing(data);
  } catch (e) {
    console.error("Processing init failed:", e);
  }
}

function renderProcessing(data) {
  // endpoint returns { buildings: [...], state: {...} } or bare array
  const buildings = Array.isArray(data) ? data : (data.buildings || []);
  const listEl = document.getElementById("processing-list");
  if (!listEl) return;

  if (!buildings.length) {
    listEl.innerHTML = '<p class="dim-msg">No processing buildings available.</p>';
    return;
  }

  listEl.innerHTML = buildings.map(b => {
    const icon       = PROCESSING_ICONS[b.id] || "⚗️";
    const costParts  = Object.entries(b.build_cost || {})
      .map(([k, v]) => `${k === "drachmae" ? "🪙" : "🌾"} ${v} ${k === "drachmae" ? "" : k}`.trim())
      .join(" · ");

    if (!b.built) {
      return `<div class="processing-card">
        <div class="processing-card-icon">${icon}</div>
        <div class="processing-card-info">
          <div class="processing-card-name">${escHtml(b.name)}</div>
          <div class="processing-card-desc">${escHtml(b.description || "")}</div>
          <div class="processing-card-cost sub-text">Cost: ${escHtml(costParts)}</div>
        </div>
        <button class="btn-outline-sm build-processing-btn"
                data-id="${escHtml(b.id)}" data-name="${escHtml(b.name)}"
                ${b.can_afford ? "" : "disabled"}>
          Build
        </button>
      </div>`;
    }

    // Built — show process control
    const inputIcon  = { grapes: "🍇", grain: "🌾", olives: "🫒", honey: "🍯" }[b.input] || "📦";
    const outputIcon = { wine: "🍷", bread: "🍞", olive_oil: "🫒", mead: "🍯" }[b.output] || "📦";
    const maxBatch   = Math.max(1, Math.floor((b.input_held || 0) / (b.ratio || 2)));

    return `<div class="processing-card processing-card-built">
      <div class="processing-card-icon">${icon}</div>
      <div class="processing-card-info">
        <div class="processing-card-name">${escHtml(b.name)}</div>
        <div class="processing-card-desc">
          ${inputIcon} ${b.input_held || 0} ${escHtml(b.input)}
          → ${outputIcon} ${escHtml(b.output)} (${b.ratio || 2}:1)
          · You have ${b.output_held || 0} ${escHtml(b.output)}
        </div>
      </div>
      <div class="processing-card-actions">
        <input type="number" class="processing-amount-input" min="1" max="${maxBatch}"
               value="1" style="width:52px" data-id="${escHtml(b.id)}">
        <button class="btn-outline-sm process-goods-btn"
                data-id="${escHtml(b.id)}" data-name="${escHtml(b.name)}"
                data-input="${escHtml(b.input)}" data-output="${escHtml(b.output)}"
                ${maxBatch >= 1 ? "" : "disabled"}>
          Process
        </button>
      </div>
    </div>`;
  }).join("");

  // Build handlers
  listEl.querySelectorAll(".build-processing-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const res = await api("/api/estate/processing/build", { building_id: btn.dataset.id });
        // Issue 2: check for server-side error
        if (res.status === "error") {
          toast("⚠ " + (res.message || "Insufficient drachmae — better go train."), 4000);
          btn.disabled = false;
          return;
        }
        estateState = res.state;
        renderEstateResources();
        toast(`${btn.dataset.name} built!`);
        await initProcessing();
      } catch (e) {
        toast(e.message, 4000);
        btn.disabled = false;
      }
    });
  });

  // Process handlers
  listEl.querySelectorAll(".process-goods-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const amtInput = listEl.querySelector(`.processing-amount-input[data-id="${btn.dataset.id}"]`);
      const amount   = parseInt(amtInput?.value || "1", 10) || 1;
      btn.disabled = true;
      try {
        const res = await api("/api/estate/processing/process",
          { building_id: btn.dataset.id, amount });
        estateState = res.state;
        renderEstateResources();
        const detail = res.result || {};
        toast(`⚗️ ${detail.output_produced || amount} ${btn.dataset.output} produced!`);
        await initProcessing();
      } catch (e) {
        toast(e.message, 4000);
        btn.disabled = false;
      }
    });
  });
  // Refresh Agora after processing state changes (new buildings may unlock products)
  if (_marketPrices) renderAgora();
}

// ══════════════════════════════════════════════════════════════════════════════
// BLESSINGS SYSTEM
// ══════════════════════════════════════════════════════════════════════════════

async function initBlessings() {
  try {
    const data = await api("/api/estate/blessings");
    renderBlessings(data);
  } catch (e) {
    console.error("Blessings init failed:", e);
  }
}

function renderBlessings(data) {
  const listEl  = document.getElementById("blessings-list");
  const chipEl  = document.getElementById("blessings-laurels-chip");
  if (!listEl) return;

  const blessings = data.blessings || [];
  const laurels   = data.laurels   || 0;

  if (chipEl) chipEl.textContent = `🌿 ${laurels} laurel${laurels === 1 ? "" : "s"}`;

  if (!blessings.length) {
    listEl.innerHTML = '<p class="dim-msg">No blessings available.</p>';
    return;
  }

  listEl.innerHTML = blessings.map(b => {
    // cost field may be cost_laurels or cost
    const cost       = b.cost_laurels ?? b.cost ?? 1;
    const remaining  = b.remaining ?? b.uses_remaining ?? 0;
    const isActive   = b.active || remaining > 0;
    const canAfford  = laurels >= cost;
    const activeTag  = isActive ? `<span class="blessing-active-tag">ACTIVE ×${remaining}</span>` : "";

    return `<div class="blessing-card ${isActive ? "blessing-card-active" : ""}">
      <div class="blessing-card-icon">${escHtml(b.icon || "⭐")}</div>
      <div class="blessing-card-info">
        <div class="blessing-card-name">${escHtml(b.name)} ${activeTag}</div>
        <div class="blessing-card-effect sub-text">${escHtml(b.effect)}</div>
        <div class="blessing-card-cost sub-text">Cost: 🌿 ${cost} laurel${cost === 1 ? "" : "s"}</div>
      </div>
      <button class="btn-outline-sm activate-blessing-btn"
              data-id="${escHtml(b.id)}" data-name="${escHtml(b.name)}"
              ${canAfford && !isActive ? "" : "disabled"}>
        ${isActive ? "Active" : "Invoke"}
      </button>
    </div>`;
  }).join("");

  listEl.querySelectorAll(".activate-blessing-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const res = await api("/api/estate/blessing/activate", { blessing_id: btn.dataset.id });
        estateState = res.state;
        renderEstateResources();
        toast(`🌟 ${btn.dataset.name} invoked!`);
        await initBlessings();
      } catch (e) {
        toast(e.message, 4000);
        btn.disabled = false;
      }
    });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// FARM BUILD / UPGRADE DIALOGS
// ══════════════════════════════════════════════════════════════════════════════

let _farmBuildCell = null;   // {col, row} for pending build
let _farmUpgradeCell = null; // {col, row, farm} for pending upgrade

function showFarmBuildDialog(col, row) {
  _farmBuildCell = { col, row };
  document.getElementById("farm-build-title").textContent    = `🌾 Build Farm (${col}, ${row})`;
  document.getElementById("farm-build-subtitle").textContent = "Choose what to plant on this plot.";
  document.getElementById("farm-type-list").innerHTML = '<p class="dim-msg">Loading farm types…</p>';
  document.getElementById("farm-build-overlay").hidden = false;

  api("/api/estate/farm-types").then(resp => {
    // endpoint returns { farm_types: [...] } or bare array
    const types  = Array.isArray(resp) ? resp : (resp.farm_types || []);
    const listEl = document.getElementById("farm-type-list");
    if (!listEl) return;
    listEl.innerHTML = types.map(t => {
      const icon = FARM_ICON[t.id] || t.icon || "🌾";
      // build_cost may be a plain number (from levels[0]) or object with drachmae key
      const buildCost = typeof t.build_cost === "number"
        ? t.build_cost
        : (t.levels?.[0]?.build_cost ?? t.build_cost?.drachmae ?? 0);
      const cost      = buildCost ? `🪙 ${buildCost}` : "Free";
      const canAfford = !estateState || (estateState.drachmae ?? 0) >= buildCost;
      const produces  = t.resource || t.produces || t.id;
      return `<div class="farm-type-card">
        <div class="farm-type-icon">${icon}</div>
        <div class="farm-type-info">
          <div class="farm-type-name">${escHtml(t.name)}</div>
          <div class="farm-type-produce sub-text">Produces: ${escHtml(produces)}</div>
          <div class="farm-type-cost sub-text">${escHtml(cost)}</div>
        </div>
        <button class="btn-outline-sm build-farm-type-btn"
                data-farm-type="${escHtml(t.id)}" data-name="${escHtml(t.name)}"
                data-cost="${buildCost}"
                ${canAfford ? "" : "disabled"}>
          Build
        </button>
      </div>`;
    }).join("");

    listEl.querySelectorAll(".build-farm-type-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!_farmBuildCell) return;
        btn.disabled = true;
        try {
          const res = await api("/api/estate/farm/build", {
            farm_type: btn.dataset.farmType,
            col: _farmBuildCell.col,
            row: _farmBuildCell.row,
          });
          if (res.status === "error") {
            const msg = (res.message || "").toLowerCase().includes("drachma") || (res.message || "").toLowerCase().includes("funds")
              ? "Insufficient drachmae — better go train."
              : (res.message || "Cannot build here.");
            toast(msg, 4000);
            btn.disabled = false;
            return;
          }
          estateState = res.state;
          renderEstateResources();
          renderEstateGridInteractive();
          toast(`🌾 ${btn.dataset.name} planted!`);
          hideFarmBuildDialog();
        } catch (e) {
          toast(e.message, 4000);
          btn.disabled = false;
        }
      });
    });
  }).catch(e => {
    document.getElementById("farm-type-list").innerHTML =
      `<p class="dim-msg">Error: ${escHtml(e.message)}</p>`;
  });
}

function hideFarmBuildDialog() {
  document.getElementById("farm-build-overlay").hidden = true;
  _farmBuildCell = null;
}

function showFarmUpgradeDialog(col, row, farm) {
  _farmUpgradeCell = { col, row, farm };
  const upgradeEl = document.getElementById("farm-upgrade-body");
  const icon      = FARM_ICON[farm.farm_type] || "🌾";
  const level     = farm.level || 1;
  const upgCost   = farm.upgrade_cost || { drachmae: 150 };
  const costStr   = Object.entries(upgCost)
    .map(([k, v]) => `${k === "drachmae" ? "🪙" : ""} ${v} ${k === "drachmae" ? "" : k}`.trim())
    .join(" · ");
  const canAfford = !estateState || (estateState.drachmae ?? 0) >= (upgCost.drachmae ?? 0);

  document.getElementById("farm-upgrade-title").textContent = `⬆️ Upgrade ${farm.farm_type?.replace("_", " ")}`;

  if (upgradeEl) {
    upgradeEl.innerHTML = level >= 3
      ? `<p class="sub-text">This farm is already at maximum level (3).</p>`
      : `<p class="sub-text">${icon} Level ${level} → Level ${level + 1}</p>
         <div class="barracks-cost-row" style="margin-top:8px">
           <span class="barracks-cost-label">Upgrade cost:</span>
           <span class="barracks-cost-resources">${escHtml(costStr)}</span>
         </div>`;
  }

  const confirmBtn = document.getElementById("confirm-farm-upgrade-btn");
  if (confirmBtn) confirmBtn.disabled = level >= 3 || !canAfford;

  document.getElementById("farm-upgrade-overlay").hidden = false;
}

function hideFarmUpgradeDialog() {
  document.getElementById("farm-upgrade-overlay").hidden = true;
  _farmUpgradeCell = null;
}

document.getElementById("confirm-farm-upgrade-btn")?.addEventListener("click", async () => {
  if (!_farmUpgradeCell) return;
  const btn = document.getElementById("confirm-farm-upgrade-btn");
  btn.disabled = true;
  try {
    const res = await api("/api/estate/farm/upgrade", {
      col: _farmUpgradeCell.col,
      row: _farmUpgradeCell.row,
    });
    // Issue 2: check for server-side error
    if (res.status === "error") {
      toast("⚠ " + (res.message || "Insufficient drachmae — better go train."), 4000);
      btn.disabled = false;
      return;
    }
    estateState = res.state;
    renderEstateResources();
    renderEstateGrid();
    toast(`⬆️ Farm upgraded to Level ${(_farmUpgradeCell.farm.level || 1) + 1}!`);
    hideFarmUpgradeDialog();
  } catch (e) {
    toast(e.message, 4000);
    btn.disabled = false;
  }
});

document.getElementById("close-farm-build-btn")?.addEventListener("click", hideFarmBuildDialog);
document.getElementById("cancel-farm-build-btn")?.addEventListener("click", hideFarmBuildDialog);
document.getElementById("farm-build-overlay")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) hideFarmBuildDialog();
});
document.getElementById("close-farm-upgrade-btn")?.addEventListener("click", hideFarmUpgradeDialog);
document.getElementById("cancel-farm-upgrade-btn")?.addEventListener("click", hideFarmUpgradeDialog);
document.getElementById("farm-upgrade-overlay")?.addEventListener("click", e => {
  if (e.target === e.currentTarget) hideFarmUpgradeDialog();
});

// ══════════════════════════════════════════════════════════════════════════════
// BARRACKS REQUIREMENTS DISPLAY
// ══════════════════════════════════════════════════════════════════════════════

// Called from renderVilla when villa data includes barracks_unlock object
function _renderBarracksRequirementsFromUnlock(unlock) {
  const el = document.getElementById("barracks-requirements");
  if (!el || !unlock) return;

  const reqs = [
    {
      label:   `Earn ${unlock.laurels_needed} laurels`,
      met:     unlock.laurels_have >= unlock.laurels_needed,
      current: `${unlock.laurels_have} / ${unlock.laurels_needed}`,
    },
    {
      label:   `Build ${unlock.farms_needed} farms`,
      met:     unlock.farms_have >= unlock.farms_needed,
      current: `${unlock.farms_have} / ${unlock.farms_needed}`,
    },
    {
      label:   `Villa Level ${unlock.villa_level_needed}`,
      met:     unlock.villa_have >= unlock.villa_level_needed,
      current: `Lv ${unlock.villa_have}`,
    },
  ];

  el.innerHTML = reqs.map(r =>
    `<div class="barracks-req-row ${r.met ? "req-met" : "req-unmet"}">
      <span class="barracks-req-icon">${r.met ? "✅" : "⬜"}</span>
      <span class="barracks-req-label">${escHtml(r.label)}</span>
      <span class="barracks-req-val">${escHtml(r.current)}</span>
    </div>`
  ).join("");
}

// Fallback version using estateState directly (called from renderArmy)
function renderBarracksRequirements(data) {
  // If villa data already provided richer unlock info, prefer that
  const el = document.getElementById("barracks-requirements");
  if (!el) return;

  const laurels    = estateState?.laurels       ?? 0;
  const farms      = estateState?.farms?.length ?? 0;
  const villaLevel = estateState?.villa_level   ?? 1;

  const reqs = [
    { label: "Earn 3 laurels", met: laurels    >= 3, current: `${laurels} / 3`    },
    { label: "Build 3 farms",  met: farms      >= 3, current: `${farms} / 3`      },
    { label: "Villa Level 2",  met: villaLevel >= 2, current: `Lv ${villaLevel}`  },
  ];

  el.innerHTML = reqs.map(r =>
    `<div class="barracks-req-row ${r.met ? "req-met" : "req-unmet"}">
      <span class="barracks-req-icon">${r.met ? "✅" : "⬜"}</span>
      <span class="barracks-req-label">${escHtml(r.label)}</span>
      <span class="barracks-req-val">${escHtml(r.current)}</span>
    </div>`
  ).join("");
}

// ══════════════════════════════════════════════════════════════════════════════
// ENHANCED ESTATE GRID (clickable tiles)
// ══════════════════════════════════════════════════════════════════════════════

function renderEstateGridInteractive() {
  const el = document.getElementById("estate-grid");
  if (!el || !estateState) return;
  const farmMap = {};
  (estateState.farms || []).forEach(f => { farmMap[`${f.col},${f.row}`] = f; });
  let html = '<div class="estate-grid-inner">';
  for (let row = 0; row < ESTATE_ROWS; row++) {
    for (let col = 0; col < ESTATE_COLS; col++) {
      const farm  = farmMap[`${col},${row}`];
      const type  = farm ? farm.farm_type : "empty";
      const icon  = farm ? (FARM_ICON[type] || "🟩") : "＋";
      const lvl   = farm ? `L${farm.level || 1}` : "";
      const bg    = FARM_COLOR[type] || FARM_COLOR.empty;
      const title = farm
        ? `${type.replace(/_/g, " ")} (Level ${farm.level || 1}) — click to upgrade`
        : "Empty plot — click to build";
      html += `<div class="estate-tile estate-tile-interactive"
                    style="background:${bg}"
                    title="${title}"
                    data-col="${col}" data-row="${row}"
                    data-farm-type="${farm ? type : ""}">
        <span class="estate-tile-icon">${icon}</span>
        <span class="estate-tile-lvl">${lvl}</span>
      </div>`;
    }
  }
  html += "</div>";
  el.innerHTML = html;

  // Attach click handlers
  el.querySelectorAll(".estate-tile-interactive").forEach(tile => {
    tile.addEventListener("click", () => {
      const col      = parseInt(tile.dataset.col, 10);
      const row      = parseInt(tile.dataset.row, 10);
      const farmType = tile.dataset.farmType;
      if (farmType) {
        // Occupied — upgrade dialog
        const farm = farmMap[`${col},${row}`];
        if (farm) showFarmUpgradeDialog(col, row, farm);
      } else {
        // Empty — build dialog
        showFarmBuildDialog(col, row);
      }
    });
  });
}

// ── Auth UI ───────────────────────────────────────────────────────────────────
function initAuth() {
  const overlay  = document.getElementById("auth-overlay");
  const form     = document.getElementById("auth-form");
  const errorEl  = document.getElementById("auth-error");
  const submitBtn= document.getElementById("auth-submit");
  const tabs     = document.querySelectorAll(".auth-tab");
  let mode = "login";

  // Toggle login / register
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      mode = tab.dataset.mode;
      tabs.forEach(t => t.classList.toggle("active", t.dataset.mode === mode));
      submitBtn.textContent = mode === "login" ? "Sign In" : "Create Account";
      document.getElementById("auth-password").autocomplete =
        mode === "login" ? "current-password" : "new-password";
      errorEl.hidden = true;
    });
  });

  // Submit
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    const username = document.getElementById("auth-username").value.trim();
    const password = document.getElementById("auth-password").value;
    submitBtn.disabled = true;
    submitBtn.textContent = mode === "login" ? "Signing in…" : "Creating…";
    try {
      const endpoint = mode === "login" ? "/login" : "/register";
      // Auth endpoints don't need token — call fetch directly
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const text = await r.text();
      let data = {};
      try { data = JSON.parse(text); } catch (_) {}
      if (!r.ok) throw new Error(data.detail || (r.status === 500 ? "Server error — check deployment logs" : "Request failed"));
      setAuth(data.token, data.username);
      hideAuthOverlay();
      refresh();
      initEstate();
      initCustomWorkSelector();
      loadHistory();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = mode === "login" ? "Sign In" : "Create Account";
    }
  });

  // Show overlay if not logged in
  if (!getToken()) {
    overlay.hidden = false;
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────
document.getElementById("logout-btn")?.addEventListener("click", () => {
  clearAuth();
  showAuthOverlay();
});

// ── Auto-reload on new deployment ─────────────────────────────────────────────
let _deployVersion = null;
(async function initVersionCheck() {
  try {
    const r = await fetch("/api/version");
    if (r.ok) _deployVersion = (await r.json()).version;
  } catch (_) {}
})();
setInterval(async () => {
  try {
    const r = await fetch("/api/version");
    if (!r.ok) return;
    const v = (await r.json()).version;
    if (_deployVersion && v !== _deployVersion) {
      // New deployment detected — reload to pick up fresh assets
      location.reload(true);
    }
  } catch (_) {}
}, 60_000);

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", () => {
  initAuth();
  initCardioTypeRow();
  if (getToken()) {
    refresh();
    initEstate();
    initCustomWorkSelector();
    loadHistory();
  }
});
