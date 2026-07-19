const form = document.getElementById("composerForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const messages = document.getElementById("messages");
const newChatBtn = document.getElementById("newChatBtn");
const historyList = document.getElementById("historyList");

const WELCOME_TEXT =
  "Hi, I'm MedicAsk. Ask me about a condition, symptom, or treatment " +
  "and I'll answer using the reference material I have access to. " +
  "I can't diagnose you — for anything urgent, contact a healthcare " +
  "provider directly.";

let conversationId = null;

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function formatAnswer(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = escaped.split("\n");
  let html = "";
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line.startsWith("* ") || line.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${line.slice(2)}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (line) html += `<p>${line}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

function addMessage(text, role, sources = []) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg msg-${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if (role === "bot") {
    bubble.innerHTML = formatAnswer(text);
  } else {
    bubble.textContent = text;
  }

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

const THINKING_PHRASES = [
  "Searching the reference material…",
  "Reading the retrieved context…",
  "Thinking through the answer…",
  "Putting the response together…",
];

function addStreamingBubble() {
  const wrapper = document.createElement("div");
  wrapper.className = "msg msg-bot";

  const bubble = document.createElement("div");
  bubble.className = "bubble streaming";
  bubble.innerHTML = `
    <span class="pulse-inline">
      <svg viewBox="0 0 46 14">
        <polyline points="0,7 12,7 16,1 20,13 24,7 46,7" />
      </svg>
    </span>
    <span class="thinking-text">${THINKING_PHRASES[0]}</span>
  `;

  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  scrollToBottom();

  let phraseIndex = 0;
  const textEl = bubble.querySelector(".thinking-text");
  const intervalId = setInterval(() => {
    phraseIndex = (phraseIndex + 1) % THINKING_PHRASES.length;
    if (textEl) textEl.textContent = THINKING_PHRASES[phraseIndex];
  }, 1800);

  return { wrapper, bubble, stopThinking: () => clearInterval(intervalId) };
}

function setBusy(isBusy) {
  sendBtn.disabled = isBusy;
  input.disabled = isBusy;
}

// ---------------------------------------------------------------------------
// Conversation history sidebar
// ---------------------------------------------------------------------------

async function loadHistoryList() {
  try {
    const res = await fetch("/api/conversations");
    const list = await res.json();
    renderHistoryList(list);
  } catch (err) {
    // sidebar just stays empty if this fails — non-fatal
  }
}

function renderHistoryList(list) {
  historyList.innerHTML = "";
  for (const convo of list) {
    const row = document.createElement("div");
    row.className = "history-row";

    const item = document.createElement("button");
    item.type = "button";
    item.className = "history-item";
    if (convo.id === conversationId) item.classList.add("active");
    item.textContent = convo.title || "New conversation";
    item.addEventListener("click", () => openConversation(convo.id));

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "history-delete";
    deleteBtn.setAttribute("aria-label", "Delete conversation");
    deleteBtn.innerHTML = "&times;";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(convo.id);
    });

    row.appendChild(item);
    row.appendChild(deleteBtn);
    historyList.appendChild(row);
  }
}

async function deleteConversation(id) {
  const confirmed = window.confirm("Delete this conversation? This can't be undone.");
  if (!confirmed) return;

  try {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
  } catch (err) {
    // continue regardless — refresh list either way
  }

  if (id === conversationId) {
    await startNewConversation();
  } else {
    await loadHistoryList();
  }
}

async function openConversation(id) {
  try {
    const res = await fetch(`/api/conversations/${id}`);
    if (!res.ok) return;
    const convo = await res.json();

    conversationId = convo.id;
    messages.innerHTML = "";

    if (convo.messages.length === 0) {
      addMessage(WELCOME_TEXT, "bot");
    } else {
      for (const m of convo.messages) {
        addMessage(m.text, m.role, m.sources || []);
      }
    }

    await loadHistoryList();
  } catch (err) {
    // ignore — user can just try again
  }
}

async function startNewConversation() {
  const res = await fetch("/api/new", { method: "POST" });
  const convo = await res.json();
  conversationId = convo.id;
  messages.innerHTML = "";
  addMessage(WELCOME_TEXT, "bot");
  await loadHistoryList();
}

// ---------------------------------------------------------------------------
// Sending messages
// ---------------------------------------------------------------------------

async function sendMessage(message) {
  addMessage(message, "user");
  setBusy(true);

  const { wrapper, bubble, stopThinking } = addStreamingBubble();
  let fullText = "";
  let sources = [];
  let firstToken = true;

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });

    if (!res.ok || !res.body) {
      throw new Error("Request failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;

        const payload = JSON.parse(line.slice(5).trim());

        if (payload.type === "token") {
          if (firstToken) {
            stopThinking();
            bubble.classList.remove("streaming");
            bubble.innerHTML = "";
            firstToken = false;
          }
          fullText += payload.text;
          bubble.innerHTML = formatAnswer(fullText);
          scrollToBottom();
        } else if (payload.type === "done") {
          sources = payload.sources || [];
        } else if (payload.type === "error") {
          fullText = payload.text;
          bubble.classList.remove("streaming");
          bubble.innerHTML = formatAnswer(fullText);
        }
      }
    }

    if (sources.length) {
      const src = document.createElement("div");
      src.className = "sources";
      src.textContent = "Source: " + sources.join(", ");
      wrapper.appendChild(src);
    }

    if (!fullText) {
      bubble.classList.remove("streaming");
      bubble.innerHTML = formatAnswer("I don't know based on the available information.");
    }

    await loadHistoryList();

  } catch (err) {
    stopThinking();
    bubble.classList.remove("streaming");
    bubble.innerHTML = formatAnswer("Couldn't reach the assistant. Is the server running?");
  } finally {
    stopThinking();
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

newChatBtn.addEventListener("click", startNewConversation);

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

(async function init() {
  try {
    const res = await fetch("/api/conversations");
    const list = await res.json();
    renderHistoryList(list);

    if (list.length > 0) {
      await openConversation(list[0].id);
      return;
    }
  } catch (err) {
    // fall through to starting a fresh conversation
  }
  await startNewConversation();
})();