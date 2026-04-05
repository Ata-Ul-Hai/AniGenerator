const state = {
  extractedText: "",
  pollTimer: null,
  activeJobId: null,
  authToken: localStorage.getItem("anigen.authToken") || "",
};

const POLL_INTERVAL_MS = 900;

const el = {
  docFile: document.getElementById("docFile"),
  maxScenes: document.getElementById("maxScenes"),
  authToken: document.getElementById("authToken"),
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

const getAuthHeaderValue = () => {
  const rawToken = (el.authToken?.value || state.authToken || "").trim();
  if (!rawToken) {
    return "";
  }
  return rawToken.startsWith("Bearer ") ? rawToken : `Bearer ${rawToken}`;
};

const buildAuthHeaders = (baseHeaders = {}) => {
  const headers = { ...baseHeaders };
  const authHeader = getAuthHeaderValue();
  if (authHeader) {
    headers.Authorization = authHeader;
  }
  return headers;
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

  const response = await fetch("/upload", {
    method: "POST",
    headers: buildAuthHeaders(),
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
      const response = await fetch(`/jobs/${jobId}`, {
        headers: buildAuthHeaders(),
      });
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
          const nextSrc = `/${job.video_path}?v=${Date.now()}`;
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

  const response = await fetch("/generate/async", {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
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

if (el.authToken) {
  el.authToken.value = state.authToken;
  el.authToken.addEventListener("change", () => {
    state.authToken = (el.authToken.value || "").trim();
    localStorage.setItem("anigen.authToken", state.authToken);
  });
}
