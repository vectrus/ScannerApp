/* ============================================================
 * BoekScanner — frontend logic
 * Pure ES2020 JavaScript (geen frameworks). Werkt offline.
 * ============================================================ */

const api = {
  base: "",
  async get(path) {
    const r = await fetch(this.base + path);
    if (!r.ok) throw await this._error(r);
    return r.headers.get("content-type")?.includes("application/json")
      ? r.json() : r.text();
  },
  async post(path, body, opts = {}) {
    const r = await fetch(this.base + path, {
      method: "POST",
      headers: opts.formData ? undefined : { "Content-Type": "application/json" },
      body: opts.formData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
    });
    if (!r.ok) throw await this._error(r);
    if (r.status === 204) return null;
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(this.base + path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw await this._error(r);
    return r.json();
  },
  async del(path) {
    const r = await fetch(this.base + path, { method: "DELETE" });
    if (!r.ok) throw await this._error(r);
    return null;
  },
  async _error(r) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      if (j && j.detail) detail = j.detail;
    } catch {}
    return new Error(detail);
  },
};

// --- Toast meldingen ----------------------------------------

const toastContainer = document.getElementById("toastContainer");
function toast(msg, type = "info", ms = 3500) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.3s";
    setTimeout(() => el.remove(), 300);
  }, ms);
}

// --- App-state ----------------------------------------------

const state = {
  status: null,
  projects: [],
  active: null,            // ProjectDetailOut
  activePageId: null,
  pageCache: new Map(),    // page_id -> {text, dirty}
  saveTimer: null,
  pollTimer: null,
};

// --- DOM-shortcuts ------------------------------------------

const $ = (id) => document.getElementById(id);

const els = {
  statusIndicator: $("statusIndicator"),
  statusText: $("statusText"),
  statusDot: () => els.statusIndicator.querySelector(".dot"),
  inboxPathDisplay: $("inboxPathDisplay"),

  updateBtn: $("updateBtn"),
  helpBtn: $("helpBtn"),
  emptyHelpBtn: $("emptyHelpBtn"),
  helpDialog: $("helpDialog"),
  helpBody: $("helpBody"),
  helpCloseBtn: $("helpCloseBtn"),
  helpPrintBtn: $("helpPrintBtn"),
  welcomeDialog: $("welcomeDialog"),
  welcomeReadHelp: $("welcomeReadHelp"),
  welcomeStart: $("welcomeStart"),
  welcomeDontShow: $("welcomeDontShow"),

  projectPicker: $("projectPicker"),
  newProjectBtn: $("newProjectBtn"),
  emptyNewProjectBtn: $("emptyNewProjectBtn"),
  newProjectDialog: $("newProjectDialog"),
  newProjectName: $("newProjectName"),
  newProjectDesc: $("newProjectDesc"),
  newProjectForm: $("newProjectForm"),
  cancelNewProject: $("cancelNewProject"),

  pageList: $("pageList"),
  pageCount: $("pageCount"),
  scanNowBtn: $("scanNowBtn"),
  uploadBtn: $("uploadBtn"),
  uploadInput: $("uploadInput"),

  emptyState: $("emptyState"),
  editorContent: $("editorContent"),
  pageImage: $("pageImage"),
  pageTitle: $("pageTitle"),
  reprocessBtn: $("reprocessBtn"),
  deletePageBtn: $("deletePageBtn"),
  ocrText: $("ocrText"),
  saveTextBtn: $("saveTextBtn"),
  checkSpellingBtn: $("checkSpellingBtn"),
  saveStatus: $("saveStatus"),
  spellResults: $("spellResults"),
  confidenceBadge: $("confidenceBadge"),

  exportBar: $("exportBar"),
  exportBtn: $("exportBtn"),
  cbCombined: $("cbCombined"),
  cbPerPage: $("cbPerPage"),
};

// --- Updates ------------------------------------------------

let lastUpdateCheck = null;

async function checkForUpdate(silent = false) {
  try {
    const info = await api.get("/api/update/check");
    lastUpdateCheck = info;
    if (!info.enabled) {
      els.updateBtn.classList.add("hidden");
      return info;
    }
    if (!info.configured) {
      els.updateBtn.title = info.message || "Updates nog niet ingesteld";
      if (!silent) toast(info.message || "Updates nog niet ingesteld.", "warning", 6000);
      return info;
    }
    if (info.available) {
      els.updateBtn.classList.add("update-available");
      els.updateBtn.innerHTML = "⬇ Update klaar";
      els.updateBtn.title = `Nieuwe versie beschikbaar: ${info.release_name || info.remote_build_id}`;
      if (!silent) toast("Nieuwe update beschikbaar.", "success");
    } else {
      els.updateBtn.classList.remove("update-available");
      els.updateBtn.innerHTML = "🔄 Update";
      els.updateBtn.title = "BoekScanner is up-to-date";
      if (!silent) toast("BoekScanner is up-to-date.", "success");
    }
    return info;
  } catch (err) {
    if (!silent) toast("Update-check mislukt: " + err.message, "warning", 6000);
    return null;
  }
}

async function installUpdate() {
  const info = lastUpdateCheck || await checkForUpdate(true);
  if (!info) return;
  if (!info.available) {
    await checkForUpdate(false);
    return;
  }
  const label = info.release_name || info.remote_build_id || "nieuwste versie";
  if (!confirm(`Update naar ${label} installeren?\n\nBoekScanner sluit zichzelf en start daarna opnieuw.`)) {
    return;
  }
  const original = els.updateBtn.innerHTML;
  els.updateBtn.disabled = true;
  els.updateBtn.innerHTML = "⏳ Updaten…";
  try {
    const result = await api.post("/api/update/install", {});
    toast(result.message || "Update wordt geïnstalleerd.", "success", 8000);
  } catch (err) {
    els.updateBtn.disabled = false;
    els.updateBtn.innerHTML = original;
    toast("Update installeren mislukt: " + err.message, "error", 8000);
  }
}

els.updateBtn.addEventListener("click", installUpdate);

// --- Status / Tesseract -------------------------------------

async function refreshStatus() {
  try {
    state.status = await api.get("/api/status");
    const ts = state.status;
    els.inboxPathDisplay.textContent = ts.inbox_dir;
    if (ts.tesseract_available) {
      els.statusDot().className = "dot dot-green";
      els.statusText.textContent = `Tesseract ${ts.tesseract_version} (${ts.tesseract_languages.length} talen)`;
    } else {
      els.statusDot().className = "dot dot-red";
      els.statusText.textContent = "Tesseract niet gevonden — voer installer uit";
    }
  } catch (err) {
    els.statusDot().className = "dot dot-red";
    els.statusText.textContent = "Server onbereikbaar";
  }
}

// --- Projecten ----------------------------------------------

async function refreshProjects() {
  state.projects = await api.get("/api/projects");
  els.projectPicker.innerHTML = '<option value="">— Kies een boek —</option>';
  for (const p of state.projects) {
    const opt = document.createElement("option");
    opt.value = p.slug;
    opt.textContent = `${p.name} (${p.pages} pagina${p.pages === 1 ? "" : "'s"})`;
    if (state.active && p.slug === state.active.slug) opt.selected = true;
    els.projectPicker.appendChild(opt);
  }
}

async function loadActiveProject() {
  try {
    state.active = await api.get("/api/projects/active");
    renderProject();
  } catch {
    state.active = null;
    renderProject();
  }
}

function renderProject() {
  const has = state.active != null;
  els.scanNowBtn.disabled = !has;
  els.uploadBtn.disabled = !has;
  els.exportBar.classList.toggle("hidden", !has);

  if (!has) {
    els.emptyState.classList.remove("hidden");
    els.editorContent.classList.add("hidden");
    els.pageList.innerHTML = "";
    els.pageCount.textContent = "0";
    return;
  }

  // Page-list
  els.pageCount.textContent = String(state.active.pages.length);
  els.pageList.innerHTML = "";
  for (const page of state.active.pages) {
    els.pageList.appendChild(renderPageItem(page));
  }

  // Editor
  if (state.active.pages.length === 0) {
    els.emptyState.classList.remove("hidden");
    els.emptyState.querySelector("h2").textContent = state.active.name;
    els.emptyState.querySelector("p").textContent = "Nog geen pagina's. Klik op 'Scan nu' of voeg bestanden toe.";
    els.emptyState.querySelector("button").classList.add("hidden");
    els.editorContent.classList.add("hidden");
  } else {
    els.emptyState.classList.add("hidden");
    els.editorContent.classList.remove("hidden");
    if (!state.activePageId || !state.active.pages.find(p => p.id === state.activePageId)) {
      state.activePageId = state.active.pages[0].id;
    }
    selectPage(state.activePageId);
  }
}

function renderPageItem(page) {
  const li = document.createElement("li");
  li.className = "page-item";
  li.dataset.pageId = page.id;
  if (page.id === state.activePageId) li.classList.add("active");
  li.draggable = true;
  li.innerHTML = `
    <img class="thumb" src="${page.has_thumb ? `/api/pages/${page.id}/thumb?t=${Date.now()}` : ""}"
         alt="Thumb pagina ${page.index}"
         onerror="this.style.visibility='hidden'" />
    <div class="meta">
      <span class="num">Pagina ${page.index}</span>
      <span class="preview">${escapeHtml(page.text_preview || "(nog geen tekst)")}</span>
      ${page.avg_confidence != null
        ? `<span class="conf">${Math.round(page.avg_confidence)}% zeker</span>`
        : ""}
    </div>
  `;
  li.addEventListener("click", () => selectPage(page.id));
  attachDnd(li);
  return li;
}

// --- Drag & drop reorder ------------------------------------

let dragSrcId = null;

function attachDnd(li) {
  li.addEventListener("dragstart", (e) => {
    dragSrcId = li.dataset.pageId;
    li.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });
  li.addEventListener("dragend", () => {
    li.classList.remove("dragging");
    document.querySelectorAll(".page-item").forEach(el => el.classList.remove("drag-over"));
  });
  li.addEventListener("dragover", (e) => {
    e.preventDefault();
    li.classList.add("drag-over");
  });
  li.addEventListener("dragleave", () => li.classList.remove("drag-over"));
  li.addEventListener("drop", async (e) => {
    e.preventDefault();
    li.classList.remove("drag-over");
    const targetId = li.dataset.pageId;
    if (!dragSrcId || dragSrcId === targetId) return;
    const ids = state.active.pages.map(p => p.id);
    const from = ids.indexOf(dragSrcId);
    const to = ids.indexOf(targetId);
    ids.splice(to, 0, ids.splice(from, 1)[0]);
    try {
      await api.post("/api/pages/reorder", { page_ids: ids });
      await loadActiveProject();
      toast("Volgorde opgeslagen", "success");
    } catch (err) {
      toast("Kon volgorde niet opslaan: " + err.message, "error");
    }
  });
}

// --- Pagina selecteren / tekst inladen ----------------------

async function selectPage(pageId) {
  state.activePageId = pageId;
  document.querySelectorAll(".page-item").forEach(el => {
    el.classList.toggle("active", el.dataset.pageId === pageId);
  });
  const page = state.active.pages.find(p => p.id === pageId);
  if (!page) return;

  els.pageTitle.textContent = `Pagina ${page.index}`;
  els.pageImage.src = `/api/pages/${pageId}/image?processed=true&t=${Date.now()}`;

  // Confidence badge
  if (page.avg_confidence != null) {
    const c = page.avg_confidence;
    let cls = "low";
    if (c >= 85) cls = "high";
    else if (c >= 70) cls = "medium";
    els.confidenceBadge.className = `conf-badge ${cls}`;
    els.confidenceBadge.textContent = `OCR-zekerheid: ${Math.round(c)}%`;
  } else {
    els.confidenceBadge.className = "conf-badge";
    els.confidenceBadge.textContent = "Nog niet OCR'd";
  }

  // Tekst inladen (uit cache of API)
  let text;
  if (state.pageCache.has(pageId)) {
    text = state.pageCache.get(pageId).text;
  } else {
    try {
      text = await api.get(`/api/pages/${pageId}/text`);
    } catch {
      text = "";
    }
    state.pageCache.set(pageId, { text, dirty: false });
  }
  els.ocrText.value = text || "";
  els.spellResults.classList.add("hidden");
  els.saveStatus.textContent = "";
}

// --- Tekst-bewerking ----------------------------------------

els.ocrText.addEventListener("input", () => {
  if (!state.activePageId) return;
  state.pageCache.set(state.activePageId, { text: els.ocrText.value, dirty: true });
  els.saveStatus.textContent = "Niet opgeslagen…";
  els.saveStatus.style.color = "var(--warning)";
  // Auto-save na 1.5s stilte
  if (state.saveTimer) clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(saveCurrentPage, 1500);
});

async function saveCurrentPage(showToast = false) {
  if (!state.activePageId) return;
  const cache = state.pageCache.get(state.activePageId);
  if (!cache || !cache.dirty) return;
  try {
    await api.put(`/api/pages/${state.activePageId}/text`, { text: cache.text });
    cache.dirty = false;
    els.saveStatus.textContent = "✓ Opgeslagen";
    els.saveStatus.style.color = "var(--success)";
    if (showToast) toast("Tekst opgeslagen", "success", 1500);
  } catch (err) {
    toast("Opslaan mislukt: " + err.message, "error");
  }
}

els.saveTextBtn.addEventListener("click", () => saveCurrentPage(true));

// --- Spellingscontrole --------------------------------------

els.checkSpellingBtn.addEventListener("click", async () => {
  if (!state.activePageId) return;
  await saveCurrentPage();
  try {
    const suggestions = await api.get(`/api/pages/${state.activePageId}/spellcheck?language=nl-NL`);
    if (suggestions.length === 0) {
      els.spellResults.classList.remove("hidden");
      els.spellResults.innerHTML = "<strong>✓ Geen spellingsproblemen gevonden.</strong>";
      return;
    }
    const text = els.ocrText.value;
    els.spellResults.classList.remove("hidden");
    els.spellResults.innerHTML = `<strong>${suggestions.length} suggestie(s):</strong>` +
      suggestions.slice(0, 50).map(s => {
        const word = text.substr(s.offset, s.length);
        const sugg = s.suggestions.length
          ? ` → ${s.suggestions.slice(0, 3).map(x => `<em>${escapeHtml(x)}</em>`).join(" / ")}`
          : "";
        return `<div class="spell-item"><strong>${escapeHtml(word)}</strong>${sugg}<br>
          <small>${escapeHtml(s.message)}</small></div>`;
      }).join("");
  } catch (err) {
    toast("Spellingscontrole niet beschikbaar: " + err.message, "warning");
  }
});

// --- Reprocess / verwijder ---------------------------------

els.reprocessBtn.addEventListener("click", async () => {
  if (!state.activePageId) return;
  try {
    els.reprocessBtn.disabled = true;
    els.reprocessBtn.textContent = "⏳ Bezig…";
    await api.post(`/api/pages/${state.activePageId}/reprocess`, { rerun_ocr: true });
    state.pageCache.delete(state.activePageId);
    await loadActiveProject();
    toast("Pagina opnieuw verwerkt", "success");
  } catch (err) {
    toast("Verwerken mislukt: " + err.message, "error");
  } finally {
    els.reprocessBtn.disabled = false;
    els.reprocessBtn.innerHTML = "🔄 Opnieuw verwerken";
  }
});

els.deletePageBtn.addEventListener("click", async () => {
  if (!state.activePageId) return;
  if (!confirm("Deze pagina permanent verwijderen?")) return;
  try {
    await api.del(`/api/pages/${state.activePageId}`);
    state.pageCache.delete(state.activePageId);
    state.activePageId = null;
    await loadActiveProject();
    toast("Pagina verwijderd", "success");
  } catch (err) {
    toast("Verwijderen mislukt: " + err.message, "error");
  }
});

// --- Upload (drag & drop in venster + knop) -----------------

els.uploadBtn.addEventListener("click", () => els.uploadInput.click());
els.uploadInput.addEventListener("change", async (e) => {
  if (!e.target.files || e.target.files.length === 0) return;
  await uploadFiles([...e.target.files]);
  e.target.value = "";
});

async function uploadFiles(files) {
  if (!state.active) {
    toast("Open eerst een boek.", "warning");
    return;
  }
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  try {
    toast(`Bezig met ${files.length} bestand(en) te verwerken…`, "info");
    await api.post("/api/pages/upload", fd, { formData: true });
    await loadActiveProject();
    toast(`${files.length} bestand(en) verwerkt`, "success");
  } catch (err) {
    toast("Upload mislukt: " + err.message, "error");
  }
}

// Native drag-and-drop op de hele app
window.addEventListener("dragover", (e) => {
  if (e.dataTransfer && [...e.dataTransfer.types].includes("Files")) {
    e.preventDefault();
  }
});
window.addEventListener("drop", async (e) => {
  if (!e.dataTransfer || !e.dataTransfer.files.length) return;
  e.preventDefault();
  await uploadFiles([...e.dataTransfer.files]);
});

// --- Scan nu (WIA) ------------------------------------------

els.scanNowBtn.addEventListener("click", async () => {
  if (!state.active) return;
  els.scanNowBtn.disabled = true;
  const original = els.scanNowBtn.innerHTML;
  els.scanNowBtn.innerHTML = "⏳ Aan het scannen…";
  try {
    await api.post("/api/scan", { dpi: 300, color: "color", output_format: "png" });
    // Wacht even op de watcher en herlaad
    await new Promise(r => setTimeout(r, 1500));
    await loadActiveProject();
    toast("Pagina gescand", "success");
  } catch (err) {
    toast("Scannen mislukt: " + err.message, "error");
  } finally {
    els.scanNowBtn.disabled = false;
    els.scanNowBtn.innerHTML = original;
  }
});

// --- Project-picker / nieuw boek ----------------------------

els.projectPicker.addEventListener("change", async (e) => {
  const slug = e.target.value;
  if (!slug) return;
  try {
    state.active = await api.post(`/api/projects/${slug}/open`, {});
    state.activePageId = null;
    state.pageCache.clear();
    renderProject();
  } catch (err) {
    toast("Boek openen mislukt: " + err.message, "error");
  }
});

function openNewProjectDialog() {
  els.newProjectName.value = "";
  els.newProjectDesc.value = "";
  els.newProjectDialog.showModal();
  setTimeout(() => els.newProjectName.focus(), 50);
}

els.newProjectBtn.addEventListener("click", openNewProjectDialog);
els.emptyNewProjectBtn.addEventListener("click", openNewProjectDialog);
els.cancelNewProject.addEventListener("click", () => els.newProjectDialog.close());
els.newProjectForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = els.newProjectName.value.trim();
  if (!name) return;
  try {
    state.active = await api.post("/api/projects", {
      name,
      description: els.newProjectDesc.value.trim(),
    });
    state.activePageId = null;
    state.pageCache.clear();
    els.newProjectDialog.close();
    await refreshProjects();
    renderProject();
    toast(`Boek '${name}' aangemaakt`, "success");
  } catch (err) {
    toast("Aanmaken mislukt: " + err.message, "error");
  }
});

// --- Export -------------------------------------------------

els.exportBtn.addEventListener("click", async () => {
  if (!state.active) return;
  const formats = [...document.querySelectorAll('.export-controls input[type="checkbox"][value]')]
    .filter(cb => cb.checked).map(cb => cb.value);
  if (formats.length === 0) {
    toast("Kies minstens één formaat", "warning");
    return;
  }
  await saveCurrentPage();
  els.exportBtn.disabled = true;
  const original = els.exportBtn.innerHTML;
  els.exportBtn.innerHTML = "⏳ Bezig met exporteren…";
  try {
    const result = await api.post("/api/export", {
      formats,
      per_page: els.cbPerPage.checked,
      combined: els.cbCombined.checked,
    });
    showExportResults(result.files);
  } catch (err) {
    toast("Exporteren mislukt: " + err.message, "error", 6000);
  } finally {
    els.exportBtn.disabled = false;
    els.exportBtn.innerHTML = original;
  }
});

function showExportResults(files) {
  if (!files.length) {
    toast("Geen bestanden gegenereerd", "warning");
    return;
  }
  // Modal-achtige toast met download-links
  const div = document.createElement("div");
  div.className = "toast success";
  div.style.maxWidth = "500px";
  div.innerHTML = `
    <strong>✓ ${files.length} bestand(en) klaar:</strong>
    <ul style="margin: 8px 0 0; padding-left: 18px;">
      ${files.map(f => `<li><a href="${f.download_url}" target="_blank" download>${escapeHtml(f.label)}</a> <small>(${formatSize(f.size_bytes)})</small></li>`).join("")}
    </ul>
    <button style="margin-top: 8px;" onclick="this.parentElement.remove()" class="btn btn-secondary">Sluiten</button>
  `;
  div.style.pointerEvents = "auto";
  toastContainer.appendChild(div);
  // Niet auto-removen
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// --- Helpers ------------------------------------------------

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// --- Polling voor watcher-updates ---------------------------

function startPolling() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    if (!state.active) return;
    try {
      const fresh = await api.get("/api/projects/active");
      if (fresh.pages.length !== state.active.pages.length) {
        state.active = fresh;
        renderProject();
      }
    } catch {}
  }, 3000);
}

// --- Hulp / welkom -----------------------------------------

const HELP_LS_KEY = "boekscanner.welcomeShown.v1";
let helpLoaded = false;

async function loadHelpContent() {
  if (helpLoaded) return;
  try {
    const html = await api.get("/help.html");
    els.helpBody.innerHTML = html;
    helpLoaded = true;
    // Anchor links binnen de help moeten niet naar #/ navigeren maar binnen scrollen
    els.helpBody.querySelectorAll('a[href^="#"]').forEach(a => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const id = a.getAttribute("href").slice(1);
        const target = els.helpBody.querySelector(`#${CSS.escape(id)}`);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  } catch (err) {
    els.helpBody.innerHTML = `<div style="padding:40px"><h2>Hulp niet beschikbaar</h2>
      <p>${escapeHtml(err.message)}</p>
      <p>Open in plaats daarvan het bestand <code>HANDLEIDING.md</code> in
      de installatiemap.</p></div>`;
    helpLoaded = true;
  }
}

async function openHelp(sectionId = null) {
  await loadHelpContent();
  if (!els.helpDialog.open) els.helpDialog.showModal();
  if (sectionId) {
    setTimeout(() => {
      const target = els.helpBody.querySelector(`#${CSS.escape(sectionId)}`);
      if (target) target.scrollIntoView({ block: "start" });
    }, 50);
  } else {
    els.helpBody.scrollTop = 0;
  }
}

function closeHelp() {
  if (els.helpDialog.open) els.helpDialog.close();
}

els.helpBtn.addEventListener("click", () => openHelp());
els.emptyHelpBtn.addEventListener("click", () => openHelp());
els.helpCloseBtn.addEventListener("click", closeHelp);
els.helpPrintBtn.addEventListener("click", () => window.print());

// Sluit welkom-popup automatisch met Esc / klik buiten
els.helpDialog.addEventListener("click", (e) => {
  // Klik op de backdrop sluit; klikken op interne elementen niet
  const rect = els.helpDialog.getBoundingClientRect();
  if (e.clientX < rect.left || e.clientX > rect.right ||
      e.clientY < rect.top || e.clientY > rect.bottom) {
    closeHelp();
  }
});

// Welkom-popup ----------------------------------------------

function maybeShowWelcome() {
  let alreadyShown = false;
  try {
    alreadyShown = localStorage.getItem(HELP_LS_KEY) === "1";
  } catch {}
  if (alreadyShown) return;
  setTimeout(() => els.welcomeDialog.showModal(), 400);
}

function dismissWelcome() {
  if (els.welcomeDialog.open) els.welcomeDialog.close();
  if (els.welcomeDontShow.checked) {
    try { localStorage.setItem(HELP_LS_KEY, "1"); } catch {}
  }
}

els.welcomeReadHelp.addEventListener("click", async () => {
  dismissWelcome();
  await openHelp("h-welkom");
});
els.welcomeStart.addEventListener("click", () => {
  dismissWelcome();
});

// --- Init ---------------------------------------------------

(async function init() {
  await refreshStatus();
  await refreshProjects();
  await loadActiveProject();
  startPolling();
  setInterval(refreshStatus, 15000);
  await checkForUpdate(true);
  setInterval(() => checkForUpdate(true), 60 * 60 * 1000);
  maybeShowWelcome();
})();
