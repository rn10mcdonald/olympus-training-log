/* ──────────────────────────────────────────────────────────────────────────
   Olympus Training Log – main.js
   ────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── API helper ────────────────────────────────────────────────────────────────
async function api(url, data) {
  const opts = data
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

// ── State ─────────────────────────────────────────────────────────────────────
let appState      = null;
let prevBadgeCount = 0;

// ── Refresh all UI ────────────────────────────────────────────────────────────
async function refresh() {
  try {
    appState = await api("/api/state");
    renderStats(appState);
    renderBadges(appState);
    renderHistory(appState);
  } catch (e) {
    toast("⚠ Error loading state: " + e.message);
  }
}

async function loadTodayWorkout() {
  try {
    const w = await api("/api/workout/today");
    renderWorkout(w);
  } catch (e) {
    toast("⚠ Error loading workout: " + e.message);
  }
}

async function populateTracks() {
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
    // pre-select the active track
    if (appState && appState.track) sel.value = appState.track;
  } catch (_) {}
}

// ── Stats bar ─────────────────────────────────────────────────────────────────
function isoWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - yearStart) / 86_400_000) + 1) / 7);
}

function renderStats(state) {
  // Drachma
  document.getElementById("drachma").textContent =
    (state.treasury || 0).toFixed(2);

  // Total ruck miles
  document.getElementById("total-miles").textContent =
    (state.total_ruck_miles || 0).toFixed(1);

  // Weekly streak (ISO week)
  const today = new Date();
  const weekKey = `(${today.getFullYear()}, ${isoWeekNumber(today)})`;
  const wkCount = Math.min((state.week_log || {})[weekKey] || 0, 3);
  document.getElementById("streak-display").textContent =
    "✔".repeat(wkCount) + "▢".repeat(3 - wkCount);

  // Cycle progress
  const done = Math.min((state.microcycle || {}).sessions_completed || 0, 6);
  document.getElementById("cycle-display").textContent =
    "▣".repeat(done) + "▢".repeat(6 - done);
}

// ── Workout display ───────────────────────────────────────────────────────────
function renderWorkout(w) {
  const el = document.getElementById("workout-display");

  if (w.status === "no_track") {
    el.innerHTML = `<p class="dim-msg">No active track. Select a track below and press <strong>Start</strong>.</p>`;
    return;
  }
  if (w.status === "cycle_complete") {
    el.innerHTML = `<p class="dim-msg">🏅 Cycle complete!  Log a custom workout or start a new track below.</p>`;
    return;
  }

  const accessories = (w.accessory || [])
    .map(a => `<li>${escHtml(a)}</li>`).join("");

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

// ── Badges ────────────────────────────────────────────────────────────────────
function renderBadges(state) {
  const badges   = state.badges || [];
  const trophies = [...badges].filter(b => b.type === "monster").reverse();
  const laurels  = [...badges].filter(b => b.type === "laurel").reverse();
  const journey  = [...badges].filter(b => b.type === "ruck_quest").reverse();

  // Trophies
  document.getElementById("trophies-list").innerHTML =
    trophies.length
      ? trophies.map(b => badgeCardHtml(b)).join("")
      : `<div class="empty-msg">Complete a 2-week cycle to earn a monster trophy</div>`;

  // Laurels
  document.getElementById("laurels-list").innerHTML =
    laurels.length
      ? laurels.map(b => badgeCardHtml(b)).join("")
      : `<div class="empty-msg">Log 3 workouts in a week to earn an Olympian Laurel</div>`;

  // Journey / ruck quest
  renderJourney(journey, state.total_ruck_miles || 0);
}

function badgeCardHtml(b) {
  const isGilded = (b.name || "").includes("★");
  const imgEl = b.image_path
    ? `<img class="badge-img" src="/img/${encodeURIPath(b.image_path)}"
           alt="${escHtml(b.name)}"
           onerror="this.replaceWith(Object.assign(document.createElement('div'),
             {className:'badge-emoji', textContent:'🏆'}))">`
    : `<div class="badge-emoji">${b.type === "laurel" ? "🌿" : "🏆"}</div>`;
  return `
    <div class="badge-card${isGilded ? " gilded" : ""}">
      ${imgEl}
      <div class="badge-name">${escHtml(b.name)}</div>
      <div class="badge-date">${b.date || b.earned_on || ""}</div>
    </div>`;
}

// ── Journey (ruck quest) ──────────────────────────────────────────────────────
const TRIP_MILES = 306;
const RUCK_STOPS = [
  [0,   "Acropolis"],    [12,  "Eleusis"],     [26,  "Megara"],
  [48,  "Corinth"],      [75,  "Nemea"],        [99,  "Tegea"],
  [153, "Sparta"],       [206, "Mantinea"],     [224, "Argos"],
  [249, "Epidaurus"],    [286, "Sounion"],      [306, "Athens_Return"],
];

function renderJourney(journeyBadges, totalMiles) {
  const pct = Math.min((totalMiles / TRIP_MILES) * 100, 100);
  const progressHtml = `
    <div class="journey-progress">
      <span class="progress-label">${totalMiles.toFixed(1)} / ${TRIP_MILES} mi</span>
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill" style="width:${pct.toFixed(1)}%"></div>
      </div>
      <span class="progress-label">${pct.toFixed(0)}%</span>
    </div>`;

  if (!journeyBadges.length) {
    document.getElementById("journey-list").innerHTML =
      progressHtml +
      `<div class="empty-msg">Ruck your first miles to unlock Pheidippides Way-Points</div>`;
    return;
  }

  const cards = journeyBadges.map(b => {
    const imgEl = b.image_path
      ? `<img src="/img/${encodeURIPath(b.image_path)}" alt="${escHtml(b.stop || b.name)}"
             onerror="this.replaceWith(Object.assign(document.createElement('div'),
               {className:'postcard-placeholder', textContent:'📜'}))">`
      : `<div class="postcard-placeholder">📜</div>`;
    return `
      <div class="postcard">
        ${imgEl}
        <div>
          <div class="postcard-city">${escHtml(b.stop || b.name)}</div>
          ${b.caption
            ? `<div class="postcard-caption">${escHtml(b.caption)}</div>`
            : ""}
          <div class="postcard-date">${b.date || b.earned_on || ""}</div>
        </div>
      </div>`;
  }).join("");

  document.getElementById("journey-list").innerHTML =
    progressHtml + `<div class="postcard-list">${cards}</div>`;
}

// ── History ───────────────────────────────────────────────────────────────────
function renderHistory(state) {
  const byDate = {};

  for (const w of state.workouts || []) {
    if (!w.date) continue;
    (byDate[w.date] = byDate[w.date] || [])
      .push({ kind: w.type, detail: w.details });
  }
  for (const r of state.ruck_log || []) {
    if (!r.date || typeof r.distance_miles !== "number") continue;
    const detail = `${r.distance_miles} mi @ ${r.weight_lbs} lb`;
    (byDate[r.date] = byDate[r.date] || []).push({ kind: "ruck", detail });
  }

  const dates = Object.keys(byDate).sort().reverse();
  const el    = document.getElementById("history-list");

  if (!dates.length) {
    el.innerHTML = `<div class="empty-msg">No workouts logged yet — get moving!</div>`;
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

// ── Actions ───────────────────────────────────────────────────────────────────
async function logRecommended() {
  try {
    const r = await api("/api/workout/recommended", {});
    toast(r.msg || "✔ Workout logged!");
    appState = r.state;
    renderStats(appState);
    renderBadges(appState);
    renderHistory(appState);
    await loadTodayWorkout();
    checkNewBadges(appState);
  } catch (e) { toast("⚠ " + e.message); }
}

async function logRuck() {
  const miles  = parseFloat(document.getElementById("miles").value || 0);
  const pounds = parseFloat(document.getElementById("lbs").value  || 0);
  if (!miles || miles <= 0) { toast("Enter a valid distance first."); return; }
  try {
    const r = await api("/api/ruck", { miles, pounds });
    toast(r.msg || "🎒 Ruck logged!");
    appState = r.state;
    renderStats(appState);
    renderBadges(appState);
    renderHistory(appState);
    checkNewBadges(appState);
    const newJourney = appState.badges.filter(b => b.type === "ruck_quest");
    if (newJourney.length > 0) switchTab("journey");
    document.getElementById("miles").value = "";
  } catch (e) { toast("⚠ " + e.message); }
}

async function startTrack() {
  const key = document.getElementById("track-select").value;
  if (!key) return;
  try {
    const r = await api("/api/track/select", { key });
    toast(r.msg || "Track started!");
    appState = r.state;
    renderStats(appState);
    await loadTodayWorkout();
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
    renderStats(appState);
    renderBadges(appState);
    renderHistory(appState);
    checkNewBadges(appState);
  } catch (e) { toast("⚠ " + e.message); }
}

// ── Badge-earned notification ─────────────────────────────────────────────────
function checkNewBadges(state) {
  const count = (state.badges || []).length;
  if (count > prevBadgeCount && prevBadgeCount > 0) {
    const newest = state.badges[state.badges.length - 1];
    if (newest) toast(`🎉 New badge unlocked: ${newest.name}!`, 5000);
  }
  prevBadgeCount = count;
}

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-pane").forEach(p =>
    p.classList.toggle("active", p.id === `tab-${name}`));
}

// ── Utility ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Encode individual path segments while preserving slashes
function encodeURIPath(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

// ── Event listeners ───────────────────────────────────────────────────────────
document.getElementById("refresh-btn").addEventListener("click", async () => {
  await Promise.all([refresh(), loadTodayWorkout()]);
  toast("Refreshed");
});

document.getElementById("log-rec-btn").addEventListener("click", logRecommended);
document.getElementById("log-custom-btn").addEventListener("click", openCustomDialog);
document.getElementById("log-ruck-btn").addEventListener("click", logRuck);
document.getElementById("start-track-btn").addEventListener("click", startTrack);

document.getElementById("submit-custom").addEventListener("click", submitCustomWorkout);
document.getElementById("cancel-custom").addEventListener("click", closeCustomDialog);

document.querySelectorAll(".tab-btn").forEach(btn =>
  btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

// Close dialog on backdrop click
document.getElementById("custom-dialog").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeCustomDialog();
});

// Ctrl+Enter submits the custom workout textarea
document.getElementById("custom-text").addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitCustomWorkout();
});

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", async () => {
  await Promise.all([refresh(), loadTodayWorkout()]);
  await populateTracks();
  if (appState) prevBadgeCount = (appState.badges || []).length;
});
