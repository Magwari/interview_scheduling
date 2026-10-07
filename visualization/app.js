/* ============================================================
 * Interview Schedule Visualizer – app.js
 * ============================================================ */

// ---------- DOM refs ----------
const uploadArea   = document.getElementById("upload-area");
const fileInput    = document.getElementById("file-input");
const fileInfo     = document.getElementById("file-info");
const fileName     = document.getElementById("file-name");
const reUploadBtn  = document.getElementById("re-upload");

const statsSection  = document.getElementById("stats");
const personSection = document.getElementById("person-section");
const roomSection   = document.getElementById("room-section");
const personGantt   = document.getElementById("person-gantt");
const roomGantt     = document.getElementById("room-gantt");

// ---------- State ----------
let scheduleData = null;

// ============================================================
// 1. FILE UPLOAD
// ============================================================

uploadArea.addEventListener("click", () => fileInput.click());
reUploadBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) handleFile(e.target.files[0]);
});

// Drag & Drop
["dragenter", "dragover"].forEach((evt) =>
  uploadArea.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  uploadArea.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
  })
);
uploadArea.addEventListener("drop", (e) => {
  const files = e.dataTransfer.files;
  if (files.length) handleFile(files[0]);
});

function handleFile(file) {
  if (!file.name.endsWith(".json")) {
    showError("JSON 파일만 업로드할 수 있습니다.");
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      scheduleData = JSON.parse(e.target.result);
      if (!scheduleData.meta || !scheduleData.persons || !scheduleData.rooms) {
        throw new Error("JSON 구조가 올바르지 않습니다. (meta, persons, rooms 필수)");
      }
      renderAll();
    } catch (err) {
      showError(err.message);
    }
  };
  reader.onerror = () => showError("파일을 읽지 못했습니다.");
  reader.readAsText(file, "utf-8");
}

// ============================================================
// 2. HELPERS
// ============================================================

/** Compute horizon in minutes from meta */
function getHorizon(data) {
  const start = new Date(data.meta.start_time);
  const end   = new Date(data.meta.end_time);
  return Math.round((end - start) / 60000);
}

/** Convert minute offset → "HH:MM" label based on meta.start_time */
function toLabel(minuteOffset, baseDate) {
  const d = new Date(baseDate.getTime() + minuteOffset * 60000);
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

/**
 * Compute a nice time-tick list (in minute offsets) from 0..horizon.
 * Step chosen so we get roughly 8-20 ticks.
 */
function makeTicks(horizon) {
  const steps = [5, 10, 15, 20, 30, 60, 120];
  let step = steps.find((s) => horizon / s <= 24) || 60;
  const ticks = [];
  for (let t = 0; t <= horizon; t += step) ticks.push(t);
  return { ticks, step };
}

/**
 * Compute the total pixel width for the timeline area.
 * We use a fixed width-per-minute so bars are readable.
 */
function timelineWidth(horizon) {
  // aim for ~1000px for 240min, minimum 800px
  const pxPerMin = Math.max(4, 1000 / horizon);
  return Math.round(horizon * pxPerMin);
}

/** Map a minute offset to a percentage (0-100) */
function pct(offset, horizon) {
  return (offset / horizon) * 100;
}

/** Map a duration to a percentage */
function pctDur(duration, horizon) {
  return (duration / horizon) * 100;
}

// ---------- Interview type theming ----------
// Interview type names are free-form (e.g. "면접 A"), so colors are
// assigned by declaration order in meta.interview_types instead of
// looking up hardcoded "A"/"B"/"C" keys.
const TYPE_PALETTE = [
  { solid: "#3b82f6", light: "#bfdbfe", text: "#ffffff" },
  { solid: "#10b981", light: "#d1fae5", text: "#ffffff" },
  { solid: "#f59e0b", light: "#fef3c7", text: "#78350f" },
  { solid: "#8b5cf6", light: "#ede9fe", text: "#ffffff" },
  { solid: "#ef4444", light: "#fee2e2", text: "#ffffff" },
  { solid: "#0ea5e9", light: "#e0f2fe", text: "#ffffff" },
  { solid: "#64748b", light: "#e2e8f0", text: "#ffffff" },
];
const FALLBACK_THEME = TYPE_PALETTE[TYPE_PALETTE.length - 1];

/** Interview type name → { solid, light, text } */
let typeTheme = new Map();

function buildTypeTheme(meta) {
  const theme = new Map();
  Object.keys(meta.interview_types || {}).forEach((name, index) => {
    theme.set(name, TYPE_PALETTE[index % TYPE_PALETTE.length]);
  });
  return theme;
}

function themeFor(type) {
  return typeTheme.get(type) || FALLBACK_THEME;
}

/** Escape a value before inserting it into innerHTML. */
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * Compare room names for stable ordering.
 * "면접 A-1" → base "면접 A", number 1.
 * Names without a trailing number use plain Korean locale order.
 */
function compareRoomNames(a, b) {
  const matchA = a.match(/^(.*?)-?(\d+)$/);
  const matchB = b.match(/^(.*?)-?(\d+)$/);
  const nameA = matchA ? matchA[1] : a;
  const nameB = matchB ? matchB[1] : b;
  const numA = matchA ? parseInt(matchA[2], 10) : 0;
  const numB = matchB ? parseInt(matchB[2], 10) : 0;
  const nameCmp = nameA.localeCompare(nameB, "ko");
  return nameCmp !== 0 ? nameCmp : numA - numB;
}

/** Show error banner */
function showError(msg) {
  let el = document.getElementById("error-msg");
  if (!el) {
    el = document.createElement("div");
    el.id = "error-msg";
    el.className = "error-msg";
    document.querySelector(".header").appendChild(el);
  }
  el.textContent = "⚠️ " + msg;
  el.classList.remove("hidden");
}

/** Hide error banner */
function hideError() {
  const el = document.getElementById("error-msg");
  if (el) el.classList.add("hidden");
}

// ============================================================
// 3. RENDER STATS
// ============================================================

function renderStats(data) {
  const { meta, status, objective, persons, rooms } = data;

  // Status
  const statusEl = document.getElementById("stat-status");
  statusEl.textContent = status;
  statusEl.className = `stat-value status-badge ${status}`;

  // Persons
  document.getElementById("stat-persons").textContent = persons.length;

  // Rooms (unique room names)
  const roomNames = new Set(rooms.map((r) => r.room));
  document.getElementById("stat-rooms").textContent = roomNames.size;

  // Total interviews
  const totalInterviews = persons.reduce((sum, p) => sum + p.interviews.length, 0);
  document.getElementById("stat-interviews").textContent = totalInterviews;

  // Avg stay
  const avgStay = persons.reduce((sum, p) => sum + p.stay, 0) / persons.length;
  document.getElementById("stat-avg-stay").textContent = avgStay.toFixed(1);

  // Objective
  document.getElementById("stat-objective").textContent =
    objective != null ? objective : "N/A";

  // Per-type stats
  const typeContainer = document.getElementById("type-stats");
  typeContainer.innerHTML = "";

  for (const [typeKey, typeInfo] of Object.entries(meta.interview_types)) {
    const typeCount = persons.reduce(
      (sum, p) => sum + p.interviews.filter((iv) => iv.type === typeKey).length,
      0
    );
    const totalMinutes = persons.reduce(
      (sum, p) =>
        sum +
        p.interviews
          .filter((iv) => iv.type === typeKey)
          .reduce((s, iv) => s + (iv.end - iv.start), 0),
      0
    );
    const roomCount = typeInfo.room_count;
    const theme = themeFor(typeKey);

    const div = document.createElement("div");
    div.className = "type-stat";
    div.innerHTML = `
      <span class="type-badge" style="background:${theme.solid};color:${theme.text}">${escapeHtml(typeKey)}</span>
      <span class="type-count">${typeCount}명</span>
      <span class="type-info">실 ${roomCount}개 · ${typeInfo.duration}분/회</span>
      <span class="type-total">총 ${totalMinutes}분 사용</span>
    `;
    typeContainer.appendChild(div);
  }

  statsSection.classList.remove("hidden");
}

// ============================================================
// 4. RENDER PERSON GANTT
// ============================================================

function renderPersonGantt(data) {
  const { meta, persons } = data;
  const horizon = getHorizon(data);
  const baseDate = new Date(meta.start_time);
  const tlWidth = timelineWidth(horizon);
  const { ticks, step } = makeTicks(horizon);

  // Sort persons by first_start, then interviewee
  const sorted = [...persons].sort(
    (a, b) => a.first_start - b.first_start || a.interviewee - b.interviewee
  );

  // --- Build HTML ---
  const frag = document.createDocumentFragment();

  // Time axis row
  const axisRow = document.createElement("div");
  axisRow.className = "gantt-timeaxis";

  const spacer = document.createElement("div");
  spacer.className = "row-label-spacer";

  const timeLabels = document.createElement("div");
  timeLabels.className = "time-labels";
  timeLabels.style.width = tlWidth + "px";

  ticks.forEach((t) => {
    const tick = document.createElement("span");
    tick.className = "time-tick";
    tick.style.left = pct(t, horizon) + "%";
    tick.textContent = toLabel(t, baseDate);
    timeLabels.appendChild(tick);
  });

  axisRow.appendChild(spacer);
  axisRow.appendChild(timeLabels);
  frag.appendChild(axisRow);

  // Rows
  const rowsDiv = document.createElement("div");
  rowsDiv.className = "gantt-rows";

  sorted.forEach((person) => {
    const row = document.createElement("div");
    row.className = "gantt-row";

    const label = document.createElement("div");
    label.className = "row-label";
    label.textContent = `P${person.interviewee}`;
    label.title = `지원자 ${person.interviewee} · 체류 ${person.stay}분`;

    const timeline = document.createElement("div");
    timeline.className = "timeline";
    timeline.style.width = tlWidth + "px";

    // Add bars for each interview
    person.interviews.forEach((iv) => {
      const theme = themeFor(iv.type);

      // Ready bar (if ready_start < start)
      if (iv.ready_start < iv.start) {
        const readyBar = document.createElement("div");
        readyBar.className = "bar";
        readyBar.style.background = theme.light;
        readyBar.style.color = "var(--text-muted)";
        readyBar.style.left = pct(iv.ready_start, horizon) + "%";
        readyBar.style.width = pctDur(iv.start - iv.ready_start, horizon) + "%";
        readyBar.title = `${iv.type} Ready (${toLabel(iv.ready_start, baseDate)}~${toLabel(iv.start, baseDate)})`;
        timeline.appendChild(readyBar);
      }

      // Interview bar
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.background = theme.solid;
      bar.style.color = theme.text;
      bar.style.left = pct(iv.start, horizon) + "%";
      bar.style.width = pctDur(iv.end - iv.start, horizon) + "%";
      bar.textContent = iv.type;
      bar.title = `${iv.type} · ${toLabel(iv.start, baseDate)}~${toLabel(iv.end, baseDate)} · ${iv.room}`;
      timeline.appendChild(bar);
    });

    row.appendChild(label);
    row.appendChild(timeline);
    rowsDiv.appendChild(row);
  });

  frag.appendChild(rowsDiv);

  // Clear & append
  personGantt.innerHTML = "";
  personGantt.appendChild(frag);

  personSection.classList.remove("hidden");
}

// ============================================================
// 5. RENDER ROOM GANTT
// ============================================================

function renderRoomGantt(data) {
  const { meta, rooms } = data;
  const horizon = getHorizon(data);
  const baseDate = new Date(meta.start_time);
  const tlWidth = timelineWidth(horizon);
  const { ticks } = makeTicks(horizon);

  // Group rooms by room name, keep order
  const roomMap = new Map();
  rooms.forEach((r) => {
    if (!roomMap.has(r.room)) roomMap.set(r.room, []);
    roomMap.get(r.room).push(r);
  });

  // Sort room names ("면접 A-1", "면접 A-10", "면접 B-1", ...)
  const sortedRoomNames = [...roomMap.keys()].sort(compareRoomNames);

  const frag = document.createDocumentFragment();

  // Time axis
  const axisRow = document.createElement("div");
  axisRow.className = "gantt-timeaxis";

  const spacer = document.createElement("div");
  spacer.className = "row-label-spacer";

  const timeLabels = document.createElement("div");
  timeLabels.className = "time-labels";
  timeLabels.style.width = tlWidth + "px";

  ticks.forEach((t) => {
    const tick = document.createElement("span");
    tick.className = "time-tick";
    tick.style.left = pct(t, horizon) + "%";
    tick.textContent = toLabel(t, baseDate);
    timeLabels.appendChild(tick);
  });

  axisRow.appendChild(spacer);
  axisRow.appendChild(timeLabels);
  frag.appendChild(axisRow);

  // Rows
  const rowsDiv = document.createElement("div");
  rowsDiv.className = "gantt-rows";

  sortedRoomNames.forEach((roomName) => {
    const roomEntries = roomMap.get(roomName);
    const row = document.createElement("div");
    row.className = "gantt-row";

    const label = document.createElement("div");
    label.className = "row-label";
    label.textContent = roomName;
    label.title = roomName;
    label.style.borderLeft = `4px solid ${themeFor(roomEntries[0].type).solid}`;

    const timeline = document.createElement("div");
    timeline.className = "timeline";
    timeline.style.width = tlWidth + "px";

    // Sort by room_start
    roomEntries.sort((a, b) => a.room_start - b.room_start);

    roomEntries.forEach((entry) => {
      const theme = themeFor(entry.type);

      // Ready / Prep bar (room_start → interview_start)
      if (entry.room_start < entry.interview_start) {
        const readyBar = document.createElement("div");
        readyBar.className = "bar";
        readyBar.style.background = theme.light;
        readyBar.style.color = "var(--text-muted)";
        readyBar.style.left = pct(entry.room_start, horizon) + "%";
        readyBar.style.width =
          pctDur(entry.interview_start - entry.room_start, horizon) + "%";
        readyBar.title = `Prep (${toLabel(entry.room_start, baseDate)}~${toLabel(entry.interview_start, baseDate)})`;
        timeline.appendChild(readyBar);
      }

      // Interview bar
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.background = theme.solid;
      bar.style.color = theme.text;
      bar.style.left = pct(entry.interview_start, horizon) + "%";
      bar.style.width =
        pctDur(entry.interview_end - entry.interview_start, horizon) + "%";
      bar.textContent = `P${entry.interviewee}`;
      bar.title = `${entry.room} · P${entry.interviewee} · ${toLabel(entry.interview_start, baseDate)}~${toLabel(entry.interview_end, baseDate)}`;
      timeline.appendChild(bar);

      // Break / Cooldown bar (interview_end → room_end)
      if (entry.interview_end < entry.room_end) {
        const breakBar = document.createElement("div");
        breakBar.className = "bar break";
        breakBar.style.left = pct(entry.interview_end, horizon) + "%";
        breakBar.style.width =
          pctDur(entry.room_end - entry.interview_end, horizon) + "%";
        breakBar.title = `Break (${toLabel(entry.interview_end, baseDate)}~${toLabel(entry.room_end, baseDate)})`;
        breakBar.textContent = "";
        timeline.appendChild(breakBar);
      }
    });

    row.appendChild(label);
    row.appendChild(timeline);
    rowsDiv.appendChild(row);
  });

  frag.appendChild(rowsDiv);

  // Clear & append
  roomGantt.innerHTML = "";
  roomGantt.appendChild(frag);

  roomSection.classList.remove("hidden");
}

// ============================================================
// 6. RENDER ALL
// ============================================================

function renderAll() {
  hideError();
  uploadArea.style.display = "none";
  fileInfo.classList.remove("hidden");
  fileName.textContent = "✅ " + (fileInput.files[0] ? fileInput.files[0].name : "");

  typeTheme = buildTypeTheme(scheduleData.meta);

  renderStats(scheduleData);
  renderPersonGantt(scheduleData);
  renderRoomGantt(scheduleData);

  // Scroll to stats
  statsSection.scrollIntoView({ behavior: "smooth" });
}