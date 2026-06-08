#!/usr/bin/env python3
"""
JSONL Review — browser-based UI (light theme, editable fields, no regex)
Serves on http://localhost:8080
"""

import json
import importlib.util
import os
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


# ── file helpers ──────────────────────────────────────────────────────────────

def load_jsonl(path: str) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(path: str, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── embedded single-page application ─────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSONL Review</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500;600&family=Geist:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #f5f4f0;
  --bg2:       #ffffff;
  --bg3:       #eeede9;
  --bg4:       #e5e4e0;
  --border:    #d8d7d3;
  --border2:   #c8c7c3;
  --text:      #1a1917;
  --text2:     #5a5855;
  --text3:     #9a9895;
  --accent:    #2563eb;
  --accent-bg: #eff4ff;
  --green:     #16a34a;
  --green-bg:  #f0fdf4;
  --red:       #dc2626;
  --red-bg:    #fef2f2;
  --dirty:     #b45309;
  --dirty-bg:  #fffbeb;

  --font-ui:   'Geist', system-ui, sans-serif;
  --font-mono: 'Geist Mono', 'Fira Code', monospace;
  --radius:    6px;
  --shadow:    0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.04);
}

body {
  font-family: var(--font-ui);
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── top bar ── */
#topbar {
  height: 42px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  box-shadow: var(--shadow);
}

#topbar-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: .02em;
}

#topbar-counts {
  font-size: 11px;
  color: var(--text3);
  font-family: var(--font-mono);
}

#topbar-status {
  margin-left: auto;
  font-size: 11px;
  font-family: var(--font-mono);
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 20px;
  opacity: 0;
  transition: opacity .3s;
}
#topbar-status.show { opacity: 1; }
#topbar-status.ok   { background: var(--green-bg); color: var(--green); }
#topbar-status.err  { background: var(--red-bg);   color: var(--red); }

/* ── layout ── */
#app {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── sidebar ── */
#sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

#sidebar-search {
  padding: 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

#search-input {
  width: 100%;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text);
  outline: none;
  transition: border-color .15s, background .15s;
}
#search-input::placeholder { color: var(--text3); }
#search-input:focus {
  border-color: var(--accent);
  background: var(--bg2);
}

#entry-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
#entry-list::-webkit-scrollbar { width: 4px; }
#entry-list::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

.entry-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background .1s;
  user-select: none;
}
.entry-item:hover { background: var(--bg3); }
.entry-item.selected {
  background: var(--accent-bg);
  border-left-color: var(--accent);
}
.entry-item.dirty .entry-name::after {
  content: ' •';
  color: var(--dirty);
}

.entry-id {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text3);
  flex-shrink: 0;
  min-width: 30px;
  text-align: right;
}
.entry-name {
  font-size: 12px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── main ── */
#main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}

#placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text3);
}
#placeholder svg { opacity: .25; }
#placeholder p { font-size: 14px; }

#detail {
  flex: 1;
  display: none;
  flex-direction: column;
  overflow: hidden;
}

/* ── section ── */
.sec {
  border-bottom: 1px solid var(--border);
  background: var(--bg2);
  flex-shrink: 0;
}

.sec-hdr {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--text3);
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  user-select: none;
}
.sec-hdr-label { flex: 1; color: var(--text2); }

/* ── entry text ── */
#entry-display {
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 10px 14px;
  max-height: 120px;
  overflow-y: auto;
  color: var(--text2);
  background: var(--bg2);
}
#entry-display::-webkit-scrollbar { width: 4px; }
#entry-display::-webkit-scrollbar-thumb { background: var(--border2); }

/* ── fields section ── */
#section-c {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-bottom: none;
}

#fields-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0 16px;
}
#fields-scroll::-webkit-scrollbar { width: 4px; }
#fields-scroll::-webkit-scrollbar-thumb { background: var(--border2); }

.field-row {
  display: flex;
  align-items: center;
  padding: 2px 14px;
  gap: 10px;
  min-height: 34px;
  border-bottom: 1px solid rgba(216,215,211,.5);
  transition: background .1s;
}
.field-row:hover { background: var(--bg3); }
.field-row.changed { background: var(--dirty-bg); }

.field-key {
  width: 180px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 4px 0;
  user-select: none;
}

.field-val {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 4px 8px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  outline: none;
  min-width: 0;
  transition: border-color .15s, box-shadow .15s;
}
.field-val:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(37,99,235,.12);
}
.field-val.modified {
  border-color: var(--dirty);
  background: var(--dirty-bg);
}

/* ── action bar ── */
#action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg2);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

#unsaved-indicator {
  font-size: 11px;
  color: var(--dirty);
  font-family: var(--font-mono);
  margin-right: auto;
  opacity: 0;
  transition: opacity .2s;
}
#unsaved-indicator.show { opacity: 1; }

/* ── buttons ── */
.btn {
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 500;
  padding: 5px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
  border: 1px solid var(--border2);
  background: var(--bg2);
  color: var(--text2);
}
.btn:hover {
  background: var(--bg3);
  color: var(--text);
  border-color: var(--border2);
}
.btn:disabled { opacity: .4; cursor: default; pointer-events: none; }

.btn-save {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.btn-save:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}

.btn-reset {
  color: var(--red);
  border-color: rgba(220,38,38,.3);
}
.btn-reset:hover {
  background: var(--red-bg);
  border-color: var(--red);
  color: var(--red);
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }
</style>
</head>
<body>

<div id="topbar">
  <span id="topbar-title">◆ JSONL Review</span>
  <span id="topbar-counts"></span>
  <span id="topbar-status"></span>
</div>

<div id="app">
  <div id="sidebar">
    <div id="sidebar-search">
      <input type="text" id="search-input" placeholder="Filter entries…" oninput="filterList(this.value)">
    </div>
    <div id="entry-list"></div>
  </div>

  <div id="main">
    <div id="placeholder">
      <svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.4"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0
             012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0
             01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
      <p>Select an entry to edit</p>
    </div>

    <div id="detail">

      <!-- Original entry text -->
      <div class="sec">
        <div class="sec-hdr">
          <span class="sec-hdr-label">Original entry</span>
          <span id="entry-id-badge" style="font-family:var(--font-mono);font-size:10px;color:var(--text3)"></span>
        </div>
        <div id="entry-display"></div>
      </div>

      <!-- Editable fields -->
      <div id="section-c" class="sec">
        <div class="sec-hdr">
          <span class="sec-hdr-label">Parsed fields</span>
        </div>
        <div id="fields-scroll">
          <div id="fields-grid"></div>
        </div>
      </div>

      <!-- Action bar -->
      <div id="action-bar">
        <span id="unsaved-indicator">● Unsaved changes</span>
        <button class="btn btn-reset" id="reset-btn" onclick="resetFields()" disabled>Reset</button>
        <button class="btn btn-save" id="save-btn" onclick="saveEntry()" disabled>Save</button>
      </div>

    </div>
  </div>
</div>

<script>
'use strict';

let DATA          = { entries: {}, parsed: [] };
let currentParsed = null;   // deep copy of selected record
let originalParsed = null;  // pristine snapshot for reset
let dirtyIds      = new Set();

// ── boot ───────────────────────────────────────────────────────────────────
async function boot() {
  const res = await fetch('/api/data');
  DATA = await res.json();
  document.getElementById('topbar-counts').textContent =
    `${DATA.parsed.length} entries`;
  renderList();
}

// ── sidebar ────────────────────────────────────────────────────────────────
function renderList(filter = '') {
  const el = document.getElementById('entry-list');
  el.innerHTML = '';
  const lc = filter.toLowerCase();
  DATA.parsed.forEach((p, i) => {
    const id   = p.entry_id ?? '?';
    const name = p.name ?? String(id);
    const label = `${id} ${name}`;
    if (lc && !label.toLowerCase().includes(lc)) return;
    const div = document.createElement('div');
    div.className = 'entry-item' + (dirtyIds.has(id) ? ' dirty' : '');
    div.dataset.i = i;
    const idSpan = document.createElement('span');
    idSpan.className = 'entry-id';
    idSpan.textContent = String(id);
    const nameSpan = document.createElement('span');
    nameSpan.className = 'entry-name';
    nameSpan.textContent = name;
    div.appendChild(idSpan);
    div.appendChild(nameSpan);
    div.onclick = () => selectEntry(i, div);
    el.appendChild(div);
  });
}

function filterList(v) { renderList(v); }

function selectEntry(idx, el) {
  document.querySelectorAll('.entry-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  showEntry(DATA.parsed[idx]);
}

// ── show entry ─────────────────────────────────────────────────────────────
function showEntry(parsed) {
  currentParsed  = JSON.parse(JSON.stringify(parsed));
  originalParsed = JSON.parse(JSON.stringify(parsed));

  document.getElementById('placeholder').style.display = 'none';
  document.getElementById('detail').style.display = 'flex';
  document.getElementById('entry-id-badge').textContent = `id: ${parsed.entry_id ?? '?'}`;
  document.getElementById('entry-display').textContent =
    DATA.entries[String(parsed.entry_id)] ?? '(not found)';

  rebuildFields(parsed);
  setDirty(false);
}

// ── fields ─────────────────────────────────────────────────────────────────
function rebuildFields(parsed) {
  const grid = document.getElementById('fields-grid');
  grid.innerHTML = '';

  Object.entries(parsed)
    .filter(([k]) => k !== 'entry_id')
    .forEach(([key, value]) => {
      const row = document.createElement('div');
      row.className = 'field-row';
      row.dataset.key = key;

      const lbl = document.createElement('div');
      lbl.className = 'field-key';
      lbl.textContent = key;
      lbl.title = key;

      const inp = document.createElement('input');
      inp.type = 'text';
      inp.className = 'field-val';
      inp.value = value == null ? '' : String(value);
      inp.dataset.key = key;
      inp.dataset.otype = value === null ? 'null' : typeof value;
      inp.dataset.original = inp.value;

      inp.addEventListener('input', () => onFieldInput(inp));

      row.appendChild(lbl);
      row.appendChild(inp);
      grid.appendChild(row);
    });
}

function onFieldInput(inp) {
  const changed = inp.value !== inp.dataset.original;
  inp.classList.toggle('modified', changed);
  inp.closest('.field-row').classList.toggle('changed', changed);
  const anyChanged = [...document.querySelectorAll('.field-val')]
    .some(i => i.value !== i.dataset.original);
  setDirty(anyChanged);
}

function setDirty(dirty) {
  document.getElementById('unsaved-indicator').classList.toggle('show', dirty);
  document.getElementById('save-btn').disabled = !dirty;
  document.getElementById('reset-btn').disabled = !dirty;
}

// ── reset ──────────────────────────────────────────────────────────────────
function resetFields() {
  rebuildFields(originalParsed);
  setDirty(false);
}

// ── save ───────────────────────────────────────────────────────────────────
async function saveEntry() {
  if (!currentParsed) return;

  const updated = { entry_id: currentParsed.entry_id };
  document.querySelectorAll('.field-val').forEach(inp => {
    updated[inp.dataset.key] = coerce(inp.value, inp.dataset.otype);
  });

  const saveBtn  = document.getElementById('save-btn');
  const resetBtn = document.getElementById('reset-btn');
  saveBtn.disabled = resetBtn.disabled = true;

  try {
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated),
    });
    if (!res.ok) throw new Error(res.statusText);

    // Patch local state
    const idx = DATA.parsed.findIndex(p => p.entry_id === currentParsed.entry_id);
    if (idx !== -1) DATA.parsed[idx] = updated;
    currentParsed  = JSON.parse(JSON.stringify(updated));
    originalParsed = JSON.parse(JSON.stringify(updated));

    // Mark pristine
    document.querySelectorAll('.field-val').forEach(inp => {
      inp.dataset.original = inp.value;
      inp.classList.remove('modified');
      inp.closest('.field-row').classList.remove('changed');
    });
    setDirty(false);

    // Track dirty entries in sidebar
    dirtyIds.add(updated.entry_id);
    renderList(document.getElementById('search-input').value);
    // Re-select the current item
    document.querySelectorAll('.entry-item').forEach(el => {
      if (Number(el.dataset.i) === DATA.parsed.findIndex(p => p.entry_id === updated.entry_id)) {
        el.classList.add('selected');
      }
    });

    showStatus('Saved ✓', 'ok');
  } catch (e) {
    saveBtn.disabled = false;
    resetBtn.disabled = false;
    setDirty(true);
    showStatus('Save failed!', 'err');
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('topbar-status');
  el.textContent = msg;
  el.className = `show ${type}`;
  setTimeout(() => { el.className = ''; }, 2500);
}

function coerce(raw, otype) {
  if (otype === 'null')    return raw === '' ? null : raw;
  if (otype === 'boolean') return raw.toLowerCase() === 'true' || raw === '1';
  if (otype === 'number')  { const n = Number(raw); return isNaN(n) ? raw : n; }
  return raw;
}

boot();
</script>
</body>
</html>
"""


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    entries:     dict = {}
    parsed:      list = []
    parsed_path: str  = ""

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, "text/html; charset=utf-8", HTML.encode())
        elif path == "/api/data":
            body = json.dumps({
                "entries": {str(k): v for k, v in Handler.entries.items()},
                "parsed":  Handler.parsed,
            }, ensure_ascii=False).encode()
            self._send(200, "application/json", body)
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/save":
            length  = int(self.headers.get("Content-Length", 0))
            updated = json.loads(self.rfile.read(length))
            eid = updated.get("entry_id")
            for i, rec in enumerate(Handler.parsed):
                if rec.get("entry_id") == eid:
                    Handler.parsed[i] = updated
                    break
            save_jsonl(Handler.parsed_path, Handler.parsed)
            self._send(200, "application/json", b'{"ok":true}')
        else:
            self.send_error(404)

    def _send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


# ── entry point ───────────────────────────────────────────────────────────────

def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    ENTRIES_PATH = "data/parsed_dict/male_parsed.jsonl"
    PARSED_PATH  = "data/parsed_entries/male_entries_parsed_V2.jsonl"

    for label, path in [("entries file", ENTRIES_PATH),
                        ("parsed file",  PARSED_PATH)]:
        if not os.path.exists(path):
            die(f"Could not find the {label}: {os.path.abspath(path)}")

    try:
        Handler.entries = {int(r["id"]): r["entry"]
                           for r in load_jsonl(ENTRIES_PATH)}
    except Exception as e:
        die(f"Error loading entries: {e}")

    try:
        Handler.parsed = load_jsonl(PARSED_PATH)
    except Exception as e:
        die(f"Error loading parsed: {e}")

    Handler.parsed_path = PARSED_PATH

    PORT   = 8080
    server = HTTPServer(("", PORT), Handler)
    print(f"  Serving → http://localhost:{PORT}")
    print(f"  Codespaces: open the PORTS tab and forward port {PORT}")
    print(f"  Ctrl+C to stop\n")

    threading.Thread(
        target=lambda: (__import__("time").sleep(0.5),
                        webbrowser.open(f"http://localhost:{PORT}")),
        daemon=True,
    ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")