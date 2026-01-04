const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const generateBtn = document.getElementById("generateBtn");

const setStatus = (message, variant = "info") => {
  statusEl.textContent = message;
  statusEl.dataset.variant = variant;
};

const renderResults = (payload) => {
  resultsEl.innerHTML = "";
  if (!payload.results || payload.results.length === 0) {
    resultsEl.innerHTML = "<p class='muted'>No packages generated yet.</p>";
    return;
  }
  const list = document.createElement("ul");
  list.className = "results__list";
  payload.results.forEach((item) => {
    const row = document.createElement("li");
    row.className = "results__item";
    row.innerHTML = `
      <div>
        <strong>${item.faa_id}</strong>
        <span class="muted">${item.name}</span>
        <div class="results__meta">Job: ${item.job_path}</div>
        <div class="results__meta">Scene: ${item.scene_path}</div>
      </div>
      <a class="button button--secondary" href="${item.zip_url}">Download ZIP</a>
    `;
    list.appendChild(row);
  });
  resultsEl.appendChild(list);
};

const gatherPayload = () => ({
  faa_ids: document.getElementById("faaIds").value,
  csv_data: document.getElementById("csvData").value,
  output_dir: document.getElementById("outputDir").value,
  jobs_dir: document.getElementById("jobsDir").value,
  aoi_radius_m: document.getElementById("aoiRadius").value,
});

generateBtn.addEventListener("click", async () => {
  setStatus("Generating scenery packages...", "info");
  generateBtn.disabled = true;
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(gatherPayload()),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Unable to generate packages.");
    }
    renderResults(data);
    setStatus(`Generated ${data.results.length} package(s).`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    generateBtn.disabled = false;
  }
});
