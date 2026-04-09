// Shared helpers + per-page init functions.

async function api(method, url, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = `${res.status}`;
    try { const j = await res.json(); msg = j.error || msg; } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

// ---------- Dashboard ----------

function initDashboard() {
  const form = document.getElementById("start-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    data.connect_only = form.connect_only.checked;
    if (data.sequence_id === "") delete data.sequence_id;
    try {
      await api("POST", "/api/runs/start", data);
      pushLog("info", "Session start requested");
    } catch (err) {
      alert("Start failed: " + err.message);
    }
  });

  document.getElementById("stop-btn").addEventListener("click", async () => {
    try { await api("POST", "/api/runs/stop"); } catch (err) { alert(err.message); }
  });

  connectLogStream();
  refreshStats();
  setInterval(refreshStats, 4000);
}

function connectLogStream() {
  const feed = document.getElementById("log-feed");
  const dot = document.getElementById("sse-dot");
  const label = document.getElementById("sse-label");
  if (!feed) return;

  const es = new EventSource("/logs/stream");
  es.onopen = () => {
    dot.classList.remove("bg-slate-400", "bg-rose-500");
    dot.classList.add("bg-emerald-500");
    label.textContent = "live";
    feed.innerHTML = "";
  };
  es.onerror = () => {
    dot.classList.remove("bg-emerald-500");
    dot.classList.add("bg-rose-500");
    label.textContent = "reconnecting";
  };
  es.onmessage = (ev) => {
    if (!ev.data) return;
    try {
      const event = JSON.parse(ev.data);
      appendLog(event);
    } catch {}
  };
}

function appendLog(event) {
  const feed = document.getElementById("log-feed");
  if (!feed) return;
  const color = {
    info: "text-slate-200",
    warn: "text-amber-300",
    error: "text-rose-400",
    success: "text-emerald-300",
  }[event.level] || "text-slate-200";
  const line = document.createElement("div");
  line.className = color;
  const ts = event.ts ? event.ts.slice(11, 19) : "";
  line.textContent = `[${ts}] ${event.message}`;
  feed.appendChild(line);
  // Keep only the last 300 lines
  while (feed.children.length > 300) feed.removeChild(feed.firstChild);
  feed.scrollTop = feed.scrollHeight;
}

function pushLog(level, message) {
  appendLog({ level, message, ts: new Date().toISOString() });
}

async function refreshStats() {
  try {
    const data = await api("GET", "/api/stats");
    for (const key of ["sent", "skipped", "failed", "total"]) {
      const el = document.querySelector(`[data-stat="${key}"]`);
      if (el) el.textContent = data.today[key] ?? 0;
    }
    const credits = document.getElementById("inmail-credits");
    if (credits) credits.textContent = data.inmail_credits;
    const status = document.getElementById("session-status");
    if (status) {
      status.textContent = data.session_running ? "RUNNING" : "idle";
      status.className = data.session_running ? "text-emerald-600" : "text-slate-600";
    }
  } catch (err) {
    // Swallow; UI just won't update this tick
  }
}

// ---------- Templates ----------

function initTemplatesPage() {
  const form = document.getElementById("template-form");
  const angleWrap = document.getElementById("angle-wrapper");
  const deliverySelect = document.getElementById("delivery-method-select");

  function toggleAngle() {
    angleWrap.style.display = deliverySelect.value === "connect_no_note" ? "none" : "";
  }
  deliverySelect.addEventListener("change", toggleAngle);
  toggleAngle();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    if (data.sequence_id === "") delete data.sequence_id;
    const id = data.id;
    delete data.id;
    try {
      if (id) {
        await api("PUT", `/api/templates/${id}`, data);
      } else {
        await api("POST", "/api/templates", data);
      }
      location.reload();
    } catch (err) {
      alert("Save failed: " + err.message);
    }
  });

  document.getElementById("template-reset").addEventListener("click", () => {
    form.reset();
    form.id.value = "";
    toggleAngle();
  });

  document.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      const tpl = JSON.parse(li.dataset.template);
      for (const [key, val] of Object.entries(tpl)) {
        if (form.elements[key]) form.elements[key].value = val ?? "";
      }
      toggleAngle();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const li = e.target.closest("li");
      const tpl = JSON.parse(li.dataset.template);
      if (!confirm(`Delete template "${tpl.name}"?`)) return;
      try {
        await api("DELETE", `/api/templates/${tpl.id}`);
        li.remove();
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

// ---------- Sequences ----------

function initSequencesPage() {
  const form = document.getElementById("sequence-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      await api("POST", "/api/sequences", data);
      location.reload();
    } catch (err) {
      alert(err.message);
    }
  });

  document.querySelectorAll(".delete-sequence").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const block = e.target.closest("[data-sequence-id]");
      const id = block.dataset.sequenceId;
      if (!confirm("Delete this sequence and all its steps?")) return;
      try {
        await api("DELETE", `/api/sequences/${id}`);
        block.remove();
      } catch (err) { alert(err.message); }
    });
  });

  document.querySelectorAll(".add-step-form").forEach((f) => {
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const block = f.closest("[data-sequence-id]");
      const id = block.dataset.sequenceId;
      const data = Object.fromEntries(new FormData(f).entries());
      if (data.template_id === "") delete data.template_id;
      try {
        await api("POST", `/api/sequences/${id}/steps`, data);
        location.reload();
      } catch (err) { alert(err.message); }
    });
  });

  document.querySelectorAll(".delete-step").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const block = e.target.closest("[data-sequence-id]");
      const seqId = block.dataset.sequenceId;
      const stepId = e.target.dataset.stepId;
      try {
        await api("DELETE", `/api/sequences/${seqId}/steps/${stepId}`);
        e.target.closest("tr").remove();
      } catch (err) { alert(err.message); }
    });
  });
}
