async function api(url, data) {
  const opts = data
    ? {method: "POST", headers: {"Content-Type":"application/json"},
       body: JSON.stringify(data)}
    : {};
  const r = await fetch(url, opts);
  if (!r.ok) { alert(await r.text()); throw new Error(r.statusText); }
  return r.json();
}

async function refresh() {
  const state = await api("/api/state");
  document.getElementById("drachma").textContent = state.treasury.toFixed(2);
  document.getElementById("log").textContent =
    state.workouts.map(w => `${w.date} – ${w.details}`).join("\n");
}
async function logRuck() {
  await api("/api/ruck", {
    miles:  parseFloat(document.getElementById("miles").value||0),
    pounds: parseFloat(document.getElementById("lbs").value||0)
  });
  refresh();
}
window.addEventListener("load", refresh);
