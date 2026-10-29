"use strict";
const $ = (s, r = document) => r.querySelector(s);
const state = { jobs: [], sel: null, styles: null, chosen: null, textMods: {}, mods: {}, pending: new Set() };
const SLIDERS = [["brightness", "Brightness"], ["contrast", "Contrast"], ["warmth", "Warmth"], ["saturation", "Colour"],
  ["clarity", "Clarity"], ["grain", "Grain"], ["fade", "Matte fade"], ["vignette", "Vignette"]];

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

// ---------------------------------------------------------------- upload
function xhrUpload(files) {
  return new Promise((resolve, reject) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    const x = new XMLHttpRequest();
    x.open("POST", "/api/upload");
    const bar = $("#uploadBar");
    const total = [...files].reduce((n, f) => n + f.size, 0);
    bar.hidden = false;
    x.upload.onprogress = e => {
      const f = e.lengthComputable ? e.loaded / e.total : 0;
      $("#uploadFill").style.width = Math.round(f * 100) + "%";
      $("#uploadText").textContent = `Uploading ${files.length} photo${files.length > 1 ? "s" : ""} · ${Math.round(f * 100)}% of ${(total / 1048576).toFixed(1)} MB`;
    };
    x.onload = () => { bar.hidden = true; x.status < 300 ? resolve(JSON.parse(x.responseText)) : reject(new Error(x.statusText || "upload failed")); };
    x.onerror = () => { bar.hidden = true; reject(new Error("network error")); };
    x.send(fd);
  });
}
async function upload(files) {
  if (!files.length) return;
  try {
    const res = await xhrUpload(files);
    if (res.errors.length) alert(res.errors.map(e => `${e.name}: ${e.error}`).join("\n"));
    await refresh();
    if (res.jobs.length) select(res.jobs[0].id);
  } catch (e) { alert("Upload failed: " + e.message); }
}
for (const id of ["#file", "#cam"]) $(id).addEventListener("change", e => { upload([...e.target.files]); e.target.value = ""; });
["dragenter", "dragover"].forEach(t => document.addEventListener(t, e => { e.preventDefault(); document.body.classList.add("over"); }));
["dragleave", "drop"].forEach(t => document.addEventListener(t, e => { e.preventDefault(); document.body.classList.remove("over"); }));
document.addEventListener("drop", e => upload([...e.dataTransfer.files]));

// ---------------------------------------------------------------- queue
const label = j => ({ awaiting_style: "choose a look", queued: "queued", running: j.stage || "editing", done: "ready", error: "failed" }[j.status]);
function renderQueue() {
  const q = $("#queue");
  q.innerHTML = "";
  for (const j of state.jobs) {
    const d = document.createElement("div");
    d.className = "thumb" + (j.id === state.sel ? " sel" : "");
    const img = j.has_preview ? "after" : "before";
    d.innerHTML = `<img src="${j.has_thumb || j.has_preview ? `/api/jobs/${j.id}/image/${img}?v=${j.version}` : ""}" alt="">
      <div class="meta"><div class="nm"></div><div class="st ${j.status}"></div>
      ${j.status === "running" || j.status === "queued" ? `<div class="mini"><i style="width:${Math.round(j.progress * 100)}%"></i></div>` : ""}</div>
      <button class="x" title="Remove">&times;</button>`;
    $(".nm", d).textContent = j.name;
    $(".st", d).textContent = label(j) + (j.status === "error" ? ": " + j.error : "");
    d.onclick = () => select(j.id);
    $(".x", d).onclick = async e => { e.stopPropagation(); await api(`/api/jobs/${j.id}`, { method: "DELETE" }); if (state.sel === j.id) state.sel = null; refresh(); };
    q.appendChild(d);
  }
}

function select(id) { state.sel = id; renderAll(); }
const cur = () => state.jobs.find(j => j.id === state.sel);

// ---------------------------------------------------------------- viewer
function renderViewer() {
  const j = cur();
  document.body.classList.toggle("has-job", !!j);
  $("#dropzone").hidden = !!j;
  $("#viewer").hidden = !j;
  $("#panel").hidden = !j;
  if (!j) return;
  const b = $("#imgBefore"), a = $("#imgAfter");
  const bs = j.has_thumb ? `/api/jobs/${j.id}/image/before?v=${j.version}` : "";
  const as = j.has_preview ? `/api/jobs/${j.id}/image/after?v=${j.version}` : "";
  if (b.dataset.src !== bs) { b.src = bs; b.dataset.src = bs; }
  if (a.dataset.src !== as) { a.src = as; a.dataset.src = as; }
  a.style.display = as ? "" : "none";
  $("#handle").style.display = as ? "" : "none";
  $("#afterTag").style.display = as ? "" : "none";
  if (!as) $("#compare").style.setProperty("--pos", "100%");
  else if (!$("#compare").dataset.moved) $("#compare").style.setProperty("--pos", "50%");
  $("#fileName").textContent = j.name;
  const busy = j.status === "running" || j.status === "queued";
  $("#busy").hidden = !(busy && !j.has_preview);
  $("#busyText").textContent = j.stage || "working…";
  $("#progressWrap").hidden = !busy;
  $("#progressBar").style.width = Math.round(j.progress * 100) + "%";
  $("#stageText").textContent = j.has_preview && busy ? "Preview ready — rendering full resolution: " + j.stage : j.stage;
  $("#downloads").innerHTML = "";
  for (const [k, url] of Object.entries(j.downloads || {})) {
    if (k === "sidecar") continue;
    const el = document.createElement("a");
    el.href = url; el.textContent = "Download " + ({ jpg: "JPEG", tif: "TIFF", png: "PNG" }[k] || k);
    $("#downloads").appendChild(el);
  }
  if (j.downloads && j.downloads.jpg && navigator.canShare) {       // phones: straight to Photos / share sheet
    const b = document.createElement("button");
    b.textContent = "Save / Share";
    b.onclick = async () => {
      try {
        const blob = await (await fetch(j.downloads.jpg)).blob();
        const file = new File([blob], j.name.replace(/\.[^.]+$/, "") + "_edit.jpg", { type: "image/jpeg" });
        if (navigator.canShare({ files: [file] })) await navigator.share({ files: [file] });
        else location.href = j.downloads.jpg;
      } catch (e) { if (e.name !== "AbortError") location.href = j.downloads.jpg; }
    };
    $("#downloads").prepend(b);
  }
}
(function () {
  const c = $("#compare");
  let drag = false;
  const move = e => {
    const r = c.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
    c.style.setProperty("--pos", Math.max(0, Math.min(100, (x / r.width) * 100)) + "%");
    c.dataset.moved = "1";
  };
  c.addEventListener("pointerdown", e => { if (e.target.closest(".busy")) return; drag = true; move(e); });
  window.addEventListener("pointermove", e => drag && move(e));
  ["pointerup", "pointercancel"].forEach(t => window.addEventListener(t, () => (drag = false)));
})();

// ---------------------------------------------------------------- panel
function renderPanel() {
  const j = cur();
  if (!j) return;
  const list = $("#styleList");
  if (!state.styles) return;
  if (!list.dataset.built) {
    for (const [cat, items] of Object.entries(state.styles.categories)) {
      const h = document.createElement("div"); h.className = "cat"; h.textContent = cat; list.appendChild(h);
      const g = document.createElement("div"); g.className = "styles";
      for (const s of items) {
        const b = document.createElement("button");
        b.className = "style"; b.dataset.id = s.id;
        b.innerHTML = `<b></b><span></span>`;
        $("b", b).textContent = s.name; $("span", b).textContent = s.description;
        b.onclick = () => { state.chosen = s.id; state.textMods = {}; $("#matchNote").textContent = ""; $("#lookText").value = ""; markStyle(); };
        g.appendChild(b);
      }
      list.appendChild(g);
    }
    list.dataset.built = "1";
    const sl = $("#sliders");
    for (const [k, nm] of SLIDERS) {
      const row = document.createElement("div"); row.className = "sl";
      const min = ["grain", "fade", "vignette"].includes(k) ? 0 : -100;
      row.innerHTML = `<span>${nm}</span><input type="range" min="${min}" max="100" value="0" data-k="${k}"><output>0</output>`;
      const inp = $("input", row);
      inp.oninput = () => { $("output", row).textContent = inp.value; state.mods[k] = inp.value / 100; };
      sl.appendChild(row);
    }
  }
  if (j.id !== state.panelFor) {                 // load the job's last settings
    state.panelFor = j.id;
    state.chosen = j.style || state.styles.default;
    $("#strength").value = Math.round(j.strength * 100); $("#strengthOut").textContent = Math.round(j.strength * 100) + "%";
    $("#lookText").value = j.text || "";
    state.mods = { ...(j.modifiers || {}) }; state.textMods = {};
    document.querySelectorAll("#sliders input").forEach(i => { const v = Math.round((state.mods[i.dataset.k] || 0) * 100); i.value = v; i.nextElementSibling.textContent = v; });
    markStyle();
    renderNotes(j);
  }
  const busy = j.status === "running" || j.status === "queued";
  $("#editBtn").disabled = busy;
  $("#editBtn").textContent = busy ? "Editing…" : j.status === "done" ? "Re-edit with these settings" : "Edit photo";
}
function markStyle() { document.querySelectorAll(".style").forEach(b => b.classList.toggle("sel", b.dataset.id === state.chosen && !$("#lookText").value)); }
function renderNotes(j) {
  const n = $("#notes");
  if (!j.notes || !j.notes.length) { n.innerHTML = ""; return; }
  n.innerHTML = "<h3>What I did</h3><ul></ul>";
  for (const t of j.notes) { const li = document.createElement("li"); li.textContent = t; $("ul", n).appendChild(li); }
}
$("#strength").oninput = e => ($("#strengthOut").textContent = e.target.value + "%");
$("#matchBtn").onclick = async () => {
  const t = $("#lookText").value.trim(); if (!t) return;
  const m = await api("/api/match", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: t }) });
  state.chosen = m.style; state.textMods = m.modifiers;
  const extra = Object.entries(m.modifiers).map(([k, v]) => `${k} ${v > 0 ? "+" : ""}${v.toFixed(1)}`).join(", ");
  $("#matchNote").textContent = `→ ${m.name}${extra ? " (" + extra + ")" : ""}`;
  document.querySelectorAll(".style").forEach(b => b.classList.toggle("sel", b.dataset.id === m.style));
};
$("#lookText").addEventListener("keydown", e => { if (e.key === "Enter") $("#matchBtn").click(); });

$("#editBtn").onclick = async () => {
  const targets = $("#applyAll").checked ? state.jobs.filter(j => j.status === "awaiting_style" || j.id === state.sel) : [cur()];
  const formats = [...document.querySelectorAll(".fmt:checked")].map(x => x.value);
  const ms = $("#maxSide").value;
  const text = $("#lookText").value.trim();
  const body = {
    style: state.chosen, strength: $("#strength").value / 100,
    modifiers: { ...state.textMods, ...state.mods }, formats: formats.length ? formats : ["jpg"],
    max_side: ms ? parseInt(ms) : null,
  };
  for (const j of targets) {
    try { await api(`/api/jobs/${j.id}/edit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }
    catch (e) { alert(j.name + ": " + e.message); }
  }
  refresh();
};

// ---------------------------------------------------------------- loop
function renderAll() { renderQueue(); renderViewer(); renderPanel(); }
async function refresh() {
  try { state.jobs = await api("/api/jobs"); } catch { return; }
  if (state.sel && !state.jobs.find(j => j.id === state.sel)) state.sel = null;
  if (!state.sel && state.jobs.length) state.sel = state.jobs[0].id;
  const j = cur();
  if (j && j.status === "done" && j.id === state.panelFor) renderNotes(j);
  renderAll();
}
(async function init() {
  state.styles = await api("/api/styles");
  await refresh();
  setInterval(refresh, 1200);
})();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
