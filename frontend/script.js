const API_BASE = "http://127.0.0.1:8000";

// Upload PDF
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = e.target.file;
  const file = fileInput.files[0];
  if (!file) {
    alert("Please select a PDF file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    document.getElementById("upload-result").innerText = "Upload failed.";
    return;
  }

  const data = await res.json();
  document.getElementById("upload-result").innerText = JSON.stringify(data, null, 2);
});

// Search
document.getElementById("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = e.target.q.value;
  const k = e.target.k.value;

  const body = new URLSearchParams();
  body.append("q", q);
  body.append("k", k);

  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString()
  });

  if (!res.ok) {
    document.getElementById("search-result").innerText = "Search failed.";
    return;
  }

  const data = await res.json();
  document.getElementById("search-result").innerHTML = 
    "<h3>Answer</h3><pre>" + data.answer + "</pre>" +
    "<h4>Chunks used</h4><pre>" + JSON.stringify(data.chunks_used, null, 2) + "</pre>";
});
