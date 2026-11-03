// NeuroHear dashboard. No build step, no external libraries: works offline.
"use strict";
const $ = (id) => document.getElementById(id);
const C = { stim: "#d6246e", spike: "#0f766e", art: "#e9a23b", ink: "#14213d", muted: "#56637a", grid: "#e3e8ec" };
const S = { exp: null, backend: null, config: null, chosen: null, connected: false, lastTrial: null,
            lastResult: null, report: null, perm: null };

// ---------------------------------------------------------------- utils
function toast(msg, isErr) {
  const t = $("toast"); t.textContent = msg; t.className = "show" + (isErr ? " err" : "");
  clearTimeout(t._h); t._h = setTimeout(() => (t.className = ""), 4200);
}
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
const pct = (x) => (x == null ? "—" : Math.round(x * 100) + "%");
function setupCanvas(cv) {
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); return [g, w, h];
}

// --------------------------------------------------------- provenance
function provenance() {
  const b = S.backend;
  if (!S.connected || !b) return { text: "DISCONNECTED", cls: "off" };
  return { text: b.provenance || b.source, cls: b.source === "live_cl1" ? "live" : "" };
}
function renderHeader() {
  const p = provenance();
  $("provText").textContent = p.text; $("prov").className = "prov " + p.cls;
  const e = S.exp;
  $("mState").textContent = e ? e.state.replace("_", " ").toLowerCase() : "—";
  $("mRun").textContent = e ? e.run_id.slice(-6) : "—";
  $("mSeed").textContent = e ? e.seed : "—";
  if (S.backend) $("sourceSel").value = S.backend.source === "cl_sdk_sim" ? "cl_sdk_sim" : S.backend.source;
  const busy = !e || e.busy || !S.connected;
  $("sendBtn").disabled = busy || !S.chosen || !(S.backend && S.backend.ready);
  document.querySelectorAll("[data-act]").forEach((b) => (b.disabled = busy));
  if (e && !busy) {
    const has = (id) => e.leaderboard.some((r) => r.encoder_id === id);
    document.querySelector('[data-act="optimise"]').disabled = !has(e.baseline_id) || e.locked;
    document.querySelector('[data-act="baseline"]').disabled = e.locked;
    document.querySelector('[data-act="lock-test"]').disabled = !e.locked || e.report_ready;
  }
  const n = e ? e.counts : {};
  $("info").textContent = e
    ? `n_train ${n.train} · n_val ${n.val} · n_test ${n.test} · active channels ${e.preflight ? e.preflight.n_active_channels : "not measured"} · active encoder ${e.active_encoder_id}` +
      (e.error ? ` · error: ${e.error}` : "")
    : "Backend disconnected. Start it with ./scripts/run_local.sh";
}

// --------------------------------------------------------- encoding view
function encoderSpec(id) { return S.config && S.config.candidates.find((c) => c.encoder_id === id); }
function renderEncoding(pulses, encId) {
  const spec = encoderSpec(encId);
  $("encId").textContent = encId || "—";
  $("encDesc").textContent = spec ? spec.description : "";
  const [g, w, h] = setupCanvas($("pulse"));
  g.clearRect(0, 0, w, h);
  if (!pulses || !pulses.length) {
    g.fillStyle = C.muted; g.font = "13px system-ui"; g.fillText("Choose yes or no to see its pulse pattern", 12, h / 2); return;
  }
  const chans = [...new Set(pulses.map((p) => p.channel))].sort((a, b) => a - b);
  const span = Math.max(40, ...pulses.map((p) => p.offset_ms)) * 1.15;
  const L = 44, R = 10, T = 10, B = 22, rowH = (h - T - B) / chans.length;
  g.font = "12px system-ui"; g.textBaseline = "middle";
  chans.forEach((c, i) => {
    const y = T + rowH * (i + 0.5);
    g.fillStyle = C.muted; g.fillText("ch " + c, 6, y);
    g.strokeStyle = C.grid; g.beginPath(); g.moveTo(L, y); g.lineTo(w - R, y); g.stroke();
  });
  pulses.forEach((p) => {
    const i = chans.indexOf(p.channel), x = L + (p.offset_ms / span) * (w - L - R), y = T + rowH * i;
    g.fillStyle = C.stim; g.fillRect(x - 2, y + rowH * 0.15, 5, rowH * 0.7);
  });
  g.fillStyle = C.muted; g.textBaseline = "alphabetic";
  for (let t = 0; t <= span; t += span > 120 ? 50 : 20) { const x = L + (t / span) * (w - L - R); if (x < w - R - 34) g.fillText(t + "", x - 4, h - 6); }
  g.fillText("ms", w - R - 16, h - 6);
  const b = spec && spec.budget;
  $("budget").textContent = b ? `${b.n_pulses} pulses · ${b.total_charge_nC} nC total · ${b.max_current_uA} µA · same budget for yes and no` : "";
}

// ------------------------------------------------------------- raster
function renderRaster(tr) {
  const [g, w, h] = setupCanvas($("raster"));
  g.clearRect(0, 0, w, h);
  const L = 40, R = 10, T = 12, B = 26, nCh = 64, rowH = (h - T - B) / nCh;
  if (!tr) {
    g.fillStyle = C.muted; g.font = "14px system-ui";
    g.fillText("Send a message or run a protocol step to record a response.", L, h / 2); return;
  }
  const dur = tr.duration_ms, X = (t) => L + (t / dur) * (w - L - R);
  // response window
  const [wa, wb] = tr.response_window_ms;
  if (wb > wa) { g.fillStyle = "rgba(15,118,110,.09)"; g.fillRect(X(wa), T, X(wb) - X(wa), h - T - B);
    g.strokeStyle = C.spike; g.setLineDash([4, 3]); g.strokeRect(X(wa), T, X(wb) - X(wa), h - T - B); g.setLineDash([]); }
  // artifact blanking (hatched)
  (tr.artifact_intervals_ms || []).forEach(([a, b]) => {
    const x0 = X(a), x1 = Math.max(X(b), x0 + 2);
    g.save(); g.beginPath(); g.rect(x0, T, x1 - x0, h - T - B); g.clip();
    g.fillStyle = "rgba(233,162,59,.35)"; g.fillRect(x0, T, x1 - x0, h - T - B);
    g.strokeStyle = C.art; g.lineWidth = 1;
    for (let y = T - 20; y < h; y += 6) { g.beginPath(); g.moveTo(x0, y); g.lineTo(x0 + 20, y + 20); g.stroke(); }
    g.restore();
  });
  // channel grid
  g.fillStyle = C.muted; g.font = "11px system-ui"; g.textBaseline = "middle";
  for (let c = 0; c < nCh; c += 8) { const y = T + rowH * c; g.strokeStyle = C.grid; g.beginPath(); g.moveTo(L, y); g.lineTo(w - R, y); g.stroke(); g.fillText(c, 10, y + rowH * 4); }
  // stimulation pulses
  (tr.stimulus || []).forEach((p) => {
    const x = X(tr.stim_onset_ms + p.offset_ms), y = T + rowH * p.channel;
    g.strokeStyle = "rgba(214,36,110,.25)"; g.beginPath(); g.moveTo(x, T); g.lineTo(x, h - B); g.stroke();
    g.fillStyle = C.stim; g.fillRect(x - 2, y - 2, 5, rowH + 4);
  });
  // spikes
  g.fillStyle = C.spike;
  for (const [t, c] of tr.events) g.fillRect(X(t) - 0.6, T + rowH * c + rowH * 0.1, 1.6, Math.max(1.5, rowH * 0.8));
  // axis
  g.fillStyle = C.muted; g.textBaseline = "alphabetic";
  const axisLbl = "ms from stimulus onset", lw = g.measureText(axisLbl).width;
  for (let t = Math.ceil(-tr.stim_onset_ms / 100) * 100; t + tr.stim_onset_ms <= dur; t += 100) {
    const x = X(t + tr.stim_onset_ms); if (x < w - R - lw - 30) g.fillText(t + "", x - 8, h - 8); }
  g.fillText(axisLbl, w - R - lw, h - 8);
  const label = tr.split === "test" || tr.split === "control" ? "label hidden" : "";
  $("trialInfo").textContent = `${tr.provenance} · ${tr.encoder_id || "spontaneous"} · ${tr.split}${label ? " · " + label : ""} · ${tr.events.length} events · trial ${String(tr.trial_id).slice(-6)}`;
  $("qflags").textContent = tr.quality_flags && tr.quality_flags.length ? "Quality flags: " + tr.quality_flags.join(", ") : "";
}

// ------------------------------------------------------- decoder panel
function renderResult(r) {
  if (!r) return;
  if (!r.decoder_trained) {
    $("pred").textContent = "—";
    $("predProb").textContent = "Decoder not trained yet for " + r.encoder_id + ". Run the baseline first.";
    $("predTruth").textContent = ""; return;
  }
  $("pred").textContent = r.pred_label === "YES" ? "Yes" : "No";
  $("predProb").textContent = `Decoded from post-stimulus neural features only · confidence ${pct(r.pred_prob)} · ${r.provenance} · single trial, not a metric`;
  if (r.true_label == null) {   // live audio: the system never knows which word was said
    $("predTruth").textContent = "Live audio: the system was never told which word you said. " + (r.note || "");
    $("predTruth").className = "truth"; return;
  }
  $("predTruth").textContent = r.correct ? "Matches the sent message" : "Does not match the sent message (" + r.true_label.toLowerCase() + ")";
  $("predTruth").className = "truth " + (r.correct ? "good" : "bad");
}
function renderBoard() {
  const e = S.exp; if (!e || !e.leaderboard.length) return;
  $("board").innerHTML = e.leaderboard.map((r) => {
    const v = r.val_balanced_accuracy ?? 0, tag = r.is_baseline ? " (baseline)" : r.is_winner ? " (chosen)" : "";
    return `<div class="row ${r.is_winner ? "win" : ""}" title="${r.description}"><div class="bar"><div class="fill" style="width:${v * 100}%"></div><div class="chance" title="chance"></div><span class="lbl">${r.encoder_id}${tag}</span></div><span>${r.val_correct}/${r.val_n}</span></div>`;
  }).join("") + `<p class="note">Dashed line: chance. ${e.leaderboard[0].provenance}. Chosen on validation trials only.</p>`;
}
function renderTest() {
  const e = S.exp, r = S.report;
  const card = (id, res) => {
    if (!res) return ["—", "held-out test not run"];
    if (res.balanced_accuracy == null) return ["—", "Insufficient evidence"];
    return [pct(res.balanced_accuracy), `${res.correct}/${res.n} held-out · 95% CI ${pct(res.ci95[0])}–${pct(res.ci95[1])}`];
  };
  const tr = (e && e.test_results) || (r && r.test_results) || {};
  const base = e && tr[e.baseline_id], win = e && e.winner_id && tr[e.winner_id];
  let [a, b] = card(e && e.baseline_id, base); $("baseAcc").textContent = a; $("baseN").textContent = (e ? e.baseline_id + " · " : "") + b;
  if (e && e.winner_id === e.baseline_id && base) { $("winAcc").textContent = "="; $("winN").textContent = "Baseline was selected; no other encoder tested"; }
  else { [a, b] = card(e && e.winner_id, win); $("winAcc").textContent = a; $("winN").textContent = (e && e.winner_id ? e.winner_id + " · " : "") + b; }
  if (!r) { $("verdict").textContent = e && e.locked ? `Locked: ${e.winner_id}. Run the sealed test.` : ""; return; }
  $("verdict").textContent = r.verdict + " " + r.provenance + ".";
  const c = r.controls, nr = c.NO_RESPONSE, pm = c.PERMUTED_LABELS, am = c.ARTIFACT_MASK, sep = c.TRAIN_TEST_SEPARATION;
  const row = (k, v) => `<div><dt>${k}</dt><dd>${v}</dd></div>`;
  $("controls").innerHTML =
    row("Shuffled labels", `null ${pct(pm.null_mean)}, 95th pct ${pct(pm.null_p95)}, p = ${pm.p_value.toFixed(3)}`) +
    row("No response", nr.status === "acquired" ? `${nr.correct}/${nr.n} (${pct(nr.balanced_accuracy)}) with mask, p = ${nr.binomial_p_vs_chance.toFixed(2)} vs chance; ${pct(nr.unmasked_balanced_accuracy)} without mask` : "not acquired") +
    row("Artifact mask", `${am.blank_ms_per_pulse} ms blank per pulse; window +${am.post_gap_ms}–${am.post_gap_ms + am.window_ms} ms after last pulse. Unmasked: ${pct(am.diagnostic_unmasked_balanced_accuracy)}`) +
    row("Separation", sep.disjoint ? `whole trials disjoint (${sep.n_train}/${sep.n_val}/${sep.n_test}); decoders frozen before test` : "LEAK DETECTED") +
    row("No-cell", "not acquired");
}
function renderAll() { renderHeader(); renderBoard(); renderTest(); }

// --------------------------------------------------------------- events
function handle(ev) {
  switch (ev.type) {
    case "hello": S.exp = ev.experiment; S.backend = ev.backend; S.connected = true; renderAll(); break;
    case "state": refresh(); break;
    case "source": S.backend = ev.status; S.report = null; refresh(); toast("Source: " + ev.status.provenance); break;
    case "reset": S.report = null; S.lastResult = null; $("pred").textContent = "—"; refresh(); break;
    case "progress": $("bar").style.width = (100 * ev.completed / ev.total) + "%"; break;
    case "trial_started": if (ev.stimulus && ev.stimulus.length) renderEncoding(ev.stimulus, ev.encoder_id); break;
    case "spikes_batch": S.lastTrial = ev; renderRaster(ev); break;
    case "trial_result": S.lastResult = ev; renderResult(ev); refresh(); break;
    case "candidate_scored": refresh(); break;
    case "locked": toast("Encoder locked: " + ev.winner + ". Decoders frozen."); refresh(); break;
    case "report_ready": S.report = ev.report; refresh(); toast("Locked test complete"); break;
    case "error": toast(ev.message, true); refresh(); break;
  }
}
async function refresh() {
  try { const h = await api("/health"); S.exp = h.experiment; S.backend = h.backend; S.connected = true; }
  catch { S.connected = false; }
  renderAll();
}
function connect() {
  const es = new EventSource("/events");
  es.onmessage = (m) => handle(JSON.parse(m.data));
  es.onerror = () => { S.connected = false; renderHeader(); };
  es.onopen = () => { S.connected = true; refresh(); };
}

// ------------------------------------------------------------- actions
function choose(label, how) {
  S.chosen = label; $("chosen").textContent = label === "YES" ? "Yes" : "No"; $("chosenHow").textContent = how;
  document.querySelectorAll(".token").forEach((b) => b.classList.toggle("sel", b.dataset.label === label));
  const enc = S.exp ? S.exp.active_encoder_id : null, spec = encoderSpec(enc);
  if (spec) renderEncoding(spec[label], enc);
  renderHeader();
}
document.querySelectorAll(".token").forEach((b) => b.addEventListener("click", () => choose(b.dataset.label, "(button)")));
$("sendBtn").addEventListener("click", async () => {
  if (S.backend && S.backend.source === "live_cl1" && !confirm("Deliver live stimulation to the CL1 culture? The operator must have approved this session.")) return;
  try { $("sendBtn").disabled = true; await api("/trials", { method: "POST", body: JSON.stringify({ label: S.chosen }) }); }
  catch (e) { toast(e.message, true); } finally { renderHeader(); }
});
document.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", async () => {
  const act = b.dataset.act;
  if (S.backend && S.backend.source === "live_cl1" && act !== "preflight" && !confirm("This step delivers many live stimulation trials. Continue?")) return;
  try { $("bar").style.width = "0"; await api("/experiments/" + act, { method: "POST" }); b.classList.add("done"); }
  catch (e) { toast(e.message, true); } finally { refresh(); }
}));
$("stopBtn").addEventListener("click", async () => { try { await api("/stop", { method: "POST" }); } catch (e) { toast(e.message, true); } });
$("resetBtn").addEventListener("click", async () => {
  try { await api("/reset", { method: "POST" }); document.querySelectorAll("[data-act]").forEach((b) => b.classList.remove("done"));
    $("controls").innerHTML = '<p class="note">Appear after the locked test.</p>'; $("board").innerHTML = '<p class="note">Run the baseline, then optimise.</p>';
    renderRaster(null); toast("Reset. Earlier runs stay on disk."); } catch (e) { toast(e.message, true); }
});
$("exportBtn").addEventListener("click", () => {
  if (!S.exp) return;
  const a = document.createElement("a"); a.href = `/experiments/${S.exp.run_id}/export`; a.click();
  const img = document.createElement("a"); img.download = `neurohear-${S.exp.run_id}-raster.png`;
  img.href = $("raster").toDataURL("image/png"); img.click();
});
$("sourceSel").addEventListener("change", async (e) => {
  const src = e.target.value;
  let replay_path = null;
  if (src === "replay") { replay_path = prompt("Run folder or trials.jsonl path to replay (e.g. runs/<run_id>)"); if (!replay_path) { renderHeader(); return; } }
  if (!confirm(`Switch data source to "${e.target.selectedOptions[0].text}"? This starts a new run.`)) { renderHeader(); return; }
  try { await api("/source", { method: "POST", body: JSON.stringify({ source: src, seed: S.exp ? S.exp.seed : 123, replay_path, confirm: true }) }); }
  catch (err) { toast(err.message, true); refresh(); }
});

// ------------------------------------------------- spoken audio -> pulses
$("speakBtn").addEventListener("click", async () => {
  const btn = $("speakBtn"); btn.disabled = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
    const ctx = new AudioContext(), src = ctx.createMediaStreamSource(stream), proc = ctx.createScriptProcessor(4096, 1, 1), chunks = [];
    proc.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(proc); proc.connect(ctx.destination);
    btn.textContent = "Listening: say yes or no now";
    await new Promise((r) => setTimeout(r, 1500));
    proc.disconnect(); src.disconnect(); stream.getTracks().forEach((t) => t.stop());
    const sr = ctx.sampleRate; await ctx.close();
    const n = chunks.reduce((a, c) => a + c.length, 0), pcm = new Int16Array(n); let o = 0;
    for (const c of chunks) for (let i = 0; i < c.length; i++) pcm[o++] = Math.max(-1, Math.min(1, c[i])) * 32767;
    const bytes = new Uint8Array(pcm.buffer); let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    btn.textContent = "Sending to the culture (the first time also trains the readout)";
    await api("/audio-trial", { method: "POST", body: JSON.stringify({ sr, pcm16: btoa(bin) }) });
  } catch (e) { toast(e.message, true); }
  finally { btn.disabled = false; btn.textContent = "Speak into the culture (raw audio)"; }
});

// ------------------------------------------------------------ microphone
let audio = null;
$("micBtn").addEventListener("click", async () => {
  const btn = $("micBtn");
  if (audio) { audio.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const ctx = new AudioContext(), an = ctx.createAnalyser(); an.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(an);
    const buf = new Float32Array(an.fftSize); let raf;
    const draw = () => {
      an.getFloatTimeDomainData(buf);
      const [g, w, h] = setupCanvas($("wave")); g.clearRect(0, 0, w, h);
      g.strokeStyle = C.ink; g.lineWidth = 1.5; g.beginPath();
      for (let i = 0; i < buf.length; i++) { const x = (i / buf.length) * w, y = h / 2 + buf[i] * h * 1.8; i ? g.lineTo(x, y) : g.moveTo(x, y); }
      g.stroke(); raf = requestAnimationFrame(draw);
    };
    draw();
    let rec = null;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      rec = new SR(); rec.lang = "en-GB"; rec.interimResults = false; rec.maxAlternatives = 3;
      rec.onresult = (ev) => {
        const alts = [...ev.results[0]].map((a) => a.transcript.trim().toLowerCase());
        const hit = alts.find((t) => /\b(yes|yeah|yep|no|nope)\b/.test(t));
        if (hit) choose(/\b(no|nope)\b/.test(hit) ? "NO" : "YES", `(heard "${hit}" by browser speech recognition)`);
        else toast(`Heard "${alts[0]}". Say yes or no, or use the buttons.`, true);
        audio && audio.stop();
      };
      rec.onerror = (ev) => { toast("Speech recognition unavailable (" + ev.error + "). Use the buttons.", true); };
      rec.start();
      $("micNote").textContent = "Listening. Browser speech recognition may send audio to the browser vendor's service. Nothing is saved.";
    } else {
      $("micNote").textContent = "This browser has no speech recognition. Level meter only; choose with the buttons.";
    }
    btn.setAttribute("aria-pressed", "true"); $("micLabel").textContent = "Listening — tap to stop";
    audio = { stop() { cancelAnimationFrame(raf); stream.getTracks().forEach((t) => t.stop()); ctx.close(); try { rec && rec.stop(); } catch {} audio = null; btn.setAttribute("aria-pressed", "false"); $("micLabel").textContent = "Say yes or no"; } };
    setTimeout(() => audio && audio.stop(), 6000);
  } catch (e) {
    toast("Microphone unavailable (" + e.name + "). Use the yes / no buttons.", true);
    $("micNote").textContent = "Microphone permission denied or unavailable. The buttons work the same way.";
  }
});

// ------------------------------------------------------------------ boot
(async () => {
  renderRaster(null); renderEncoding(null);
  { const [g, w, h] = setupCanvas($("wave")); g.strokeStyle = "#c9d2d9"; g.beginPath(); g.moveTo(0, h / 2); g.lineTo(w, h / 2); g.stroke(); }
  try { S.config = await api("/config"); } catch { toast("Backend not reachable. Start it with ./scripts/run_local.sh", true); }
  await refresh(); connect();
  window.addEventListener("resize", () => { renderRaster(S.lastTrial); });
})();
