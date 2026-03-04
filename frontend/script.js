const API_BASE = "";

// Generate unique session ID
const SESSION_ID = 'session_' + Math.random().toString(36).substr(2, 9);

// DOM Elements
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const fileName = document.getElementById("file-name");
const uploadBtn = uploadForm.querySelector(".upload-btn");
const uploadStatus = document.getElementById("upload-status");
const documentList = document.getElementById("document-list");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const chatMessages = document.getElementById("chat-messages");
const topKInput = document.getElementById("top-k");

// Track uploaded documents
let uploadedDocuments = [];

// File Input Change Handler
fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    fileName.textContent = file.name;
    uploadBtn.disabled = false;
    document.querySelector(".file-upload-label").classList.add("has-file");
  } else {
    fileName.textContent = "Choose PDF file";
    uploadBtn.disabled = true;
    document.querySelector(".file-upload-label").classList.remove("has-file");
  }
});

// Upload PDF Handler
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    showUploadStatus("Please select a PDF file.", "error");
    return;
  }

  // Show loading state
  uploadBtn.disabled = true;
  uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
  showUploadStatus("Processing document... This may take a moment.", "loading");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Upload failed");
    }

    const data = await res.json();
    showUploadStatus(`Successfully uploaded "${file.name}"!`, "success");
    
    // Add to document list
    addDocumentToList(file.name);
    
    // Reset form
    fileInput.value = "";
    fileName.textContent = "Choose PDF file";
    document.querySelector(".file-upload-label").classList.remove("has-file");
    
    // Enable chat
    sendBtn.disabled = false;
    chatInput.placeholder = "Ask a question about your documents...";
    
  } catch (error) {
    showUploadStatus("Failed to upload document. Please try again.", "error");
    console.error(error);
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload';
  }
});

// Show upload status
function showUploadStatus(message, type) {
  uploadStatus.textContent = message;
  uploadStatus.className = `upload-status ${type}`;
}

// Add document to sidebar list
function addDocumentToList(name) {
  // Remove empty state if exists
  const emptyState = documentList.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  
  // Add new document
  uploadedDocuments.push(name);
  const li = document.createElement("li");
  li.innerHTML = `<i class="fas fa-file-pdf"></i> ${name}`;
  documentList.appendChild(li);
}

// Chat Form Handler
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = chatInput.value.trim();
  if (!query) return;

  // Clear welcome message if present
  const welcomeMsg = chatMessages.querySelector(".welcome-message");
  if (welcomeMsg) {
    welcomeMsg.remove();
  }

  // Add user message
  addMessage(query, "user");
  chatInput.value = "";
  chatInput.style.height = "auto";
  sendBtn.disabled = true;

  // Show typing indicator
  const typingId = showTypingIndicator();

  try {
    const k = parseInt(topKInput.value) || 5;
    
    // Use new LangChain chat endpoint
    const res = await fetch(`${API_BASE}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        session_id: SESSION_ID,
        top_k: k,
        advanced: true  // Use advanced chat with query rewriting
      }),
    });

    // Remove typing indicator
    removeTypingIndicator(typingId);

    if (!res.ok) {
      throw new Error("Chat request failed");
    }

    const data = await res.json();
    addBotMessage(data.answer, data.chunks_used, data.rewritten_query);
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addMessage("Sorry, I encountered an error. Please try again.", "bot");
    console.error(error);
  }
});

// Add message to chat
function addMessage(text, type) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${type}`;
  
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.innerHTML = type === "user" 
    ? '<i class="fas fa-user"></i>' 
    : '<i class="fas fa-robot"></i>';
  
  const content = document.createElement("div");
  content.className = "message-content";
  content.innerHTML = `<p>${escapeHtml(text)}</p>`;
  
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(content);
  chatMessages.appendChild(messageDiv);
  scrollToBottom();
}

// Add bot message with sources
function addBotMessage(answer, chunks, rewrittenQuery = null) {
  const messageDiv = document.createElement("div");
  messageDiv.className = "message bot";
  
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.innerHTML = '<i class="fas fa-robot"></i>';
  
  const content = document.createElement("div");
  content.className = "message-content";
  
  // Format answer (convert newlines to paragraphs)
  const formattedAnswer = answer
    .split("\n")
    .filter(p => p.trim())
    .map(p => `<p>${escapeHtml(p)}</p>`)
    .join("");
  
  content.innerHTML = formattedAnswer;
  
  // Show rewritten query if different from original
  if (rewrittenQuery) {
    const queryNote = document.createElement("div");
    queryNote.className = "rewritten-query";
    queryNote.innerHTML = `<i class="fas fa-search"></i> Searched for: "${escapeHtml(rewrittenQuery)}"`;
    content.appendChild(queryNote);
  }
  
  // Add sources if available
  if (chunks && chunks.length > 0) {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "sources";
    
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "sources-toggle";
    toggleBtn.innerHTML = `<i class="fas fa-book"></i> View Sources (${chunks.length})`;
    
    const sourcesContent = document.createElement("div");
    sourcesContent.className = "sources-content";
    
    chunks.forEach((chunk, index) => {
      const sourceItem = document.createElement("div");
      sourceItem.className = "source-item";
      sourceItem.innerHTML = `
        <div>${escapeHtml(chunk.text || chunk)}</div>
        ${chunk.score ? `<div class="source-meta">Relevance: ${(chunk.score * 100).toFixed(1)}%</div>` : ''}
      `;
      sourcesContent.appendChild(sourceItem);
    });
    
    toggleBtn.addEventListener("click", () => {
      sourcesContent.classList.toggle("show");
      const icon = toggleBtn.querySelector("i");
      icon.className = sourcesContent.classList.contains("show") 
        ? "fas fa-book-open" 
        : "fas fa-book";
    });
    
    sourcesDiv.appendChild(toggleBtn);
    sourcesDiv.appendChild(sourcesContent);
    content.appendChild(sourcesDiv);
  }
  
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(content);
  chatMessages.appendChild(messageDiv);
  scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
  const id = "typing-" + Date.now();
  const messageDiv = document.createElement("div");
  messageDiv.className = "message bot";
  messageDiv.id = id;
  
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.innerHTML = '<i class="fas fa-robot"></i>';
  
  const content = document.createElement("div");
  content.className = "message-content";
  content.innerHTML = `
    <div class="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;
  
  messageDiv.appendChild(avatar);
  messageDiv.appendChild(content);
  chatMessages.appendChild(messageDiv);
  scrollToBottom();
  
  return id;
}

// Remove typing indicator
function removeTypingIndicator(id) {
  const indicator = document.getElementById(id);
  if (indicator) {
    indicator.remove();
  }
}

// Scroll to bottom of chat
function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Auto-resize textarea
chatInput.addEventListener("input", function() {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 150) + "px";
  
  // Enable/disable send button based on input
  sendBtn.disabled = !this.value.trim();
});

// Handle Enter key for sending (Shift+Enter for new line)
chatInput.addEventListener("keydown", function(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (this.value.trim()) {
      chatForm.dispatchEvent(new Event("submit"));
    }
  }
});

// New Chat Button Handler
const newChatBtn = document.getElementById("new-chat-btn");
const sessionBadge = document.getElementById("session-badge");

newChatBtn.addEventListener("click", async () => {
  // Clear chat history on server
  try {
    await fetch(`${API_BASE}/chat/history/${SESSION_ID}`, {
      method: "DELETE"
    });
  } catch (e) {
    console.error("Failed to clear server history:", e);
  }
  
  // Clear chat messages UI
  chatMessages.innerHTML = `
    <div class="welcome-message">
      <div class="welcome-icon">
        <i class="fas fa-comments"></i>
      </div>
      <h2>Welcome to RAG Chat!</h2>
      <p>Upload your PDF documents using the sidebar, then ask questions about them.</p>
      <div class="quick-tips">
        <div class="tip">
          <i class="fas fa-lightbulb"></i>
          <span>Upload multiple PDFs to build your knowledge base</span>
        </div>
        <div class="tip">
          <i class="fas fa-search"></i>
          <span>Ask specific questions for better answers</span>
        </div>
        <div class="tip">
          <i class="fas fa-brain"></i>
          <span>AI uses your documents to provide accurate responses</span>
        </div>
      </div>
    </div>
  `;
  
  // Generate new session ID
  window.location.reload();
});

// Display session ID
sessionBadge.textContent = `Session: ${SESSION_ID.slice(-6)}`;
