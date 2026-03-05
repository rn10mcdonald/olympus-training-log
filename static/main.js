/* ──────────────────────────────────────────────────────────────────────────
   Olympus Training Log – main.js  v7
   ────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────────
const TRIP_MILES      = 306;
const SESSIONS_NEEDED = 6;
const WEEK_TARGET     = 3;

// ── API helper ────────────────────────────────────────────────────────────────
async function api(url, data, method) {
  const m = method || (data !== undefined ? "POST" : "GET");
  const opts = m !== "GET"
    ? { method: m, headers: { "Content-Type": "application/json" },
        body: data !== undefined ? JSON.stringify(data) : undefined }
    : {};
  const r = await fetch(url, opts);
  if (!r.ok) {
    const text = await r.text();
    let msg = text;
    try { msg = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(msg || r.statusText);
  }
  return r.json();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
const toastEl = document.getElementById("toast");
let _toastTimer;
function toast(msg, ms = 3500) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toastEl.classList.remove("show"), ms);
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
  if (!lbs || lbs <= 0 || !stdKg) return BASE_WORKOUT_COINS;
  const kg    = lbs * 0.453592;
  const ratio = Math.min(Math.max(kg / stdKg, 0.5), 2.0);
  return Math.round(BASE_WORKOUT_COINS * ratio * 100) / 100;
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
  renderRuckSection(state);
  renderRunSection(state);
  renderWalkSection(state);
  renderVaultSection(state);
  renderHistory(state, historyFilter);
}

// ── Header ────────────────────────────────────────────────────────────────────
function renderHeader(state) {
  document.getElementById("drachma").textContent =
    (state.treasury || 0).toFixed(2);

  const today = new Date();
  const [yr, wk] = isoWeek(today);
  const weekKey = `(${yr}, ${wk})`;
  const wkCount = Math.min((state.week_log || {})[weekKey] || 0, WEEK_TARGET);
  document.getElementById("week-count").textContent = `${wkCount}/${WEEK_TARGET}`;
}

// ── Train section ─────────────────────────────────────────────────────────────
function renderTrainSection(state, workout) {
  renderWorkout(workout);
  const totalSessions = workout && workout.total_sessions ? workout.total_sessions : SESSIONS_NEEDED;
  renderCycleGrid(state, totalSessions);
}

// ── Cycle grid ────────────────────────────────────────────────────────────────
function getMondayOf(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

function fmtShort(d) {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function renderCycleGrid(state, totalSessions) {
  const el   = document.getElementById("cycle-grid");
  const mc   = state.microcycle || {};
  const n    = totalSessions || SESSIONS_NEEDED;
  const done = Math.min(mc.sessions_completed || 0, n);

  document.getElementById("cycle-fraction").textContent = `${done} / ${n}`;

  if (!mc.start_date) {
    el.innerHTML = `<p class="dim-msg">Select a track below to begin.</p>`;
    return;
  }

  const mon1 = getMondayOf(mc.start_date);
  const sun1 = new Date(mon1); sun1.setDate(sun1.getDate() + 6);
  const mon2 = new Date(mon1); mon2.setDate(mon2.getDate() + 7);
  const sun2 = new Date(mon2); sun2.setDate(sun2.getDate() + 6);

  const cycleLogs = (state.workouts || [])
    .filter(w => w.date >= mc.start_date)
    .slice(0, n);

  function sessionCell(idx) {
    const num = `S${idx + 1}`;
    if (idx < done) {
      const raw   = cycleLogs[idx]?.date || "";
      const label = raw ? fmtShort(new Date(raw + "T12:00:00")) : "done";
      return `<div class="cs cs-done" title="Session ${idx+1} — ${label}">
        <span class="cs-icon">✓</span>
        <span class="cs-num">${num}</span>
        <span class="cs-date">${label}</span>
      </div>`;
    }
    if (idx === done) {
      return `<div class="cs cs-next" title="Session ${idx+1} — up next">
        <span class="cs-icon">→</span>
        <span class="cs-num">${num}</span>
        <span class="cs-date">next</span>
      </div>`;
    }
    return `<div class="cs cs-upcoming" title="Session ${idx+1} — upcoming">
      <span class="cs-icon">○</span>
      <span class="cs-num">${num}</span>
    </div>`;
  }

  // Week 1 = sessions 0-2, Week 2 = sessions 3-5 (for 6-session cycles)
  // For custom cycles, split evenly: first half in wk1, second half in wk2
  const half    = Math.ceil(n / 2);
  const wk1Cells = Array.from({length: half}, (_, i) => sessionCell(i)).join("");
  const wk2Cells = Array.from({length: n - half}, (_, i) => sessionCell(half + i)).join("");

  el.innerHTML = `
    <div class="cycle-week">
      <div class="cycle-week-hdr">
        <span class="cw-label">Week 1</span>
        <span class="cw-range">${fmtShort(mon1)} – ${fmtShort(sun1)}</span>
      </div>
      <div class="cs-row">${wk1Cells}</div>
    </div>
    ${n > half ? `
    <div class="cycle-divider"></div>
    <div class="cycle-week">
      <div class="cycle-week-hdr">
        <span class="cw-label">Week 2</span>
        <span class="cw-range">${fmtShort(mon2)} – ${fmtShort(sun2)}</span>
      </div>
      <div class="cs-row">${wk2Cells}</div>
    </div>` : ""}`;
}

/** Compact weight input HTML for a given movement key. */
function weightInputHtml(key) {
  return `<input type="number" class="movement-weight-input"
                 data-key="${key}" placeholder="lbs"
                 step="1" min="0" max="999" inputmode="decimal">`;
}

function renderWorkout(w) {
  const el = document.getElementById("workout-display");

  if (!w || w.status === "no_track") {
    el.innerHTML = `<p class="dim-msg">No active track. Choose a track below and press <strong>Start</strong>.</p>`;
    return;
  }
  if (w.status === "cycle_complete") {
    el.innerHTML = `<p class="dim-msg">🏅 Cycle complete! Log a custom workout or start a new track below.</p>`;
    return;
  }

  currentStdKg = w.std_kg || 16;
  const stdLbs = Math.round(currentStdKg * 2.20462);

  const accessories = (w.accessory || []).map((a, i) => `
    <li>
      <span class="acc-text">${escHtml(a)}</span>
      ${weightInputHtml(`acc_${i}`)}
    </li>`).join("");

  el.innerHTML = `
    <div class="workout-track-name">${escHtml(w.track_name || "")}</div>
    <div class="workout-session-label">Session ${w.session_num} of ${w.total_sessions}</div>

    <div class="workout-main">
      <span class="workout-main-text">${escHtml(w.main)}</span>
      ${weightInputHtml("main")}
    </div>

    <div class="workout-accessories">
      <h4>Accessories</h4>
      <ul>${accessories}</ul>
    </div>

    <div class="workout-finisher">
      <div class="finisher-content">
        <span class="finisher-label">Finisher</span>
        ${escHtml(w.finisher)}
      </div>
      ${weightInputHtml("finisher")}
    </div>

    <div class="workout-coins-row">
      <span class="weight-std-hint">· std: ${stdLbs} lbs (${currentStdKg} kg)</span>
      <span class="weight-coins-preview" id="weight-coins-preview">🪙 ${BASE_WORKOUT_COINS.toFixed(2)}</span>
    </div>`;
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

// ── Ruck section ──────────────────────────────────────────────────────────────
function renderRuckSection(state) {
  const ruckMiles = state.total_ruck_miles  || 0;
  const runMiles  = state.total_run_miles   || 0;
  const walkMiles = state.total_walk_miles  || 0;
  const journey   = state.journey_miles     || 0;

  document.getElementById("total-ruck-miles").textContent = ruckMiles.toFixed(1) + " mi";
  document.getElementById("total-run-miles-ruck").textContent = runMiles.toFixed(1) + " mi";
  document.getElementById("total-walk-miles-ruck").textContent = walkMiles.toFixed(1) + " mi";

  const pct = Math.min((journey / TRIP_MILES) * 100, 100);
  document.getElementById("journey-bar").style.width = pct.toFixed(1) + "%";
  document.getElementById("journey-fraction").textContent =
    `${journey.toFixed(1)} / ${TRIP_MILES} mi`;

  const postcards = (state.badges || []).filter(b => b.type === "ruck_quest").reverse();
  document.getElementById("ruck-postcards").innerHTML =
    postcards.length
      ? postcards.map(b => postcardHtml(b)).join("")
      : `<p class="dim-msg">Ruck or run your first miles to unlock waypoints.</p>`;
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

// ── Run section ───────────────────────────────────────────────────────────────
function renderRunSection(state) {
  const runMiles = state.total_run_miles || 0;
  const journey  = state.journey_miles   || 0;

  const runDrachma = (state.run_log || [])
    .reduce((sum, r) => sum + (r.coins || 0), 0);

  document.getElementById("total-run-miles").textContent = runMiles.toFixed(1) + " mi";
  document.getElementById("run-drachma").textContent = "🪙 " + runDrachma.toFixed(2);

  const pct = Math.min((journey / TRIP_MILES) * 100, 100);
  document.getElementById("journey-bar-run").style.width = pct.toFixed(1) + "%";
  document.getElementById("journey-fraction-run").textContent =
    `${journey.toFixed(1)} / ${TRIP_MILES} mi`;

  const runs = [...(state.run_log || [])].reverse().slice(0, 5);
  document.getElementById("recent-runs").innerHTML = runs.length
    ? runs.map(r => `
        <div class="recent-run-item">
          <span class="run-miles-text">${r.distance_miles.toFixed(2)} mi</span>
          ${r.pace_min_per_mile
            ? `<span class="run-pace-text">${formatPace(r.pace_min_per_mile)}/mi</span>`
            : ""}
          <span class="run-date-text">${r.date || ""}</span>
        </div>`).join("")
    : `<p class="dim-msg">No runs logged yet.</p>`;
}

// ── Walk section ──────────────────────────────────────────────────────────────
function renderWalkSection(state) {
  const walkMiles = state.total_walk_miles || 0;
  const journey   = state.journey_miles    || 0;

  const walkDrachma = (state.walk_log || [])
    .reduce((sum, r) => sum + (r.coins || 0), 0);

  document.getElementById("total-walk-miles").textContent = walkMiles.toFixed(1) + " mi";
  document.getElementById("walk-drachma").textContent = "🪙 " + walkDrachma.toFixed(2);

  const pct = Math.min((journey / TRIP_MILES) * 100, 100);
  document.getElementById("journey-bar-walk").style.width = pct.toFixed(1) + "%";
  document.getElementById("journey-fraction-walk").textContent =
    `${journey.toFixed(1)} / ${TRIP_MILES} mi`;

  const walks = [...(state.walk_log || [])].reverse().slice(0, 5);
  document.getElementById("recent-walks").innerHTML = walks.length
    ? walks.map(w => `
        <div class="recent-run-item">
          <span class="run-miles-text">${w.distance_miles.toFixed(2)} mi</span>
          <span class="run-date-text">${w.date || ""}</span>
        </div>`).join("")
    : `<p class="dim-msg">No walks logged yet.</p>`;
}

// ── Vault section ─────────────────────────────────────────────────────────────
function renderVaultSection(state) {
  const badges    = state.badges || [];
  const trophies  = [...badges].filter(b => b.type === "monster").reverse();
  const laurels   = [...badges].filter(b => b.type === "laurel").reverse();
  const postcards = [...badges].filter(b => b.type === "ruck_quest").reverse();

  document.getElementById("trophies-list").innerHTML = trophies.length
    ? trophies.map(b => badgeCardHtml(b)).join("")
    : `<div class="empty-msg">Complete a 6-session cycle to earn your first trophy.</div>`;

  document.getElementById("laurels-list").innerHTML = laurels.length
    ? laurels.map(b => badgeCardHtml(b)).join("")
    : `<div class="empty-msg">Log 3 activities in a week to earn a Laurel.</div>`;

  document.getElementById("vault-postcards").innerHTML = postcards.length
    ? postcards.map(b => postcardHtml(b)).join("")
    : `<div class="empty-msg">Unlock waypoints by covering journey miles.</div>`;
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

// ── History ───────────────────────────────────────────────────────────────────
function renderHistory(state, filter) {
  const byDate = {};

  if (filter === "all" || filter === "lifting") {
    for (const w of state.workouts || []) {
      if (!w.date) continue;
      let detail = w.details || "";

      if (w.weights_lbs && Object.keys(w.weights_lbs).length > 0) {
        const order = ["main", "acc_0", "acc_1", "acc_2", "finisher"];
        const parts = order.map(k => w.weights_lbs[k]).filter(v => v && v > 0);
        if (parts.length) detail += ` · ${parts.join("/")} lbs`;
      } else if (w.weight_kg) {
        detail += ` · ${Math.round(w.weight_kg * 2.20462)} lbs`;
      }

      if (w.coins != null) detail += ` · 🪙 ${Number(w.coins).toFixed(2)}`;
      (byDate[w.date] = byDate[w.date] || [])
        .push({ kind: w.type === "recommended" ? "lifting" : "custom",
                detail, _filter: "lifting" });
    }
  }

  if (filter === "all" || filter === "ruck") {
    for (const r of state.ruck_log || []) {
      if (!r.date || typeof r.distance_miles !== "number") continue;
      (byDate[r.date] = byDate[r.date] || [])
        .push({ kind: "ruck",
                detail: `${r.distance_miles} mi @ ${r.weight_lbs} lb — 🪙 ${(r.coins || 0).toFixed(2)}`,
                _filter: "ruck" });
    }
  }

  if (filter === "all" || filter === "run") {
    for (const r of state.run_log || []) {
      if (!r.date || typeof r.distance_miles !== "number") continue;
      const pace = r.pace_min_per_mile ? ` @ ${formatPace(r.pace_min_per_mile)}/mi` : "";
      (byDate[r.date] = byDate[r.date] || [])
        .push({ kind: "run",
                detail: `${r.distance_miles} mi${pace} — 🪙 ${(r.coins || 0).toFixed(2)}`,
                _filter: "run" });
    }
  }

  if (filter === "all" || filter === "walk") {
    for (const r of state.walk_log || []) {
      if (!r.date || typeof r.distance_miles !== "number") continue;
      (byDate[r.date] = byDate[r.date] || [])
        .push({ kind: "walk",
                detail: `${r.distance_miles} mi — 🪙 ${(r.coins || 0).toFixed(2)}`,
                _filter: "walk" });
    }
  }

  const dates = Object.keys(byDate).sort().reverse();
  const el    = document.getElementById("history-list");

  if (!dates.length) {
    el.innerHTML = `<div class="empty-msg">No activity logged yet — get moving!</div>`;
    return;
  }

  el.innerHTML = dates.map(date => `
    <div class="history-group">
      <div class="history-date">${date}</div>
      ${byDate[date].map(e => `
        <div class="history-entry">
          <span class="history-kind">${escHtml(e.kind)}</span>
          <span class="history-detail">${escHtml(e.detail)}</span>
        </div>`).join("")}
    </div>`).join("");
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
  const weights = {};
  document.querySelectorAll("#workout-display .movement-weight-input").forEach(inp => {
    const v = parseFloat(inp.value || 0);
    if (v > 0) weights[inp.dataset.key] = v;
  });
  const payload = Object.keys(weights).length > 0 ? { weights_lbs: weights } : {};

  try {
    const r = await api("/api/workout/recommended", payload);
    toast(r.msg || "⚔️ Workout logged!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
  } catch (e) { toast("⚠ " + e.message); }
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

async function logRuck() {
  const miles  = parseFloat(document.getElementById("ruck-miles").value || 0);
  const pounds = parseFloat(document.getElementById("ruck-lbs").value  || 0);
  if (!miles || miles <= 0) { toast("Enter a valid distance."); return; }
  try {
    const r = await api("/api/ruck", { miles, pounds });
    toast(r.msg || "🎒 Ruck logged!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    document.getElementById("ruck-miles").value = "";
    const newPostcards = (appState.badges || []).filter(b => b.type === "ruck_quest");
    if (newPostcards.length > prevBadgeCount) switchSection("ruck");
    prevBadgeCount = (appState.badges || []).length;
  } catch (e) { toast("⚠ " + e.message); }
}

async function logWalk() {
  const miles = parseFloat(document.getElementById("walk-miles").value || 0);
  if (!miles || miles <= 0) { toast("Enter a valid distance."); return; }
  try {
    const r = await api("/api/walk", { miles });
    toast(r.msg || "🚶 Walk logged!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    document.getElementById("walk-miles").value = "";
    prevBadgeCount = (appState.badges || []).length;
  } catch (e) { toast("⚠ " + e.message); }
}

async function logRun() {
  const miles = parseFloat(document.getElementById("run-miles").value || 0);
  if (!miles || miles <= 0) { toast("Enter a valid distance."); return; }

  const paceStr = document.getElementById("run-pace").value.trim();
  const pace    = parsePace(paceStr);
  if (paceStr && pace === null) {
    toast("Invalid pace format. Use MM:SS (e.g. 8:30).");
    return;
  }

  try {
    const payload = { miles };
    if (pace !== null) payload.pace_min_per_mile = pace;
    const r = await api("/api/run", payload);
    toast(r.msg || "🏃 Run logged!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
    document.getElementById("run-miles").value = "";
    document.getElementById("run-pace").value  = "";
    prevBadgeCount = (appState.badges || []).length;
  } catch (e) { toast("⚠ " + e.message); }
}

function openCustomDialog() {
  document.getElementById("custom-dialog").removeAttribute("hidden");
  document.getElementById("custom-text").focus();
}

function closeCustomDialog() {
  document.getElementById("custom-dialog").setAttribute("hidden", "");
  document.getElementById("custom-text").value = "";
}

async function submitCustomWorkout() {
  const text = document.getElementById("custom-text").value.trim();
  if (!text) { toast("Please describe your workout."); return; }
  try {
    const r = await api("/api/workout/custom", { text });
    closeCustomDialog();
    toast(r.msg || "✔ Custom workout logged!");
    appState = r.state;
    const workout = await api("/api/workout/today");
    renderAll(appState, workout);
    checkNewBadges(appState);
  } catch (e) { toast("⚠ " + e.message); }
}

// ── Badge notification ────────────────────────────────────────────────────────
function checkNewBadges(state) {
  const count = (state.badges || []).length;
  if (count > prevBadgeCount && prevBadgeCount > 0) {
    const newest = state.badges[state.badges.length - 1];
    if (newest) toast(`🎉 ${newest.name} unlocked!`, 5000);
  }
  prevBadgeCount = count;
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
document.getElementById("log-rec-btn").addEventListener("click", logRecommended);
document.getElementById("log-custom-btn").addEventListener("click", openCustomDialog);
document.getElementById("preview-track-btn").addEventListener("click", showTrackPreview);
document.getElementById("start-track-btn").addEventListener("click", () => startTrack());
document.getElementById("delete-track-btn").addEventListener("click", deleteCustomTrack);
document.getElementById("open-builder-btn").addEventListener("click", openBuilderDialog);
document.getElementById("track-select").addEventListener("change", updateDeleteTrackBtn);

// Live coin preview — delegate from workout-display so it works after re-renders
document.getElementById("workout-display").addEventListener("input", e => {
  if (e.target.classList.contains("movement-weight-input") &&
      e.target.dataset.key === "main") {
    updateCoinPreview();
  }
});

// Ruck section
document.getElementById("log-ruck-btn").addEventListener("click", logRuck);

// Run section
document.getElementById("log-run-btn").addEventListener("click", logRun);
document.getElementById("log-walk-btn").addEventListener("click", logWalk);
document.getElementById("go-to-ruck-btn").addEventListener("click", () => switchSection("ruck"));
document.getElementById("go-to-ruck-from-walk-btn").addEventListener("click", () => switchSection("ruck"));

// Custom workout dialog
document.getElementById("submit-custom").addEventListener("click", submitCustomWorkout);
document.getElementById("cancel-custom").addEventListener("click", closeCustomDialog);
document.getElementById("custom-dialog").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeCustomDialog();
});
document.getElementById("custom-text").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitCustomWorkout();
});

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
    if (appState) renderHistory(appState, historyFilter);
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
    renderEstateGrid();
  } catch (e) {
    console.error("Estate init failed:", e);
  }
}

function renderEstateResources() {
  const el = document.getElementById("estate-resources");
  if (!el || !estateState) return;
  const drachEl = document.getElementById("estate-drachma-pill");
  if (drachEl) drachEl.textContent = `🪙 ${(estateState.drachmae ?? 0).toFixed(2)}`;
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
    renderEstateGrid();
    (res.events || []).forEach(evt => {
      const t = evt.includes("Farm") || evt.includes("harvest") ? "farm"
              : evt.includes("drachma") || evt.includes("LAUREL")  ? "reward"
              : "system";
      pushEstateLog(evt, t);
    });
    toast(`⚔️ ${res.events?.[0] || "Workout logged!"}`);
    if (res.event) showEventPopup(res.event);
  } catch (e) {
    toast("Estate error: " + e.message, 4000);
  } finally {
    btn.disabled = false;
  }
});

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", () => { refresh(); initEstate(); });
