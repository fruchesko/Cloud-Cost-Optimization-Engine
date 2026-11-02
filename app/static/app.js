const $ = (s) => document.querySelector(s);
const money = (v) => v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = (v) => v.toLocaleString("en-US", { maximumFractionDigits: 2 });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pretty = (n) => n.replace(/_/g, " ").replace(/\bmin\b/, "minimum").replace(/\bmax\b/, "maximum");

let catalog = [], current = null, lastResultFor = null;

// Fractions (0..1) are shown as percentages.
const isPct = (p) => p.kind === "float" && p.max === 1;
const toView = (p, v) => isPct(p) ? Math.round(v * 1000) / 10 : v;
const fromView = (p, v) => isPct(p) ? v / 100 : v;

function renderTabs() {
  $("#tabs").innerHTML = catalog.map((s) =>
    `<button type="button" role="tab" data-id="${s.id}" aria-selected="${s.id === current.id}">${esc(s.name.replace(/:.*/, ""))}<br><small>${esc(s.name.replace(/^[^:]*:\s*/, ""))}</small></button>`).join("");
  $("#tabs").querySelectorAll("button").forEach((b) => b.onclick = () => select(b.dataset.id));
}

function paramControl(p) {
  const id = `p_${p.name}`;
  const help = p.help ? `<div class="help">${esc(p.help)}</div>` : "";
  if (p.kind === "multi") {
    return `<fieldset class="param multi" data-name="${p.name}"><legend>${esc(p.label)}</legend>${help}
      <div class="checks">${p.choices.map((c) => `<label class="check"><input type="checkbox" value="${esc(c)}" ${p.default.includes(c) ? "checked" : ""}> ${esc(c)}</label>`).join("")}</div>
      <div class="field-err" hidden></div></fieldset>`;
  }
  if (p.kind === "choice") {
    return `<div class="param" data-name="${p.name}"><label for="${id}">${esc(p.label)}</label>${help}
      <div class="row"><select id="${id}">${p.choices.map((c) => `<option ${c === p.default ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></div>
      <div class="field-err" hidden></div></div>`;
  }
  const pct = isPct(p);
  const min = toView(p, p.min), max = toView(p, p.max), step = pct ? 1 : p.step, val = toView(p, p.default);
  const unit = pct ? `% ${p.unit}` : p.unit;
  return `<div class="param" data-name="${p.name}">
    <label for="${id}"><span>${esc(p.label)}</span></label>${help}
    <div class="row">
      <input type="range" min="${min}" max="${max}" step="${step}" value="${val}" aria-label="${esc(p.label)} slider">
      <input type="number" id="${id}" min="${min}" max="${max}" step="${pct ? "0.1" : p.step}" value="${val}" inputmode="decimal">
      <span class="unit">${esc(unit)}</span>
    </div>
    <div class="help">Range ${num(min)}–${num(max)}${pct ? "%" : ""}</div>
    <div class="field-err" hidden></div></div>`;
}

function select(id) {
  current = catalog.find((s) => s.id === id);
  try { localStorage.setItem("scenario", id); } catch {}
  renderTabs();
  $("#desc").textContent = current.description;
  $("#notes").innerHTML = current.notes.map((n) => `<li>${esc(n)}</li>`).join("");
  $("#params").innerHTML = current.parameters.map(paramControl).join("");
  $("#params").querySelectorAll(".param").forEach((el) => {
    const range = el.querySelector("input[type=range]"), box = el.querySelector("input[type=number]");
    if (el.classList.contains("multi")) {
      el.querySelectorAll("input").forEach((i) => i.onchange = () => changed(el));
    } else if (range) {
      range.oninput = () => { box.value = range.value; changed(el); };
      box.oninput = () => { if (box.value !== "") range.value = box.value; changed(el); };
    } else {
      el.querySelector("select").onchange = () => changed(el);
    }
  });
  $("#result").innerHTML = `<div class="placeholder">Press Solve to run ${esc(current.name)}.</div>`;
  lastResultFor = null;
}

function changed(el) {
  el.classList.remove("invalid");
  el.querySelector(".field-err").hidden = true;
  if (lastResultFor === current.id) $("#result").classList.add("stale");
}

function readParams() {
  const out = {}, errors = [];
  for (const p of current.parameters) {
    const el = $(`.param[data-name="${p.name}"]`);
    if (p.kind === "choice") { out[p.name] = el.querySelector("select").value; continue; }
    if (p.kind === "multi") {
      const picked = [...el.querySelectorAll("input:checked")].map((i) => i.value);
      if (!picked.length) errors.push([p.name, "Pick at least one instance type."]); else out[p.name] = picked;
      continue;
    }
    const raw = el.querySelector("input[type=number]").value.trim();
    const v = Number(raw);
    const min = toView(p, p.min), max = toView(p, p.max);
    if (raw === "" || !Number.isFinite(v)) errors.push([p.name, "Enter a number."]);
    else if (v < min || v > max) errors.push([p.name, `Must be between ${num(min)} and ${num(max)}.`]);
    else if (p.kind === "int" && !Number.isInteger(v)) errors.push([p.name, "Must be a whole number."]);
    else out[p.name] = fromView(p, v);
  }
  return { params: out, errors };
}

function showFieldErrors(errors) {
  for (const [name, msg] of errors) {
    const el = $(`.param[data-name="${name}"]`);
    if (!el) continue;
    el.classList.add("invalid");
    const e = el.querySelector(".field-err"); e.textContent = msg; e.hidden = false;
  }
}

async function solve(ev) {
  ev.preventDefault();
  const { params, errors } = readParams();
  if (errors.length) { showFieldErrors(errors); return; }
  const btn = $("#solve"); btn.disabled = true; btn.textContent = "Solving…";
  try {
    const res = await fetch("solve", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: current.id, params }) });
    const body = await res.json().catch(() => ({}));
    $("#result").classList.remove("stale");
    if (res.ok) { renderResult(body); lastResultFor = current.id; return; }
    lastResultFor = null;
    if (body.error === "infeasible") {
      $("#result").innerHTML = `<div class="banner bad"><div class="big">No feasible plan</div>
        <p>${esc(body.message)}</p></div>`;
    } else if (res.status === 422 && Array.isArray(body.detail)) {
      showFieldErrors(body.detail.map((d) => [d.loc.filter((x) => typeof x === "string").pop(), d.msg]));
      $("#result").innerHTML = `<div class="banner warn">Some inputs are out of range. Fix the highlighted fields.</div>`;
    } else {
      $("#result").innerHTML = `<div class="banner warn">${esc(body.message || `Request failed (HTTP ${res.status}).`)}</div>`;
    }
  } catch (e) {
    $("#result").innerHTML = `<div class="banner warn">Could not reach the server. ${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = "Solve";
  }
}

function renderResult(r) {
  const hi = Math.max(r.heuristic_cost, r.optimal_cost) || 1;
  const pct = (v) => (v / hi * 100).toFixed(1);
  const saved = r.savings >= 0;
  const banner = saved
    ? `<div class="banner good"><div class="big">${money(r.savings)} saved (${r.savings_pct.toFixed(1)}%)</div>
       <p>The optimum costs ${money(r.optimal_cost)} against ${money(r.heuristic_cost)} for the baseline.</p></div>`
    : `<div class="banner warn"><b>The baseline is ${money(-r.savings)} cheaper here, but it does not meet the demand.</b>
       <p>The baseline only sizes for vCPUs, so it ignores the RAM${current.id === "scenario_15" ? ", IOPS" : ""} you asked for. The optimum is the cheapest plan that actually meets every requirement.</p></div>`;

  const hasProv = r.resources.some((x) => x.provider);
  const rows = r.resources.map((x) => `<tr><td>${esc(x.name)}</td>${hasProv ? `<td>${esc(x.provider)}</td>` : ""}<td>${esc(x.type)}</td>
    <td class="n">${num(x.count)}</td><td class="n">${num(x.count * x.vcpu_each)}</td><td class="n">${num(x.count * x.ram_gb_each)}</td>
    <td class="n">${money(x.total_cost)}</td></tr>`).join("");
  const cons = r.constraints.map((c) => `<tr><td>${esc(pretty(c.name))}</td>
    <td class="n">${num(c.lhs)}</td><td class="n">${c.sense === ">=" ? "≥" : "≤"} ${num(c.rhs)}</td><td class="n">${num(c.slack)}</td>
    <td>${c.binding ? '<span class="chip on">binding</span>' : '<span class="chip">slack</span>'}</td></tr>`).join("");

  $("#result").innerHTML = `
    <div class="cards">
      <div class="card base"><div class="k">Heuristic baseline</div><div class="v">${money(r.heuristic_cost)}</div><div class="bar"><i style="width:${pct(r.heuristic_cost)}%"></i></div></div>
      <div class="card opt"><div class="k">Optimum (LP)</div><div class="v">${money(r.optimal_cost)}</div><div class="bar"><i style="width:${pct(r.optimal_cost)}%"></i></div></div>
    </div>
    ${banner}
    <div class="section"><h2>Chosen resources</h2><div class="table-wrap"><table>
      <thead><tr><th>Instance</th>${hasProv ? "<th>Cloud</th>" : ""}<th>Pricing</th><th class="n">Count</th><th class="n">vCPU</th><th class="n">RAM GB</th><th class="n">Total cost</th></tr></thead>
      <tbody>${rows}</tbody></table></div></div>
    <div class="section"><h2>Constraints</h2><div class="table-wrap"><table>
      <thead><tr><th>Constraint</th><th class="n">Plan uses</th><th class="n">Limit</th><th class="n">Room left</th><th></th></tr></thead>
      <tbody>${cons}</tbody></table></div>
      <p class="meta">A binding constraint is one the plan uses exactly. Loosening it is the only way to lower the cost further.</p></div>
    <p class="meta">${esc(r.name)} · solver status ${esc(r.status)} · solved in ${r.solve_ms} ms</p>`;
}

async function init() {
  try {
    const res = await fetch("scenarios");
    catalog = (await res.json()).scenarios;
  } catch (e) {
    $("#result").innerHTML = `<div class="banner warn">Could not load scenarios. ${esc(e.message)}</div>`;
    return;
  }
  let saved = null; try { saved = localStorage.getItem("scenario"); } catch {}
  select(catalog.some((s) => s.id === saved) ? saved : catalog[catalog.length - 1].id);
  $("#form").onsubmit = solve;
  $("#reset").onclick = () => select(current.id);
}
init();

// ---- Needs assistant ----
const ai = { history: [], busy: false };
const aiLog = $("#ai-log");

function aiAdd(cls, text) {
  const el = document.createElement("div");
  el.className = `msg ${cls}`; el.textContent = text;
  aiLog.appendChild(el); aiLog.scrollTop = aiLog.scrollHeight;
  return el;
}

function fmtParam(p, v) {
  if (p.kind === "multi") return v.join(", ");
  if (p.kind === "choice") return v;
  if (isPct(p)) return `${num(v * 100)}%`;
  return `${num(v)} ${p.unit === "$" ? "USD" : p.unit}`;
}

function aiSuggestion(sug) {
  const sc = catalog.find((s) => s.id === sug.scenario);
  if (!sc) return;
  const box = document.createElement("div");
  box.className = "sugg";
  const items = Object.entries(sug.params).map(([k, v]) => {
    const p = sc.parameters.find((x) => x.name === k);
    return `<li>${esc(p.label)}: <b>${esc(fmtParam(p, v))}</b></li>`;
  }).join("");
  box.innerHTML = `<h4>Suggested settings · ${esc(sc.name)}</h4><ul>${items}</ul>
    <button class="btn primary" type="button">Apply settings</button>`;
  box.querySelector("button").onclick = () => {
    if (current.id !== sc.id) select(sc.id);
    for (const [k, v] of Object.entries(sug.params)) {
      const p = sc.parameters.find((x) => x.name === k);
      const el = $(`.param[data-name="${k}"]`);
      if (!p || !el) continue;
      if (p.kind === "multi") el.querySelectorAll("input").forEach((i) => i.checked = v.includes(i.value));
      else if (p.kind === "choice") el.querySelector("select").value = v;
      else {
        const vv = toView(p, v);
        el.querySelector("input[type=number]").value = vv;
        el.querySelector("input[type=range]").value = vv;
      }
      changed(el);
    }
    box.querySelector("button").textContent = "Applied ✓";
    aiAdd("bot", "Applied. Press Solve to compare the baseline with the optimum.");
  };
  aiLog.appendChild(box); aiLog.scrollTop = aiLog.scrollHeight;
}

async function aiSend(ev) {
  ev.preventDefault();
  const input = $("#ai-input"), text = input.value.trim();
  if (!text || ai.busy) return;
  ai.busy = true; $("#ai-send").disabled = true; input.value = "";
  aiAdd("me", text);
  ai.history.push({ role: "user", content: text });
  const typing = aiAdd("bot typing", "Thinking…");
  try {
    const { params } = readParams();
    const res = await fetch("assistant", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: ai.history.slice(-20), scenario: current?.id, params }) });
    const body = await res.json().catch(() => ({}));
    typing.remove();
    if (!res.ok) {
      ai.history.pop();
      aiAdd("err", body.message || (Array.isArray(body.detail) ? "That message is too long." : `Something went wrong (HTTP ${res.status}).`));
      return;
    }
    aiAdd("bot", body.reply);
    ai.history.push({ role: "assistant", content: body.reply });
    if (body.suggestion) aiSuggestion(body.suggestion);
  } catch (e) {
    typing.remove(); ai.history.pop();
    aiAdd("err", "Could not reach the assistant. Check your connection and try again.");
  } finally {
    ai.busy = false; $("#ai-send").disabled = false; input.focus();
  }
}

(async function aiInit() {
  try {
    const info = await (await fetch("assistant")).json();
    if (!info.enabled) return;
  } catch { return; }
  const open = $("#ai-open"), panel = $("#ai-panel");
  open.hidden = false;
  open.onclick = () => { panel.hidden = false; open.hidden = true; $("#ai-input").focus(); };
  $("#ai-close").onclick = () => { panel.hidden = true; open.hidden = false; };
  $("#ai-form").onsubmit = aiSend;
  $("#ai-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ai-form").requestSubmit(); }
  });
  aiAdd("bot", "Hi! Tell me about your client's workload: roughly how much compute and memory it needs, " +
    "whether there's money to pay upfront, how much interruption risk is acceptable, and any cloud policy. " +
    "I'll suggest settings you can apply with one click.");
})();
