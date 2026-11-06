"use strict";

const tg = window.Telegram && window.Telegram.WebApp;
// ?dev=<telegram id> works only when the server runs with DEV_MODE=1
const devId = new URLSearchParams(location.search).get("dev");
const $view = document.getElementById("view");
const $back = document.getElementById("back");
let me = null;

if (tg) { tg.ready(); tg.expand(); }
$back.onclick = () => history.back();

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (iso) => { const [d, t] = iso.split("T"); return `${d.split("-").reverse().join(".")} ${t || ""}`; };

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => (el.hidden = true), 2600);
}

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (tg && tg.initData) headers["X-Init-Data"] = tg.initData;
  else if (devId) headers["X-Dev-Tg-Id"] = devId;
  const res = await fetch("/api" + path, { ...opts, headers });
  let data = null;
  try { data = await res.json(); } catch (_) { /* not JSON */ }
  if (!res.ok) {
    // FastAPI validation errors come as a list - never show raw JSON to the user
    const d = data && data.detail;
    throw new Error(typeof d === "string" ? d : `Request failed (${res.status})`);
  }
  return data;
}

// Shrinks a photo on the phone before upload: saves mobile data and server disk.
function compress(file, max = 1600) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      c.toBlob((b) => resolve(b || file), "image/jpeg", 0.85);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

// ---------- full-screen photo viewer ----------
// The viewer is pushed to history, otherwise the phone's "back" closes the
// whole screen underneath instead of just the photo.
let viewerOpen = false;
function showImage(url) {
  document.getElementById("viewer-img").src = url;
  document.getElementById("viewer").hidden = false;
  if (!viewerOpen) { viewerOpen = true; history.pushState({ viewer: true }, ""); }
}
function closeImage(fromHistory) {
  const v = document.getElementById("viewer");
  if (v.hidden) return;
  v.hidden = true;
  document.getElementById("viewer-img").removeAttribute("src");
  if (viewerOpen) { viewerOpen = false; if (!fromHistory) history.back(); }
}
document.getElementById("viewer").onclick = () => closeImage(false);
window.addEventListener("popstate", () => { if (viewerOpen) closeImage(true); });

// ---------- routing ----------
window.addEventListener("hashchange", route);

async function route() {
  const name = (location.hash || "#list").slice(1);
  const isRoot = name === "list";
  $back.hidden = isRoot;
  if (tg && tg.BackButton) {
    isRoot ? tg.BackButton.hide() : tg.BackButton.show();
  }
  $view.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    await (name === "new" ? viewNew : viewList)();
  } catch (e) {
    $view.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

async function viewList() {
  const { items } = await api("/reports");
  $view.innerHTML = `
    <button id="new" class="big">+ New report</button>
    ${me.is_admin ? `<div class="hint">Admin: send <b>/export</b> to the bot to get all reports as Excel.</div>` : ""}
    <div class="list">${items.length ? items.map((r) => `
      <div class="card">
        <div class="row"><b>${esc(r.title)}</b><span class="muted">${fmt(r.created_at)}</span></div>
        ${me.is_admin ? `<div class="muted">${esc(r.author)}</div>` : ""}
        ${r.note ? `<div>${esc(r.note)}</div>` : ""}
        <div class="thumbs">${r.photos.map((p) => `<img src="${p.thumb}" data-full="${p.url}" alt="">`).join("")}</div>
      </div>`).join("") : `<div class="empty">No reports yet</div>`}</div>`;
  document.getElementById("new").onclick = () => { location.hash = "#new"; };
  $view.querySelectorAll("img[data-full]").forEach((img) => (img.onclick = () => showImage(img.dataset.full)));
}

async function viewNew() {
  const files = [];
  $view.innerHTML = `
    <h2>New report</h2>
    <label>Title<input id="title" autocomplete="off"></label>
    <label>Note (optional)<textarea id="note" rows="3"></textarea></label>
    <div class="label">Photos · up to ${me.max_photos}</div>
    <div class="thumbs" id="pics"></div>
    <div id="msg"></div>
    <button id="send" class="big">Send</button>`;
  const pics = document.getElementById("pics");
  const urls = [];  // preview links; freed on every redraw so memory does not leak
  const render = () => {
    urls.splice(0).forEach(URL.revokeObjectURL);
    pics.innerHTML = files.map((f, i) => { const u = URL.createObjectURL(f); urls.push(u);
      return `<div class="pic"><img src="${u}" alt=""><span data-i="${i}">✕</span></div>`; }).join("")
      + (files.length < me.max_photos
        // capture="environment" opens the camera directly, so photos are taken on the spot
        ? `<label class="add">📷<input type="file" accept="image/*" capture="environment"></label>` : "");
    pics.querySelectorAll("[data-i]").forEach((x) => (x.onclick = () => { files.splice(+x.dataset.i, 1); render(); }));
    const input = pics.querySelector("input");
    if (input) input.onchange = async () => { for (const f of input.files) files.push(await compress(f)); render(); };
  };
  render();
  document.getElementById("send").onclick = async (e) => {
    const fd = new FormData();
    fd.append("title", document.getElementById("title").value);
    fd.append("note", document.getElementById("note").value);
    files.forEach((f) => fd.append("photos", f, "photo.jpg"));
    e.target.disabled = true;
    try {
      await api("/reports", { method: "POST", body: fd });
      toast("Sent ✓");
      history.back();
    } catch (err) {
      document.getElementById("msg").innerHTML = `<div class="err">${esc(err.message)}</div>`;
      e.target.disabled = false;
    }
  };
}

// ---------- start ----------
(async () => {
  if (tg && tg.BackButton) tg.BackButton.onClick(() => history.back());
  try {
    me = await api("/me");
    document.getElementById("who").textContent = me.full_name;
    route();
  } catch (e) {
    $view.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
})();
