import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";
import { Upload, Zap, LogOut, Loader2, CheckCircle2, XCircle, Clock, FileVideo } from "lucide-react";

interface Props {
  token: string;
  onLogout: () => void;
}

type JobStatus = "queued" | "running" | "completed" | "failed";

interface JobState {
  id: string;
  status: JobStatus;
  error?: string;
  video_path?: string;
}

const STATUS: Record<JobStatus, { icon: React.ElementType; color: string; label: string }> = {
  queued:    { icon: Clock,         color: "text-zinc-400",    label: "Queued"    },
  running:   { icon: Loader2,       color: "text-blue-400",    label: "Running"   },
  completed: { icon: CheckCircle2,  color: "text-emerald-400", label: "Completed" },
  failed:    { icon: XCircle,       color: "text-red-400",     label: "Failed"    },
};

const Dashboard: React.FC<Props> = ({ token, onLogout }) => {
  const [file, setFile]                  = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [maxScenes, setMaxScenes]         = useState(12);
  const [renderVideo, setRenderVideo]     = useState(true);
  const [job, setJob]                     = useState<JobState | null>(null);
  const [stage, setStage]                 = useState<"idle"|"extracting"|"extracted"|"generating">("idle");
  const [statusMsg, setStatusMsg]         = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const authHeader = { Authorization: `Bearer ${token}` };

  const stopPolling = () => { if (pollRef.current) clearInterval(pollRef.current); };

  const pollJob = (jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const res  = await fetch(`${API}/jobs/${jobId}`, { headers: authHeader });
        const data = await res.json();
        setJob(data);
        if (data.status === "completed" || data.status === "failed") {
          stopPolling();
          setStage("idle");
          setStatusMsg(data.status === "completed" ? "Video ready!" : `Failed: ${data.error ?? "unknown"}`);
        }
      } catch { stopPolling(); }
    }, 3000);
  };

  const handleExtract = async () => {
    if (!file) return;
    setStage("extracting"); setStatusMsg("Extracting text…");
    const form = new FormData();
    form.append("file", file);
    try {
      const res  = await fetch(`${API}/upload`, { method: "POST", headers: authHeader, body: form });
      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setExtractedText(data.extracted_text);
      setStage("extracted");
      setStatusMsg(`Extracted ${data.chunk_count} chunk(s).`);
    } catch (e: unknown) {
      setStage("idle");
      setStatusMsg(e instanceof Error ? e.message : "Error");
    }
  };

  const handleGenerate = async () => {
    setStage("generating"); setStatusMsg("Queuing job…");
    try {
      const res  = await fetch(`${API}/generate/async`, {
        method:  "POST",
        headers: { ...authHeader, "Content-Type": "application/json" },
        body:    JSON.stringify({ extracted_text: extractedText, max_scenes: maxScenes, render_video: renderVideo }),
      });
      if (!res.ok) throw new Error("Failed to queue job");
      const data = await res.json();
      setJob(data);
      setStatusMsg("Job queued — polling for updates…");
      pollJob(data.job_id);
    } catch (e: unknown) {
      setStage("idle");
      setStatusMsg(e instanceof Error ? e.message : "Error");
    }
  };

  const S = job ? STATUS[job.status] : null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">

      {/* NAV */}
      <nav className="border-b border-zinc-900 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-semibold tracking-tight">AniGenerator</span>
            <span className="text-zinc-700 text-sm">· Control Room</span>
          </div>
          <button onClick={onLogout} className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </nav>

      {/* MAIN */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* ENGINE CONFIG */}
        <div className="lg:col-span-2 flex flex-col gap-5">

          {/* Upload card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <h2 className="text-[10px] tracking-[0.25em] uppercase text-zinc-500 mb-4">Source Document</h2>
            <label className="flex flex-col items-center gap-3 border-2 border-dashed border-zinc-800 rounded-xl p-8 cursor-pointer hover:border-zinc-700 transition-colors group">
              <Upload size={20} className="text-zinc-700 group-hover:text-zinc-500 transition-colors" />
              <div className="text-center">
                <p className="text-sm text-zinc-400">{file ? file.name : "Drop file or click to upload"}</p>
                <p className="text-xs text-zinc-700 mt-1">PDF · DOCX · TXT</p>
              </div>
              <input type="file" accept=".pdf,.docx,.txt" className="hidden"
                onChange={(e) => { if (e.target.files?.[0]) setFile(e.target.files[0]); }} />
            </label>

            <button
              onClick={handleExtract}
              disabled={!file || stage === "extracting"}
              className={cn(
                "mt-4 w-full py-3 rounded-xl text-sm font-medium transition-all duration-200",
                !file || stage === "extracting"
                  ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                  : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
              )}
            >
              {stage === "extracting" ? "Extracting…" : "1. Extract Text"}
            </button>
          </div>

          {/* Config card */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-5">
            <h2 className="text-[10px] tracking-[0.25em] uppercase text-zinc-500">Generation Config</h2>

            <div className="space-y-2">
              <label className="text-xs text-zinc-600">Max Scenes</label>
              <input type="number" value={maxScenes} min={1} max={20}
                onChange={(e) => setMaxScenes(+e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100 text-sm focus:outline-none focus:border-zinc-700" />
            </div>

            <label className="flex items-center gap-3 cursor-pointer select-none">
              <button
                type="button"
                onClick={() => setRenderVideo(!renderVideo)}
                className={cn(
                  "w-9 h-5 rounded-full relative transition-colors duration-200 flex-shrink-0",
                  renderVideo ? "bg-zinc-200" : "bg-zinc-800"
                )}
              >
                <span className={cn(
                  "absolute top-0.5 w-4 h-4 rounded-full bg-zinc-900 transition-all duration-200",
                  renderVideo ? "left-4" : "left-0.5"
                )} />
              </button>
              <span className="text-sm text-zinc-400">Render MP4 Video</span>
            </label>

            <button
              onClick={handleGenerate}
              disabled={!extractedText || stage === "generating"}
              className={cn(
                "w-full py-3 rounded-xl text-sm font-semibold transition-all duration-200",
                !extractedText || stage === "generating"
                  ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                  : "bg-zinc-100 text-zinc-900 hover:bg-white hover:scale-[1.02] active:scale-[0.98]"
              )}
            >
              <span className="flex items-center justify-center gap-2">
                <Zap size={13} />
                {stage === "generating" ? "Generating…" : "2. Generate & Render"}
              </span>
            </button>
          </div>
        </div>

        {/* RIGHT PANELS */}
        <div className="lg:col-span-3 flex flex-col gap-5">

          {/* Job status */}
          <AnimatePresence>
            {job && S && (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5"
              >
                <h2 className="text-[10px] tracking-[0.25em] uppercase text-zinc-500 mb-3">Job Status</h2>
                <div className="flex items-center gap-2.5">
                  <S.icon size={16} className={cn(S.color, job.status === "running" ? "animate-spin" : "")} />
                  <span className={cn("text-sm font-medium", S.color)}>{S.label}</span>
                  <span className="text-[10px] text-zinc-800 font-mono ml-auto">{job.id}</span>
                </div>
                {statusMsg && <p className="text-xs text-zinc-600 mt-2">{statusMsg}</p>}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Video preview */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex-1">
            <h2 className="text-[10px] tracking-[0.25em] uppercase text-zinc-500 mb-4">Whiteboard Preview</h2>
            {job?.video_path ? (
              <video src={job.video_path} controls className="w-full rounded-xl bg-zinc-950" />
            ) : (
              <div className="flex flex-col items-center justify-center h-44 gap-3 text-zinc-800">
                <FileVideo size={28} />
                <p className="text-sm">Ready for generation</p>
              </div>
            )}
          </div>

          {/* Extracted text */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
            <h2 className="text-[10px] tracking-[0.25em] uppercase text-zinc-500 mb-3">Extracted Text Preview</h2>
            <div className="h-28 overflow-y-auto scrollbar-thin">
              {extractedText ? (
                <p className="text-[11px] text-zinc-500 leading-relaxed font-mono whitespace-pre-wrap">{extractedText}</p>
              ) : (
                <p className="text-xs text-zinc-800">No text extracted yet.</p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
