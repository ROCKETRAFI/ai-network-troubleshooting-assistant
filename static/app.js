/* ═════════════════════════════════════════════════════════════════════
   NETWORK ASSISTANCE — FRONTEND APPLICATION LOGIC
═════════════════════════════════════════════════════════════════════ */

const state = {
  history: [],
  configs: {},
  topology: null,
  topologyFile: null,
  outputs: {
    intent: "{}",
    validation: "—",
    config: "—",
    diff: "—",
    rollback: "—",
    risk: "—",
    playbook: "—",
  },
};

const $ = (id) => document.getElementById(id);

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderMarkdown(text) {
  const escaped = escapeHtml(text);
  const withCode = escaped.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre>${code.trim()}</pre>`;
  });
  return withCode
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function addBubble(role, text, extraClass = "") {
  const article = document.createElement("article");
  article.className = `chat-bubble ${role} ${extraClass}`.trim();
  const isUser = role === "user";
  const authorName = isUser ? "You" : "Network Assistance";
  const avatar = isUser ? "" : `<span class="assistant-avatar">NA</span>`;
  const timeLabel = isUser ? "Network Engineer" : "AI Copilot";

  article.innerHTML = `
    <div class="bubble-header">
      ${avatar}
      <span class="bubble-author">${authorName}</span>
      <span class="bubble-time">${timeLabel}</span>
    </div>
    <div class="bubble-content">${
      isUser ? escapeHtml(text) : renderMarkdown(text)
    }</div>
  `;

  const thread = $("thread");
  thread.appendChild(article);
  thread.scrollTop = thread.scrollHeight;
  return article;
}

function setClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  $("clock").textContent = timeStr;
}

function switchView(name) {
  document.querySelectorAll(".nav-link").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.view === name);
  });
  $("view-chat").classList.toggle("is-active", name === "chat");
  $("view-atelier").classList.toggle("is-active", name === "atelier");
  $("view-topology").classList.toggle("is-active", name === "topology");

  const titles = {
    chat:     ["Network Assistance", "Chat"],
    atelier:  ["Network Assistance", "Change Studio"],
    topology: ["Network Assistance", "Topology"],
  };

  $("view-kicker").textContent = titles[name][0];
  $("view-title").textContent  = titles[name][1];
}

function switchPane(name) {
  document.querySelectorAll(".folio-tab").forEach((tab) => {
    const isTarget = tab.dataset.pane === name;
    tab.classList.toggle("is-active", isTarget);
    tab.setAttribute("aria-selected", isTarget ? "true" : "false");
  });
  document.querySelectorAll(".folio-pane").forEach((pane) => {
    pane.classList.toggle("is-active", pane.id === `pane-${name}`);
  });
}

function bannerClass(status) {
  if (status.startsWith("Approved")) return "approved";
  if (status.startsWith("Rejected") || status === "Not approved") return "rejected";
  if (status.startsWith("Pending")) return "pending";
  return "idle";
}

async function loadMeta() {
  try {
    const response = await fetch("/api/meta");
    const data = await response.json();
    state.configs = data.configs || {};

    $("chat-config").value = data.default_config || "";
    $("change-config").value = data.default_config || "";

    // Populate Example selector
    const exampleSelect = $("example-select");
    exampleSelect.innerHTML = `<option value="">Choose an example template…</option>`;
    (data.examples || []).forEach((item) => {
      const option = document.createElement("option");
      option.value = item;
      option.textContent = item;
      exampleSelect.appendChild(option);
    });

    // Populate Device Config inventory selector
    const configSelect = $("config-select");
    configSelect.innerHTML = "";
    Object.keys(state.configs).forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      configSelect.appendChild(option);
    });
    configSelect.value = "Minimal R1";

    // Populate Topology sample cards
    const sampleBox = $("topology-samples");
    sampleBox.innerHTML = "";
    (data.topology_samples || []).forEach((sample) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sample-card";
      button.innerHTML = `<img src="${sample.url}" alt="${sample.label}" /><span>${sample.label}</span>`;
      button.addEventListener("click", () => useTopologySample(sample, button));
      sampleBox.appendChild(button);
    });

    // Populate Quick Prompts
    const suggestions = $("chat-suggestions");
    suggestions.innerHTML = "";
    const promptList = [
      "What can you do?",
      data.examples?.[0] || "Connect R1 and R2 with OSPF on 10.1.1.0/30 area 0",
      data.examples?.[1] || "Add BGP neighbor 10.1.2.2 on R1 with local ASN 65001",
    ];

    promptList.filter(Boolean).forEach((text) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = text;
      button.addEventListener("click", () => {
        const input = $("chat-input");
        input.value = text;
        input.focus();
      });
      suggestions.appendChild(button);
    });
  } catch (err) {
    console.error("Failed to load metadata:", err);
  }
}

function studioPayload() {
  const out = state.outputs || {};
  const intent = out.intent || "{}";
  const validation = out.validation || "—";
  const config = out.config || "—";
  if (intent === "{}" && validation === "—" && config === "—") {
    return null;
  }
  return {
    intent,
    validation,
    config,
    diff: out.diff || "—",
    rollback: out.rollback || "—",
    risk: out.risk || "—",
    playbook: out.playbook || "—",
    approval_status: out.approval_status || "",
  };
}

function topologyPayload() {
  if (!state.topology || !state.topology.ok) return null;
  return state.topology;
}

function updateWorkspaceChip() {
  const chip = $("workspace-chip");
  const label = $("workspace-chip-text");
  if (!chip || !label) return;
  const parts = [];
  if (topologyPayload()) parts.push("Topology diagram");
  if (studioPayload()) parts.push("Change Studio pack");
  if (!parts.length) {
    chip.hidden = true;
    return;
  }
  chip.hidden = false;
  label.textContent = "Chat can use: " + parts.join(" + ");
}

function compactStudio(data) {
  return {
    intent: data.intent || "{}",
    validation: data.validation || "—",
    config: data.config || "—",
    diff: data.diff || "—",
    rollback: data.rollback || "—",
    risk: data.risk || "—",
    playbook: data.playbook || "—",
    approval_status: data.approval_status || "",
  };
}

async function sendChat(event) {
  if (event) event.preventDefault();
  const message = $("chat-input").value.trim();
  if (!message) return;

  addBubble("user", message);
  $("chat-input").value = "";
  const pending = addBubble("assistant", "", "typing");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: state.history,
        existing_config: $("chat-config").value,
        approval: $("chat-approval").checked,
        topology: topologyPayload(),
        studio: studioPayload(),
      }),
    });
    const data = await response.json();
    pending.remove();
    const replyText = data.reply || "No reply received from server.";
    addBubble("assistant", replyText);
    state.history.push({ role: "user", content: message });
    state.history.push({ role: "assistant", content: replyText });
  } catch (error) {
    pending.remove();
    addBubble("assistant", "Unable to connect to the backend server. Please verify the Python application is running.");
  }
}

async function generateChange() {
  const requestText = $("change-request").value.trim();
  const button = $("generate-btn");
  button.disabled = true;

  const banner = $("status-banner");
  banner.className = "status-banner pending";
  banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Composing validation folio &amp; Cisco IOS delta…</span>`;

  try {
    const response = await fetch("/api/change", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_text: requestText,
        existing_config: $("change-config").value,
        approval: $("change-approval").checked,
      }),
    });
    const data = await response.json();
    state.outputs = compactStudio(data);

    $("out-intent").textContent = data.intent || "{}";
    $("out-validation").textContent = data.validation || "—";
    $("out-config").textContent = data.config || "—";
    $("out-diff").textContent = data.diff || "—";
    $("out-rollback").textContent = data.rollback || "—";
    $("out-risk").textContent = data.risk || "—";
    $("out-playbook").textContent = data.playbook || "—";

    $("out-status").innerHTML = `<span class="status-pill-small">Status</span><span>Approval: <strong>${escapeHtml(data.approval_status)}</strong></span>`;

    const bClass = bannerClass(data.approval_status);
    banner.className = `status-banner ${bClass}`;
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">${escapeHtml(data.approval_status)}</span>`;
    updateWorkspaceChip();
  } catch (error) {
    banner.className = "status-banner rejected";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Failed to execute change request.</span>`;
  } finally {
    button.disabled = false;
  }
}

async function useTopologySample(sample, button) {
  document.querySelectorAll(".sample-card").forEach((card) => card.classList.remove("is-active"));
  button.classList.add("is-active");

  try {
    const response = await fetch(sample.url);
    const blob = await response.blob();
    const name = sample.id;
    state.topologyFile = new File([blob], name, { type: blob.type || "image/png" });

    const preview = $("topology-preview");
    preview.src = sample.url;
    preview.hidden = false;

    const banner = $("topology-banner");
    banner.className = "status-banner idle";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Loaded sample: ${escapeHtml(sample.label)}. Click Analyze Diagram.</span>`;
  } catch (err) {
    console.error("Error loading sample:", err);
  }
}

async function readTopology() {
  const file = state.topologyFile || $("topology-file").files[0];
  const banner = $("topology-banner");

  if (!file) {
    banner.className = "status-banner rejected";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Select a sample or upload a diagram file first.</span>`;
    return;
  }

  const body = new FormData();
  body.append("file", file);

  const btn = $("topology-btn");
  btn.disabled = true;
  banner.className = "status-banner pending";
  banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Analyzing topology diagram with Vision AI…</span>`;

  try {
    const response = await fetch("/api/topology", { method: "POST", body });
    const data = await response.json();
    state.topology = data;

    $("topology-out").textContent = JSON.stringify(data, null, 2);

    if (data.ok) {
      banner.className = "status-banner approved";
      banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">${escapeHtml(data.summary || "Diagram successfully analyzed.")}</span>`;
      updateWorkspaceChip();
    } else {
      banner.className = "status-banner rejected";
      banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">${escapeHtml(data.error || "Failed to analyze diagram.")}</span>`;
    }
  } catch (error) {
    banner.className = "status-banner rejected";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Network upload error. Is server online?</span>`;
  } finally {
    btn.disabled = false;
  }
}

async function copyOutput(key, btn) {
  const text = state.outputs[key] || "";
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const originalHTML = btn.innerHTML;
      btn.classList.add("copied");
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Copied!</span>`;
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = originalHTML;
      }, 1800);
    }
  } catch (err) {
    console.error("Clipboard copy error:", err);
  }
}

// Event Listeners
document.querySelectorAll(".nav-link").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

document.querySelectorAll(".folio-tab").forEach((tab) => {
  tab.addEventListener("click", () => switchPane(tab.dataset.pane));
});

document.querySelectorAll("[data-copy]").forEach((btn) => {
  btn.addEventListener("click", () => copyOutput(btn.dataset.copy, btn));
});

$("chat-form").addEventListener("submit", sendChat);
$("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat();
  }
});

$("generate-btn").addEventListener("click", generateChange);

$("example-select").addEventListener("change", (event) => {
  if (event.target.value) {
    $("change-request").value = event.target.value;
  }
});

$("config-select").addEventListener("change", (event) => {
  $("change-config").value = state.configs[event.target.value] || "";
});

$("topology-file").addEventListener("change", () => {
  const file = $("topology-file").files[0];
  const preview = $("topology-preview");
  state.topologyFile = file || null;
  document.querySelectorAll(".sample-card").forEach((card) => card.classList.remove("is-active"));

  if (!file) {
    preview.hidden = true;
    return;
  }
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
});

$("topology-btn").addEventListener("click", readTopology);

$("send-suggested").addEventListener("click", () => {
  const suggested = state.topology && state.topology.suggested_change;
  if (!suggested) {
    const banner = $("topology-banner");
    banner.className = "status-banner rejected";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">No suggested change extracted. Please analyze a diagram first.</span>`;
    return;
  }
  $("change-request").value = suggested;
  switchView("atelier");
});

$("discuss-chat").addEventListener("click", () => {
  if (!topologyPayload()) {
    const banner = $("topology-banner");
    banner.className = "status-banner rejected";
    banner.innerHTML = `<span class="banner-icon"></span><span class="banner-text">Analyze a diagram first, then discuss it in Chat.</span>`;
    return;
  }
  switchView("chat");
  updateWorkspaceChip();
  const devices = (state.topology.devices || []).join(", ") || "none";
  const summary = state.topology.summary || "Diagram analyzed.";
  addBubble(
    "assistant",
    `I loaded the last Topology analysis into Chat.\n\n${summary}\nDevices: ${devices}\n\nAsk about devices, links, NetBox matches, or say generate the suggested change from the diagram.`
  );
});

setClock();
setInterval(setClock, 10000);
loadMeta();
