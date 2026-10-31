/**
 * GhostShell: The Haunted AI Terminal
 * Frontend Controller & Interactive Engine
 */

function initGhostShell() {
  if (window.__GHOSTSHELL_READY__) return;
  window.__GHOSTSHELL_READY__ = true;

  // --- State ---
  const state = {
    activeMode: "terminal", // "terminal" | "guardian" | "archives"
    ollamaOnline: false,
    currentModel: "qwen2.5:3b",
    installedModels: [],
    isGenerating: false,
    conversationHistory: [],
    crtEnabled: true
  };

  // --- DOM Elements ---
  const dom = {
    // Overlays & CRT
    crtOverlay: document.getElementById("crtOverlay"),
    toggleCrtBtn: document.getElementById("toggleCrtBtn"),

    // Header & Status
    statusBadge: document.getElementById("statusBadge"),
    statusText: document.getElementById("statusText"),
    modelPill: document.getElementById("modelPill"),
    settingsBtn: document.getElementById("settingsBtn"),

    // Mode Buttons
    modeButtons: document.querySelectorAll(".mode-btn"),
    modePanels: document.querySelectorAll(".mode-panel"),

    // Companion Avatar & State
    ghostAvatar: document.getElementById("ghostAvatar"),
    ghostStatusDesc: document.getElementById("ghostStatusDesc"),

    // Terminal Ghost Mode Elements
    terminalStream: document.getElementById("terminalStream"),
    terminalInput: document.getElementById("terminalInput"),
    terminalSendBtn: document.getElementById("terminalSendBtn"),
    clearTerminalBtn: document.getElementById("clearTerminalBtn"),

    // Security Guardian Mode Elements
    guardianInput: document.getElementById("guardianInput"),
    guardianInspectBtn: document.getElementById("guardianInspectBtn"),
    guardianResults: document.getElementById("guardianResults"),
    guardianPlatformSelect: document.getElementById("guardianPlatformSelect"),

    // Haunted Archives Elements
    archiveStoryType: document.getElementById("archiveStoryType"),
    archiveSetting: document.getElementById("archiveSetting"),
    archiveIntensity: document.getElementById("archiveIntensity"),
    archiveLength: document.getElementById("archiveLength"),
    archivePromptInput: document.getElementById("archivePromptInput"),
    archiveSummonBtn: document.getElementById("archiveSummonBtn"),
    archiveOutput: document.getElementById("archiveOutput"),
    cyoaChoicesContainer: document.getElementById("cyoaChoicesContainer"),

    // Settings Modal
    settingsModal: document.getElementById("settingsModal"),
    closeSettingsBtn: document.getElementById("closeSettingsBtn"),
    modalModelSelect: document.getElementById("modalModelSelect"),
    modalCustomModelInput: document.getElementById("modalCustomModelInput"),
    modalSaveModelBtn: document.getElementById("modalSaveModelBtn"),
    modalOllamaStatusInfo: document.getElementById("modalOllamaStatusInfo")
  };

  // --- Helper: HTML Escaper ---
  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Helper: Format Markdown subset (code blocks, bold, inline code)
  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);

    // Code blocks ```code```
    formatted = formatted.replace(/```([a-zA-Z0-9_\-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="code-block"><div class="code-header"><span>${lang || 'terminal'}</span><button class="btn-copy" onclick="copyToClipboard(this)">Copy</button></div><code>${code.trim()}</code></pre>`;
    });

    // Inline `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Bold **text**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Bullet points
    formatted = formatted.replace(/^[\*\-]\s+(.*)$/gm, '• $1');

    return formatted;
  }

  // --- Global Clipboard Copy ---
  window.copyToClipboard = function(btn) {
    let textToCopy = "";
    const pre = btn.closest(".code-block");
    if (pre) {
      const code = pre.querySelector("code");
      textToCopy = code ? code.innerText : "";
    } else {
      const card = btn.closest(".analysis-card, .msg-content, .card-body");
      textToCopy = card ? card.innerText : "";
    }

    if (!textToCopy) return;

    navigator.clipboard.writeText(textToCopy).then(() => {
      const originalText = btn.innerText;
      btn.innerText = "Copied! 📋";
      setTimeout(() => {
        btn.innerText = originalText;
      }, 2000);
    }).catch(err => {
      console.error("Clipboard copy failed:", err);
    });
  };

  // --- Companion Avatar Mood Controller ---
  function setGhostMood(mood, customStatus) {
    if (!dom.ghostAvatar) return;
    const aura = dom.ghostAvatar.querySelector(".ghost-aura");
    const eyes = dom.ghostAvatar.querySelectorAll(".ghost-eye");

    if (mood === "warning" || mood === "critical") {
      dom.ghostStatusDesc.innerText = customStatus || "Spectral alarm triggered! Danger detected.";
      dom.ghostStatusDesc.style.color = "var(--risk-critical)";
      if (aura) aura.setAttribute("fill", "rgba(239, 68, 68, 0.4)");
    } else if (mood === "thinking") {
      dom.ghostStatusDesc.innerText = customStatus || "Divining the ethereal machine buffers...";
      dom.ghostStatusDesc.style.color = "var(--term-purple)";
      if (aura) aura.setAttribute("fill", "rgba(168, 85, 247, 0.4)");
    } else if (mood === "safe") {
      dom.ghostStatusDesc.innerText = customStatus || "The machine spirits are peaceful.";
      dom.ghostStatusDesc.style.color = "var(--term-green)";
      if (aura) aura.setAttribute("fill", "rgba(0, 255, 136, 0.3)");
    } else {
      dom.ghostStatusDesc.innerText = customStatus || "Haunting your terminal in local isolation.";
      dom.ghostStatusDesc.style.color = "var(--term-purple)";
      if (aura) aura.setAttribute("fill", "url(#ghostGlow)");
    }
  }

  // --- Mode Switching ---
  function switchMode(newMode) {
    state.activeMode = newMode;
    dom.modeButtons.forEach(btn => {
      btn.classList.toggle("active", btn.dataset.mode === newMode);
    });
    dom.modePanels.forEach(panel => {
      panel.classList.toggle("active", panel.id === `mode-${newMode}`);
    });

    if (newMode === "guardian") {
      setGhostMood("calm", "Security Guardian mode active. Ready to audit commands.");
      dom.guardianInput.focus();
    } else if (newMode === "archives") {
      setGhostMood("calm", "Haunted Archives mode open. Ready to summon fictional tech horror.");
    } else {
      setGhostMood("calm", "Terminal Ghost active. Ask questions or type commands.");
      dom.terminalInput.focus();
    }
  }

  dom.modeButtons.forEach(btn => {
    btn.addEventListener("click", () => switchMode(btn.dataset.mode));
  });

  // --- Check Local Ollama AI Status ---
  async function fetchStatus() {
    try {
      const resp = await fetch("/api/status");
      const data = await resp.json();
      state.ollamaOnline = data.ollama_available;
      state.currentModel = data.current_model || state.currentModel;
      state.installedModels = data.installed_models || [];

      // Update UI Status Badge
      if (state.ollamaOnline && data.model_available) {
        dom.statusBadge.className = "status-badge online";
        dom.statusText.innerText = "Ollama Online";
        dom.modelPill.innerText = `🤖 ${state.currentModel}`;
      } else if (state.ollamaOnline && !data.model_available) {
        dom.statusBadge.className = "status-badge offline";
        dom.statusText.innerText = "Model Missing";
        dom.modelPill.innerText = `⚠️ ${state.currentModel}`;
      } else {
        dom.statusBadge.className = "status-badge offline";
        dom.statusText.innerText = "Ollama Offline";
        dom.modelPill.innerText = "🔒 Non-AI Rules Only";
      }

      // Populate Settings Model Select
      if (dom.modalModelSelect) {
        dom.modalModelSelect.innerHTML = "";
        if (state.installedModels.length > 0) {
          state.installedModels.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.name;
            opt.innerText = `${m.name} (${Math.round(m.size / (1024 * 1024 * 1024) * 10) / 10} GB)`;
            if (m.name === state.currentModel) opt.selected = true;
            dom.modalModelSelect.appendChild(opt);
          });
        } else {
          const opt = document.createElement("option");
          opt.value = state.currentModel;
          opt.innerText = `${state.currentModel} (Not yet downloaded)`;
          dom.modalModelSelect.appendChild(opt);
        }
      }

      if (dom.modalOllamaStatusInfo) {
        if (state.ollamaOnline) {
          dom.modalOllamaStatusInfo.innerHTML = `<span style="color:var(--term-green);">● Ollama is connected at ${escapeHtml(data.base_url)}. ${state.installedModels.length} models detected.</span>`;
        } else {
          dom.modalOllamaStatusInfo.innerHTML = `<span style="color:var(--risk-critical);">● Ollama unreachable at ${escapeHtml(data.base_url)}. Rule-based command safety checks remain 100% operational offline.</span>`;
        }
      }
    } catch (err) {
      console.warn("Status check failed:", err);
      dom.statusBadge.className = "status-badge offline";
      dom.statusText.innerText = "Ollama Offline";
      dom.modelPill.innerText = "🔒 Non-AI Rules Only";
    }
  }

  // --- Terminal Stream Message Appender ---
  function appendTerminalMessage(role, content, extraHtml = "") {
    const msgDiv = document.createElement("div");
    msgDiv.className = `stream-msg msg-${role}`;

    let headerIcon = "👻 Ghost";
    if (role === "user") headerIcon = "❯ mortal@user";
    if (role === "system") headerIcon = "⚙️ System Notice";

    msgDiv.innerHTML = `
      <div class="msg-header">
        <span>${headerIcon}</span>
        <button class="btn-copy" onclick="copyToClipboard(this)">Copy</button>
      </div>
      <div class="msg-content">${formatMarkdown(content)}${extraHtml}</div>
    `;

    dom.terminalStream.appendChild(msgDiv);
    dom.terminalStream.scrollTop = dom.terminalStream.scrollHeight;
    return msgDiv;
  }

  // --- Show Typing Indicator ---
  function showTypingIndicator() {
    const indicatorDiv = document.createElement("div");
    indicatorDiv.id = "ghostTypingIndicator";
    indicatorDiv.className = "stream-msg msg-ghost";
    indicatorDiv.innerHTML = `
      <div class="msg-header"><span>👻 Ghost is communing...</span></div>
      <div class="msg-content">
        <div class="typing-indicator">
          <span>spectral thoughts forming</span>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    dom.terminalStream.appendChild(indicatorDiv);
    dom.terminalStream.scrollTop = dom.terminalStream.scrollHeight;
  }

  function removeTypingIndicator() {
    const el = document.getElementById("ghostTypingIndicator");
    if (el) el.remove();
  }

  // --- Render Risk Analysis Card ---
  function buildAnalysisCardHtml(analysis) {
    const risk = analysis.risk_level || "SAFE";
    let badgeClass = "badge-safe";
    let icon = "🛡️";

    if (risk === "CRITICAL") { badgeClass = "badge-critical"; icon = "🚨"; }
    else if (risk === "HIGH") { badgeClass = "badge-high"; icon = "⚠️"; }
    else if (risk === "MEDIUM") { badgeClass = "badge-medium"; icon = "⚡"; }
    else if (risk === "LOW") { badgeClass = "badge-low"; icon = "ℹ️"; }
    else if (risk === "REVIEW REQUIRED") { badgeClass = "badge-review"; icon = "❓"; }

    const findingsHtml = (analysis.findings || []).map(f => `<li>${escapeHtml(f)}</li>`).join("");

    let chainedHtml = "";
    if (analysis.chained_commands && analysis.chained_commands.length > 1) {
      chainedHtml = `
        <div>
          <div class="section-label">⛓️ Chained Operations Detected (${analysis.chained_commands.length})</div>
          <ul class="findings-list">
            ${analysis.chained_commands.map(c => `<li><code>${escapeHtml(c)}</code></li>`).join("")}
          </ul>
        </div>
      `;
    }

    let aiExplanationHtml = "";
    if (analysis.ai_explanation) {
      aiExplanationHtml = `
        <div>
          <div class="section-label">👻 Ghost's AI Analysis</div>
          <div class="ghost-explanation-box">${formatMarkdown(analysis.ai_explanation)}</div>
        </div>
      `;
    }

    return `
      <div class="analysis-card">
        <div class="card-header">
          <div class="card-command"><code>${escapeHtml(analysis.command)}</code></div>
          <div class="risk-badge ${badgeClass}">${icon} ${escapeHtml(risk)}</div>
        </div>
        <div class="card-body">
          <div style="font-size: 0.8rem; color: var(--term-gray);">
            <strong>Platform:</strong> ${escapeHtml(analysis.platform || 'generic')}
          </div>
          <div>
            <div class="section-label">🔍 Deterministic Security Findings</div>
            <ul class="findings-list">${findingsHtml}</ul>
          </div>
          <div>
            <div class="section-label">📖 Operational Explanation</div>
            <p>${escapeHtml(analysis.explanation)}</p>
          </div>
          <div>
            <div class="section-label">💡 Recommended Next Step</div>
            <div class="recommendation-box">${escapeHtml(analysis.recommendation)}</div>
          </div>
          ${chainedHtml}
          ${aiExplanationHtml}
        </div>
      </div>
    `;
  }

  // --- Terminal Chat Submission ---
  async function submitTerminalMessage() {
    const rawText = dom.terminalInput.value.trim();
    if (!rawText || state.isGenerating) return;

    dom.terminalInput.value = "";
    appendTerminalMessage("user", rawText);
    state.conversationHistory.push({ role: "user", content: rawText });

    state.isGenerating = true;
    dom.terminalSendBtn.disabled = true;
    showTypingIndicator();
    setGhostMood("thinking", "Spectral neural link active...");

    try {
      // Check if user is asking to analyze a command specifically
      const isLikelyCommand = /^(?:rm|sudo|chmod|chown|kill|curl|wget|del|rmdir|Get-|Set-|format|dd|cat|type)\b/i.test(rawText);

      if (isLikelyCommand) {
        // Run command analyzer directly
        const resp = await fetch("/api/analyze-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: rawText, with_ai: true })
        });
        const analysis = await resp.json();
        removeTypingIndicator();

        const cardHtml = buildAnalysisCardHtml(analysis);
        appendTerminalMessage("ghost", `I have audited your command without executing it, mortal:`, cardHtml);

        if (analysis.risk_level === "CRITICAL" || analysis.risk_level === "HIGH") {
          setGhostMood("critical", `Alert! Detected ${analysis.risk_level} risk!`);
        } else {
          setGhostMood("safe", "Audit complete.");
        }
      } else {
        // Conversational chat with Ghost
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: rawText,
            history: state.conversationHistory
          })
        });
        const data = await resp.json();
        removeTypingIndicator();

        const reply = data.content || "👻 *The machine spirits were silent.*";
        appendTerminalMessage("ghost", reply);
        state.conversationHistory.push({ role: "assistant", content: reply });
        setGhostMood("calm");
      }
    } catch (err) {
      removeTypingIndicator();
      console.error("Chat error:", err);
      appendTerminalMessage("ghost", `👻 *A phantom disconnect disrupted communication:* ${escapeHtml(err.message)}`);
      setGhostMood("calm");
    } finally {
      state.isGenerating = false;
      dom.terminalSendBtn.disabled = false;
      dom.terminalInput.focus();
    }
  }

  // --- Security Guardian Inspection ---
  async function inspectGuardianCommand(customCommand) {
    const cmd = customCommand || dom.guardianInput.value.trim();
    if (!cmd) return;

    dom.guardianInput.value = cmd;
    dom.guardianResults.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--term-cyan);">
        <div class="typing-indicator" style="justify-content: center;">
          <span>Auditing syntax, flags, and dangerous vectors...</span>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    setGhostMood("thinking", "Inspecting command patterns deterministically...");

    try {
      const resp = await fetch("/api/analyze-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, with_ai: true })
      });
      const analysis = await resp.json();

      dom.guardianResults.innerHTML = buildAnalysisCardHtml(analysis);

      if (analysis.risk_level === "CRITICAL" || analysis.risk_level === "HIGH") {
        setGhostMood("critical", `CRITICAL VULNERABILITY DETECTED in ${analysis.platform || 'shell'} command!`);
      } else if (analysis.risk_level === "SAFE") {
        setGhostMood("safe", "Command passed all safety checks without destructive patterns.");
      } else {
        setGhostMood("calm", `Command risk assessed as ${analysis.risk_level}.`);
      }
    } catch (err) {
      console.error("Guardian analysis failed:", err);
      dom.guardianResults.innerHTML = `
        <div style="color: var(--risk-critical); padding: 14px;">
          ❌ Error analyzing command: ${escapeHtml(err.message)}
        </div>
      `;
      setGhostMood("calm");
    }
  }

  // --- Haunted Archives Story Summoner ---
  async function summonHauntedArchive(cyoaChoice = null) {
    if (state.isGenerating) return;

    const payload = {
      story_type: dom.archiveStoryType.value,
      setting: dom.archiveSetting.value,
      intensity: dom.archiveIntensity.value,
      length: dom.archiveLength.value,
      prompt: dom.archivePromptInput.value.trim(),
      cyoa_choice: cyoaChoice || ""
    };

    state.isGenerating = true;
    dom.archiveSummonBtn.disabled = true;
    setGhostMood("thinking", "Summoning ghosts from the digital archive...");

    dom.archiveOutput.innerHTML = `
      <div style="padding: 24px; text-align: center; color: var(--term-purple);">
        <div class="typing-indicator" style="justify-content: center;">
          <span>Channeling phantom transmission...</span>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    dom.cyoaChoicesContainer.innerHTML = "";

    try {
      const resp = await fetch("/api/story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      const storyText = data.story || "The archives yielded only static noise...";

      dom.archiveOutput.innerHTML = `
        <div class="msg-content" style="border-left-color: var(--term-purple);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
            <span style="font-size:0.75rem; color:var(--term-purple); text-transform:uppercase; letter-spacing:1px;">
              📜 Haunted Archive // ${escapeHtml(payload.story_type)} // ${escapeHtml(payload.setting)}
            </span>
            <button class="btn-copy" onclick="copyToClipboard(this)">Copy Story</button>
          </div>
          ${formatMarkdown(storyText)}
        </div>
      `;

      // If CYOA mode, extract or create interactive choice buttons
      if (payload.story_type === "cyoa") {
        renderCyoaButtons();
      }

      setGhostMood("calm", "Archive recovered from the ether.");
    } catch (err) {
      console.error("Story summon failed:", err);
      dom.archiveOutput.innerHTML = `
        <div style="color: var(--risk-critical); padding: 14px;">
          ❌ Spectral archive corruption: ${escapeHtml(err.message)}
        </div>
      `;
      setGhostMood("calm");
    } finally {
      state.isGenerating = false;
      dom.archiveSummonBtn.disabled = false;
    }
  }

  function renderCyoaButtons() {
    dom.cyoaChoicesContainer.innerHTML = `
      <div style="width: 100%; font-size: 0.8rem; color: var(--term-purple); margin-bottom: 6px;">
        Choose your next spectral action:
      </div>
      <button class="btn-cyoa" onclick="handleCyoaChoice(1)">Option 1: Investigate the mysterious terminal prompt</button>
      <button class="btn-cyoa" onclick="handleCyoaChoice(2)">Option 2: Cut the power to the server rack</button>
      <button class="btn-cyoa" onclick="handleCyoaChoice(3)">Option 3: Send an emergency broadcast packet</button>
    `;
  }

  window.handleCyoaChoice = function(choiceNumber) {
    const choices = [
      "Investigate the mysterious terminal prompt and dump memory buffers",
      "Sever all physical power cables and disconnect from the network",
      "Transmit an encrypted emergency broadcast packet into the darkness"
    ];
    const chosenText = choices[choiceNumber - 1] || "Proceed deeper into the facility";
    summonHauntedArchive(chosenText);
  };

  // --- Keyboard Shortcuts ---
  // Terminal Input Keydown
  dom.terminalInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitTerminalMessage();
    }
  });

  // Guardian Input Keydown
  dom.guardianInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      inspectGuardianCommand();
    }
  });

  // Global Ctrl+L to Clear Conversation
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "l" || e.key === "L")) {
      e.preventDefault();
      clearTerminalConversation();
    }
  });

  function clearTerminalConversation() {
    if (confirm("👻 Clear the current haunted terminal session history?")) {
      dom.terminalStream.innerHTML = "";
      state.conversationHistory = [];
      appendTerminalMessage("system", "Session buffers purged. The ghost awaits your next command.");
    }
  }

  if (dom.clearTerminalBtn) {
    dom.clearTerminalBtn.addEventListener("click", clearTerminalConversation);
  }

  dom.terminalSendBtn.addEventListener("click", submitTerminalMessage);
  dom.guardianInspectBtn.addEventListener("click", () => inspectGuardianCommand());
  dom.archiveSummonBtn.addEventListener("click", () => summonHauntedArchive());

  // --- Quick Prompt Pills Handler ---
  document.querySelectorAll(".pill-btn").forEach(pill => {
    pill.addEventListener("click", () => {
      const target = pill.dataset.prompt;
      if (!target) return;

      if (state.activeMode === "guardian") {
        dom.guardianInput.value = target;
        inspectGuardianCommand(target);
      } else {
        dom.terminalInput.value = target;
        submitTerminalMessage();
      }
    });
  });

  // --- CRT Scanline Toggle ---
  if (dom.toggleCrtBtn) {
    dom.toggleCrtBtn.addEventListener("click", () => {
      state.crtEnabled = !state.crtEnabled;
      dom.crtOverlay.classList.toggle("disabled", !state.crtEnabled);
      dom.toggleCrtBtn.innerText = state.crtEnabled ? "📺 CRT: ON" : "📺 CRT: OFF";
    });
  }

  // --- Settings Modal Handler ---
  if (dom.settingsBtn) {
    dom.settingsBtn.addEventListener("click", () => {
      fetchStatus();
      dom.settingsModal.classList.add("open");
    });
  }

  if (dom.closeSettingsBtn) {
    dom.closeSettingsBtn.addEventListener("click", () => {
      dom.settingsModal.classList.remove("open");
    });
  }

  dom.settingsModal.addEventListener("click", (e) => {
    if (e.target === dom.settingsModal) {
      dom.settingsModal.classList.remove("open");
    }
  });

  if (dom.modalSaveModelBtn) {
    dom.modalSaveModelBtn.addEventListener("click", async () => {
      const selectedModel = dom.modalCustomModelInput.value.trim() || dom.modalModelSelect.value;
      if (!selectedModel) return;

      try {
        const resp = await fetch("/api/settings/model", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: selectedModel })
        });
        const data = await resp.json();
        if (resp.ok) {
          state.currentModel = data.current_model;
          dom.settingsModal.classList.remove("open");
          fetchStatus();
          appendTerminalMessage("system", `Active model switched to: **${escapeHtml(state.currentModel)}**`);
        } else {
          alert(`Model switch failed: ${data.error}`);
        }
      } catch (err) {
        alert(`Error communicating with backend: ${err.message}`);
      }
    });
  }

  // --- Initial Polling & Startup ---
  fetchStatus();
  setInterval(fetchStatus, 30000); // Re-check status every 30s
}

// Safe bootstrap checking document.readyState
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initGhostShell);
} else {
  initGhostShell();
}
