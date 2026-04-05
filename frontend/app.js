const state = {
  extractedText: "",
  pollTimer: null,
  activeJobId: null,
};

// For hybrid deployment: Set this to your Cloud Run URL (e.g. https://anigen-backend-xyz.a.run.app)
// If empty, it defaults to the same domain (useful for local dev).
const API_BASE_URL = window.location.hostname === "localhost" ? "" : (window.API_BASE_URL || "");

const POLL_INTERVAL_MS = 900;

const el = {
  docFile: document.getElementById("docFile"),
  maxScenes: document.getElementById("maxScenes"),
  renderVideo: document.getElementById("renderVideo"),
  uploadBtn: document.getElementById("uploadBtn"),
  generateBtn: document.getElementById("generateBtn"),
  statusBox: document.getElementById("statusBox"),
  chunkCount: document.getElementById("chunkCount"),
  sceneCount: document.getElementById("sceneCount"),
  jobState: document.getElementById("jobState"),
  textPreview: document.getElementById("textPreview"),
  videoPreview: document.getElementById("videoPreview"),
};

const setStatus = (message, level = "") => {
  el.statusBox.textContent = message;
  el.statusBox.className = `status ${level}`.trim();
};

const stopPolling = () => {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
};

const requireFile = () => {
  const file = el.docFile.files?.[0];
  if (!file) {
    throw new Error("Please choose a document first.");
  }
  return file;
};

const uploadDocument = async () => {
  const file = requireFile();
  setStatus("Uploading and extracting text...", "warn");

  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Upload failed: ${detail}`);
  }

  const payload = await response.json();
  state.extractedText = payload.extracted_text;

  el.chunkCount.textContent = String(payload.chunk_count ?? 0);
  el.textPreview.textContent = (payload.extracted_text || "").slice(0, 2500);
  el.generateBtn.disabled = !state.extractedText;

  setStatus("Text extraction complete.", "ok");
};

const pollJob = (jobId) => {
  stopPolling();
  state.activeJobId = jobId;
  let pending = false;

  const fetchStatus = async () => {
    if (pending) {
      return;
    }

    pending = true;
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch job status: ${response.status}`);
      }

      const job = await response.json();
      el.jobState.textContent = job.status;

      if (job.status === "completed") {
        stopPolling();
        el.generateBtn.disabled = false;
        setStatus("Job completed.", "ok");

        const scenes = job.render_props?.scenes || [];
        el.sceneCount.textContent = String(scenes.length);

        if (job.video_path) {
          const nextSrc = `${API_BASE_URL}/${job.video_path}?v=${Date.now()}`;
          el.videoPreview.pause();
          el.videoPreview.removeAttribute("src");
          el.videoPreview.src = nextSrc;
          el.videoPreview.load();
        }
      }

      if (job.status === "failed") {
        stopPolling();
        el.generateBtn.disabled = false;
        setStatus(job.error || "Generation failed.", "err");
      }
    } catch (error) {
      stopPolling();
      el.generateBtn.disabled = false;
      setStatus(error.message || "Job polling failed.", "err");
    } finally {
      pending = false;
    }
  };

  // Start with an immediate read so completion is reflected as soon as possible.
  void fetchStatus();
  state.pollTimer = setInterval(fetchStatus, POLL_INTERVAL_MS);
};

const generateAsync = async () => {
  if (!state.extractedText) {
    throw new Error("Run text extraction first.");
  }

  setStatus("Submitting async generation job...", "warn");
  el.jobState.textContent = "Queued";
  el.generateBtn.disabled = true;

  const payload = {
    extracted_text: state.extractedText,
    max_scenes: Number(el.maxScenes.value || 12),
    render_video: Boolean(el.renderVideo.checked),
  };

  const response = await fetch(`${API_BASE_URL}/generate/async`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Generation submit failed: ${detail}`);
  }

  const data = await response.json();
  setStatus(`Queued job ${data.job_id}. Polling status...`, "warn");
  pollJob(data.job_id);
};

el.uploadBtn.addEventListener("click", async () => {
  try {
    await uploadDocument();
  } catch (error) {
    setStatus(error.message || "Upload failed.", "err");
  }
});

el.generateBtn.addEventListener("click", async () => {
  try {
    await generateAsync();
  } catch (error) {
    setStatus(error.message || "Generation failed.", "err");
  }
});
