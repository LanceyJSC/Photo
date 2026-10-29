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
  const showing = state.previewing && j.status !== "running" && j.status !== "queued";
  if (!showing) {
    if (a.dataset.src !== as) { a.src = as; a.dataset.src = as; }
    a.style.display = as ? "" : "none";
    $("#handle").style.display = as ? "" : "none";
    $("#afterTag").style.display = as ? "" : "none";
    if (!as) $("#compare").style.setProperty("--pos", "100%");
    else if (!$("#compare").dataset.moved) $("#compare").style.setProperty("--pos", "50%");
  }
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

// ---------------------------------------------------------------- panel (look picker)
let tiles = {};            // style id -> tile element
function buildTiles() {
  const list = $("#styleList");
  if (list.dataset.built || !state.styles) return;
  list.dataset.built = "1";
  const mk = (title, id) => {
    const h = document.createElement("div"); h.className = "cat"; h.textContent = title; h.id = id || ""; list.appendChild(h);
    const g = document.createElement("div"); g.className = "tiles"; list.appendChild(g); return g;
  };
  state.recGrid = mk("Best for this photo", "recHead");
  state.cats = {};
  for (const [cat, items] of Object.entries(state.styles.categories)) {
    const g = mk(cat);
    g.previousSibling.dataset.cat = cat;
    for (const s of items) {
      const t = tile(s);
      g.appendChild(t);
    }
  }
}
function tile(s, clone) {
  const b = document.createElement("button");
  b.className = "tile"; b.dataset.id = s.id;
  b.innerHTML = '<div class="ph"><img alt="" loading="lazy" draggable="false"></div><b></b><small></small>';
  const parts = s.name.split(" – ");
  $("b", b).textContent = s.photographer ? parts[0] : (parts[1] || parts[0]);
  $("small", b).textContent = s.photographer ? (parts[1] || "") : s.category;
  b.title = s.description;
  b.dataset.search = (s.name + " " + s.category + " " + s.description + " " + (s.keywords || []).join(" ")).toLowerCase();
  b.onclick = () => choose(s.id);
  (tiles[s.id] = tiles[s.id] || []).push(b);
  return b;
}
function allStyles() { return Object.values(state.styles.categories).flat(); }
function choose(id) {
  state.chosen = id;
  markChosen();
  const j = cur(); if (!j) return;
  const opt = `/api/jobs/${j.id}/option/${id}`;
  // show the chosen look large straight away (before the full-quality edit exists)
  const a = $("#imgAfter"); a.src = opt; a.dataset.src = opt; a.style.display = ""; state.previewing = id;
  $("#handle").style.display = ""; $("#afterTag").style.display = "";
  const c = $("#compare"); if (!c.dataset.moved) c.style.setProperty("--pos", "0%");
  updateEditBtn();
}
function markChosen() {
  document.querySelectorAll(".tile").forEach(t => t.classList.toggle("sel", t.dataset.id === state.chosen));
}
function updateEditBtn() {
  const j = cur(); const b = $("#editBtn");
  const busy = j && (j.status === "running" || j.status === "queued");
  const name = state.chosen ? allStyles().find(s => s.id === state.chosen)?.name : null;
  b.disabled = busy || !state.chosen;
  b.textContent = busy ? "Editing…" : name ? "Apply: " + name.replace(/^[^–]+–\s*/, "") : "Choose a look";
}
function refreshTiles() {
  const j = cur(); if (!j) return;
  buildTiles();
  // recommended row
  const rec = j.recommended || [];
  const g = state.recGrid;
  const sig = j.id + ":" + rec.join(",");
  if (g.dataset.sig !== sig) {
    g.dataset.sig = sig; g.innerHTML = "";
    const byId = Object.fromEntries(allStyles().map(s => [s.id, s]));
    tiles.__rec = [];
    for (const id of rec) if (byId[id]) { const t = tile(byId[id]); t.classList.add("rec"); g.appendChild(t); }
    $("#recHead").hidden = g.hidden = !rec.length;
    const kinds = { portrait: "portrait", landscape: "landscape", architecture: "architecture", night: "night scene", street: "street / general scene" };
    $("#recHead").textContent = rec.length ? `Best for this photo (looks like a ${kinds[j.kind] || "photo"})` : "";
  }
  const ready = new Set(j.options_ready || []);
  document.querySelectorAll(".tile").forEach(t => {
    const img = $("img", t), id = t.dataset.id;
    const url = ready.has(id) ? `/api/jobs/${j.id}/option/${id}` : "";
    if (img.dataset.u !== url + j.id) { img.dataset.u = url + j.id; if (url) img.src = url; else img.removeAttribute("src"); }
    t.classList.toggle("wait", !ready.has(id));
  });
  $("#panelSub").textContent = j.options_done ? "Your photo in styles chosen for it. Tap one — I do the rest."
    : `Preparing looks for your photo… ${ready.size} ready`;
  markChosen();
}
function filterTiles() {
  const q = $("#search").value.trim().toLowerCase();
  document.querySelectorAll("#styleList .tiles").forEach(g => {
    let any = false;
    g.querySelectorAll(".tile").forEach(t => { const m = !q || q.split(/\s+/).every(w => t.dataset.search.includes(w)); t.hidden = !m; any = any || m; });
    g.previousSibling.hidden = !any || (g === state.recGrid && (q || !g.children.length));
    g.hidden = !any || (g === state.recGrid && !!q);
  });
}
$("#search").addEventListener("input", filterTiles);

function renderPanel() {
  const j = cur();
  if (!j || !state.styles) return;
  if (j.id !== state.panelFor) {
    state.panelFor = j.id; state.chosen = j.style || null; state.previewing = null;
    $("#search").value = "";
    renderNotes(j);
  }
  refreshTiles(); filterTiles(); updateEditBtn();
}
function renderNotes(j) {
  const n = $("#notes");
  if (!j.notes || !j.notes.length) { n.innerHTML = ""; return; }
  n.innerHTML = "<h3>What I did</h3><ul></ul>";
  for (const t of j.notes) { const li = document.createElement("li"); li.textContent = t; $("ul", n).appendChild(li); }
}

$("#editBtn").onclick = async () => {
  if (!state.chosen) return;
  const targets = $("#applyAll").checked ? state.jobs.filter(j => j.status === "awaiting_style" || j.id === state.sel) : [cur()];
  const formats = ["jpg", ...[...document.querySelectorAll(".fmt:checked")].map(x => x.value)];
  state.previewing = null;
  for (const j of targets) {
    try {
      await api(`/api/jobs/${j.id}/edit`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ style: state.chosen, strength: 1, modifiers: {}, formats }) });
    } catch (e) { alert(j.name + ": " + e.message); }
  }
  $("#compare").dataset.moved = "";
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
