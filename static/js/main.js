const form = document.getElementById("composerForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const messages = document.getElementById("messages");
const newChatBtn = document.getElementById("newChatBtn");

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(text, role, sources = []) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg msg-${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrapper.appendChild(bubble);

  if (sources.length) {
    const src = document.createElement("div");
    src.className = "sources";
    src.textContent = "Source: " + sources.join(", ");
    wrapper.appendChild(src);
  }

  messages.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function addThinkingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "msg msg-bot thinking";
  wrapper.innerHTML = `
    <div class="bubble">
      <svg viewBox="0 0 46 14">
        <polyline points="0,7 12,7 16,1 20,13 24,7 46,7" />
      </svg>
    </div>
  `;
  messages.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function setBusy(isBusy) {
  sendBtn.disabled = isBusy;
  input.disabled = isBusy;
}

async function sendMessage(message) {
  addMessage(message, "user");
  const thinking = addThinkingIndicator();
  setBusy(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await res.json();
    thinking.remove();

    if (!res.ok) {
      addMessage(data.error || "Something went wrong. Please try again.", "bot");
      return;
    }

    addMessage(data.answer, "bot", data.sources || []);
  } catch (err) {
    thinking.remove();
    addMessage("Couldn't reach the assistant. Is the server running?", "bot");
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.value = "";
  sendMessage(value);
});

newChatBtn.addEventListener("click", () => {
  messages.innerHTML = "";
  addMessage(
    "Hi, I'm MedicAsk. Ask me about a condition, symptom, or treatment " +
    "and I'll answer using the reference material I have access to. " +
    "I can't diagnose you — for anything urgent, contact a healthcare " +
    "provider directly.",
    "bot"
  );
  input.focus();
});

function formatAnswer(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = escaped.split("\n");
  let html = "";
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${trimmed.slice(2)}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (trimmed) html += `<p>${trimmed}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}


function formatAnswer(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = escaped.split("\n");
  let html = "";
  let inList = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${trimmed.slice(2)}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (trimmed) html += `<p>${trimmed}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}