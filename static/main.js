/* ──────────────────────────────────────────────────────────────────────────
   Olympus Training Log – main.js
   ────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────────
const TRIP_MILES  = 306;
const SESSIONS_NEEDED = 6;
const WEEK_TARGET = 3;

// ── API helper ────────────────────────────────────────────────────────────────
async function api(url, data) {
  const opts = data !== undefined
    ? { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data) }
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

// ── App state ─────────────────────────────────────────────────────────────────
let appState        = null;
let prevBadgeCount  = 0;
let historyFilter   = "all";
let previewedKey    = null;   // track key currently shown in preview dialog

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
  renderCycleGrid(state);
}

// ── Cycle grid ────────────────────────────────────────────────────────────────
function getMondayOf(dateStr) {
  // Parse as local noon to avoid timezone-midnight edge cases
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay(); // 0 = Sun, 1 = Mon … 6 = Sat
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

function fmtShort(d) {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function renderCycleGrid(state) {
  const el  = document.getElementById("cycle-grid");
  const mc  = state.microcycle || {};
  const done = Math.min(mc.sessions_completed || 0, SESSIONS_NEEDED);

  document.getElementById("cycle-fraction").textContent = `${done} / ${SESSIONS_NEEDED}`;

  if (!mc.start_date) {
    el.innerHTML = `<p class="dim-msg">Select a track below to begin.</p>`;
    return;
  }

  // Week 1 = Mon of week containing start_date; Week 2 = 7 days later
  const mon1 = getMondayOf(mc.start_date);
  const sun1 = new Date(mon1); sun1.setDate(sun1.getDate() + 6);
  const mon2 = new Date(mon1); mon2.setDate(mon2.getDate() + 7);
  const sun2 = new Date(mon2); sun2.setDate(sun2.getDate() + 6);

  // Pull dates for sessions logged in this cycle (workouts on or after start_date)
  const cycleLogs = (state.workouts || [])
    .filter(w => w.date >= mc.start_date)
    .slice(0, SESSIONS_NEEDED);

  function sessionCell(idx) {
    const num   = `S${idx + 1}`;
    if (idx < done) {
      const raw  = cycleLogs[idx]?.date || "";
      const label = raw
        ? fmtShort(new Date(raw + "T12:00:00"))
        : "done";
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

  el.innerHTML = `
    <div class="cycle-week">
      <div class="cycle-week-hdr">
        <span class="cw-label">Week 1</span>
        <span class="cw-range">${fmtShort(mon1)} – ${fmtShort(sun1)}</span>
      </div>
      <div class="cs-row">${sessionCell(0)}${sessionCell(1)}${sessionCell(2)}</div>
    </div>
    <div class="cycle-divider"></div>
    <div class="cycle-week">
      <div class="cycle-week-hdr">
        <span class="cw-label">Week 2</span>
        <span class="cw-range">${fmtShort(mon2)} – ${fmtShort(sun2)}</span>
      </div>
      <div class="cs-row">${sessionCell(3)}${sessionCell(4)}${sessionCell(5)}</div>
    </div>`;
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
  const accessories = (w.accessory || []).map(a => `<li>${escHtml(a)}</li>`).join("");
  el.innerHTML = `
    <div class="workout-track-name">${escHtml(w.track_name || "")}</div>
    <div class="workout-session-label">Session ${w.session_num} of ${w.total_sessions}</div>
    <div class="workout-main">${escHtml(w.main)}</div>
    <div class="workout-accessories">
      <h4>Accessories</h4>
      <ul>${accessories}</ul>
    </div>
    <div class="workout-finisher">
      <span class="finisher-label">Finisher</span>
      ${escHtml(w.finisher)}
    </div>`;
}

async function populateTracks(state) {
  try {
    const tracks = await api("/api/tracks");
    const sel = document.getElementById("track-select");
    sel.innerHTML = "";
    for (const [key, name] of Object.entries(tracks)) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = name;
      sel.appendChild(opt);
    }
    if (state && state.track) sel.value = state.track;
  } catch (_) {}
}

// ── Ruck section ──────────────────────────────────────────────────────────────
function renderRuckSection(state) {
  const ruckMiles = state.total_ruck_miles || 0;
  const runMiles  = state.total_run_miles  || 0;
  const journey   = state.journey_miles    || 0;

  document.getElementById("total-ruck-miles").textContent = ruckMiles.toFixed(1) + " mi";
  document.getElementById("total-run-miles-ruck").textContent = runMiles.toFixed(1) + " mi";

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

  // Drachma earned from running (coins stored per entry)
  const runDrachma = (state.run_log || [])
    .reduce((sum, r) => sum + (r.coins || 0), 0);

  document.getElementById("total-run-miles").textContent = runMiles.toFixed(1) + " mi";
  document.getElementById("run-drachma").textContent = "🪙 " + runDrachma.toFixed(2);

  // Mini journey bar
  const pct = Math.min((journey / TRIP_MILES) * 100, 100);
  document.getElementById("journey-bar-run").style.width = pct.toFixed(1) + "%";
  document.getElementById("journey-fraction-run").textContent =
    `${journey.toFixed(1)} / ${TRIP_MILES} mi`;

  // Recent runs (up to 5)
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

// ── Vault section ─────────────────────────────────────────────────────────────
function renderVaultSection(state) {
  const badges   = state.badges || [];
  const trophies = [...badges].filter(b => b.type === "monster").reverse();
  const laurels  = [...badges].filter(b => b.type === "laurel").reverse();
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
      (byDate[w.date] = byDate[w.date] || [])
        .push({ kind: w.type === "recommended" ? "lifting" : "custom",
                detail: w.details, _filter: "lifting" });
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

    // Accordion click
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
  try {
    const r = await api("/api/workout/recommended", {});
    toast(r.msg || "✔ Workout logged!");
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
    // If a new waypoint was unlocked, show the journey
    const newPostcards = (appState.badges || []).filter(b => b.type === "ruck_quest");
    if (newPostcards.length > prevBadgeCount) switchSection("ruck");
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

// ── Event wiring ──────────────────────────────────────────────────────────────

// Bottom nav
document.querySelectorAll(".nav-btn").forEach(btn =>
  btn.addEventListener("click", () => switchSection(btn.dataset.section)));

// Train section
document.getElementById("refresh-btn").addEventListener("click", refresh);
document.getElementById("log-rec-btn").addEventListener("click", logRecommended);
document.getElementById("log-custom-btn").addEventListener("click", openCustomDialog);
document.getElementById("preview-track-btn").addEventListener("click", showTrackPreview);
document.getElementById("start-track-btn").addEventListener("click", () => startTrack());

// Ruck section
document.getElementById("log-ruck-btn").addEventListener("click", logRuck);

// Run section
document.getElementById("log-run-btn").addEventListener("click", logRun);
document.getElementById("go-to-ruck-btn").addEventListener("click", () => switchSection("ruck"));

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

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", refresh);
