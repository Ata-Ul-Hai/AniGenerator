import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import { cn } from "../lib/utils";
import { 
  Upload, LogOut, Loader2, FileVideo, 
  FileText, Settings, AlertCircle, ArrowRight,
  CheckCircle2, Sparkles, Shield, Copy, Check, Clock, Film
} from "lucide-react";
import anigenLogo from "../assets/AnigenLogo.png";
import api from "../api/api";
import { useAuth } from "../context/AuthContext";

interface Props {
  token: string;
  onLogout: () => void;
}

type JobStatus = "queued" | "running" | "rendering" | "completed" | "failed";

interface JobState {
  job_id: string;
  status: JobStatus;
  error?: string;
  video_path?: string;
}

const MAX_POLL_ATTEMPTS = 200; // ~10 minutes at 3s intervals
const MAX_CLIENT_FILE_SIZE_MB = 20;
const ACCEPTED_FILE_TYPES = ".pdf,.docx,.txt";

/** Resolves a video path to a full URL, handling both absolute and relative paths. */
const resolveVideoUrl = (path: string) =>
  path.startsWith("http") ? path : `/api/${path.replace(/^\//, "")}`;

const Dashboard: React.FC<Props> = ({ onLogout }) => {
  const { user, checkAuth } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [renderVideo, setRenderVideo] = useState(true);
  const [selectedStyle, setSelectedStyle] = useState<"expo" | "blueprint" | "chalk">("expo");
  const [job, setJob] = useState<JobState | null>(null);
  const [stage, setStage] = useState<"idle" | "extracting" | "extracted" | "generating">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [isError, setIsError] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [copiedJobId, setCopiedJobId] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  // Check onboarding status
  useEffect(() => {
    if (user && !user.has_seen_onboarding) {
      const timer = setTimeout(() => {
        setShowOnboarding(true);
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [user]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  // Track elapsed generation time
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (stage === "generating" || job?.status === "running" || job?.status === "rendering") {
      interval = setInterval(() => {
        setElapsedSeconds((s) => s + 1);
      }, 1000);
    } else {
      const resetTimer = setTimeout(() => setElapsedSeconds(0), 0);
      return () => clearTimeout(resetTimer);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [stage, job?.status]);

  const handleAcknowledgeOnboarding = async () => {
    try {
      await api.post('/user/mark-onboarded');
      await checkAuth();
      setShowOnboarding(false);
    } catch (err) {
      console.error('Failed to mark onboarded', err);
      setShowOnboarding(false);
    }
  };

  const copyJobId = () => {
    if (job?.job_id) {
      navigator.clipboard.writeText(job.job_id);
      setCopiedJobId(true);
      setTimeout(() => setCopiedJobId(false), 2000);
    }
  };

  const pollJob = (jobId: string) => {
    if (pollRef.current) clearTimeout(pollRef.current);
    pollCountRef.current = 0;

    const executePoll = async () => {
      pollCountRef.current += 1;

      if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
        pollRef.current = null;
        setIsError(true);
        setStatusMsg("Polling timeout — job may still be rendering. Refresh to check status.");
        setStage("idle");
        return;
      }

      try {
        const res = await api.get(`/user/jobs/${jobId}`);
        const data = res.data;
        setJob(data);
        if (data.status === "completed" || data.status === "failed") {
          pollRef.current = null;
          setStage("idle");
          setIsError(data.status === "failed");
          setStatusMsg(data.status === "completed" ? "Whiteboard video successfully rendered!" : `Engine Error: ${data.error || "Unknown error"}`);
          return;
        }
      } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          pollRef.current = null;
          setIsError(true);
          setStatusMsg("Session expired. Please log in again.");
          setStage("idle");
          return;
        }
        pollRef.current = null;
        setIsError(true);
        const message = err instanceof Error ? err.message : "Unknown error";
        setStatusMsg(`Network Error: ${message}`);
        return;
      }
      
      pollRef.current = setTimeout(executePoll, 3000);
    };

    executePoll();
  };

  const handleExtract = async () => {
    if (!file) return;

    if (file.size > MAX_CLIENT_FILE_SIZE_MB * 1024 * 1024) {
      setIsError(true);
      setStatusMsg(`File exceeds ${MAX_CLIENT_FILE_SIZE_MB}MB limit. Please upload a smaller document.`);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setStage("extracting");
    setIsError(false);
    setStatusMsg("Extracting semantic hierarchy and stripping noise...");

    try {
      const res = await api.post("/document/extract", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setExtractedText(res.data.text);
      setStage("extracted");
      setStatusMsg(`Extraction complete (${res.data.text.length} characters parsed). Ready to storyboard.`);
    } catch (err: unknown) {
      setIsError(true);
      setStage("idle");
      let message = "Unknown error";
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        message = typeof detail === "object" ? detail.message || JSON.stringify(detail) : detail || err.message;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setStatusMsg(`Extraction failed: ${message}`);
    }
  };

  const handleGenerate = async () => {
    if (!extractedText) return;

    setStage("generating");
    setIsError(false);
    setStatusMsg("Submitting storyboard script to Gemini Flash Director...");

    try {
      const res = await api.post("/user/generate", {
        text: extractedText,
        render_video: renderVideo,
      });

      const newJob: JobState = {
        job_id: res.data.job_id,
        status: res.data.status || "queued",
      };
      setJob(newJob);
      setStatusMsg("Job queued. Initializing Remotion Chromium worker...");
      pollJob(res.data.job_id);
    } catch (err: unknown) {
      setIsError(true);
      setStage("idle");
      let message = "Unknown error";
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        message = typeof detail === "object" ? detail.message || JSON.stringify(detail) : detail || err.message;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setStatusMsg(`Generation failed: ${message}`);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    const ext = selected.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "docx", "txt"].includes(ext)) {
      setIsError(true);
      setStatusMsg("Unsupported file format. Please upload PDF, DOCX, or TXT.");
      return;
    }

    setFile(selected);
    setExtractedText("");
    setJob(null);
    setStatusMsg("");
    setIsError(false);
    setStage("idle");
  };

  // Determine active pipeline step index (0-3)
  const getActivePipelineStep = () => {
    if (job?.status === "completed") return 4;
    if (job?.status === "rendering") return 3;
    if (job?.status === "running") return 2;
    if (stage === "generating" || job?.status === "queued") return 1;
    if (stage === "extracted") return 1;
    if (stage === "extracting" || file) return 0;
    return -1;
  };

  const activeStep = getActivePipelineStep();

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col font-sans selection:bg-orange-100 selection:text-orange-900">
      {/* Onboarding Dialog */}
      {showOnboarding && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white border border-zinc-200 rounded-2xl p-7 max-w-md w-full shadow-2xl relative overflow-hidden">
            <div className="w-12 h-12 rounded-xl border border-zinc-200 bg-white p-2 flex items-center justify-center mb-5 shadow-xs">
              <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain" />
            </div>

            <h2 className="text-xl font-bold text-zinc-900 mb-2">Welcome to AniGenerator Studio</h2>
            <p className="text-zinc-600 text-xs sm:text-sm mb-5 leading-relaxed">
              You've been authorized for beta access. To optimize our distributed Remotion rendering clusters, access is scoped to:
            </p>

            <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-4 mb-5 flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-orange-100 border border-orange-200 flex items-center justify-center text-orange-700 shrink-0 mt-0.5">
                <Sparkles size={16} />
              </div>
              <div>
                <strong className="block text-zinc-900 text-xs font-bold mb-0.5">1 Completed Whiteboard Video / 24 Hours</strong>
                <span className="text-[11px] text-zinc-500">Failed attempts or test extractions do not count against your quota.</span>
              </div>
            </div>

            <button 
              onClick={handleAcknowledgeOnboarding}
              className="w-full py-3 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-xl text-xs transition-all shadow-xs"
            >
              Enter Studio Workspace
            </button>
          </div>
        </div>
      )}

      {/* Studio Header Bar */}
      <nav className="h-16 border-b border-zinc-200 bg-white/95 backdrop-blur-md px-6 md:px-8 flex items-center justify-between sticky top-0 z-40">
        {/* Left: Studio Identity */}
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 rounded-xl border border-zinc-200 bg-white p-1.5 flex items-center justify-center shadow-xs">
            <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-extrabold tracking-tight text-zinc-900">AniGenerator Studio</h1>
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-200">
                Director Beta
              </span>
            </div>
            <p className="text-[10px] text-zinc-500 -mt-0.5 font-mono">Workspace #01 • Local Engine</p>
          </div>
        </div>

        {/* Right: Studio Status & Actions */}
        <div className="flex items-center gap-3">
          {/* Daily Quota Indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-zinc-50 rounded-lg border border-zinc-200 text-xs font-mono">
            <span className="text-zinc-500">Daily Quota:</span>
            <span className="text-orange-700 font-bold">
              {job?.status === "completed" ? "0/1 Available" : "1/1 Available"}
            </span>
          </div>

          {/* Engine Node Status */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg border border-emerald-200 text-[11px] font-mono text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block" />
            <span>Remotion Chromium: Online</span>
          </div>

          {user?.is_admin && (
            <button 
              onClick={() => window.location.href = '/admin'}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-50 border border-sky-200 rounded-lg text-xs font-mono text-sky-700 hover:bg-sky-100 transition-colors font-semibold"
            >
              <Shield size={13} />
              <span>Admin Console</span>
            </button>
          )}

          {/* User Profile */}
          <div className="text-xs text-zinc-500 hidden sm:block border-l border-zinc-200 pl-3 ml-1">
            <span className="text-zinc-400">Director: </span>
            <span className="text-zinc-900 font-bold">{user?.username}</span>
          </div>

          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 transition-colors border border-transparent"
          >
            <LogOut size={14} />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </nav>

      {/* Main Studio Workbench in Bright Theme */}
      <main className="flex-1 p-4 md:p-8 max-w-[1700px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">
        {/* ── Left Rail: Production Desk (5 cols) ──────────────── */}
        <div className="lg:col-span-5 space-y-6">
          {/* Station 1: Source Document */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 space-y-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600">
                  <Upload size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-zinc-900 tracking-tight">1. Source Document</h2>
                  <p className="text-[11px] text-zinc-500">PDF, DOCX, or TXT up to 20MB</p>
                </div>
              </div>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-100 text-zinc-500 border border-zinc-200 font-medium">
                Step 01
              </span>
            </div>

            {/* Drag and Drop Zone */}
            <label className={cn(
              "flex flex-col items-center justify-center min-h-[160px] border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 group p-4",
              file
                ? "border-emerald-300 bg-emerald-50/40"
                : "border-zinc-300 bg-zinc-50/50 hover:bg-orange-50/20 hover:border-orange-300"
            )}>
              <div className="flex flex-col items-center gap-2.5 text-center">
                <div className={cn(
                  "w-11 h-11 rounded-xl flex items-center justify-center transition-all",
                  file ? "bg-emerald-100 text-emerald-700 border border-emerald-200" : "bg-white text-zinc-500 group-hover:text-orange-600 group-hover:bg-orange-50 border border-zinc-200"
                )}>
                  <Upload size={20} className="transition-transform group-hover:-translate-y-0.5" />
                </div>
                
                <div>
                  <p className="text-xs font-semibold text-zinc-800 break-all max-w-[280px]">
                    {file ? file.name : "Drop document here or browse"}
                  </p>
                  <p className="text-[10px] text-zinc-500 font-mono mt-1">
                    {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for ingestion` : "PDF, DOCX, TXT accepted"}
                  </p>
                </div>
              </div>
              <input
                type="file"
                className="hidden"
                accept={ACCEPTED_FILE_TYPES}
                onChange={handleFileChange}
              />
            </label>

            {/* Extract Semantics CTA */}
            <button
              onClick={handleExtract}
              disabled={!file || stage === "extracting"}
              className={cn(
                "w-full py-3 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all flex items-center justify-center gap-2",
                !file || stage === "extracting"
                  ? "bg-zinc-100 text-zinc-400 cursor-not-allowed border border-zinc-200"
                  : "bg-zinc-900 hover:bg-zinc-800 text-white shadow-xs hover:scale-[1.01] active:scale-[0.99]"
              )}
            >
              {stage === "extracting" ? (
                <>
                  <Loader2 size={15} className="animate-spin text-zinc-400" />
                  <span>Parsing Semantic Hierarchy...</span>
                </>
              ) : (
                <>
                  <FileText size={15} />
                  <span>Extract Semantic Script</span>
                </>
              )}
            </button>
          </div>

          {/* Station 2: Studio Director Parameters */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 space-y-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
                  <Settings size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-zinc-900 tracking-tight">2. Director Parameters</h2>
                  <p className="text-[11px] text-zinc-500">Visual style and Remotion target</p>
                </div>
              </div>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-100 text-zinc-500 border border-zinc-200 font-medium">
                Step 02
              </span>
            </div>

            {/* Whiteboard Style Selector */}
            <div className="space-y-2">
              <label className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider block">
                Whiteboard Aesthetic
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "expo", label: "Expo Marker", sub: "Classic Crisp" },
                  { id: "blueprint", label: "Blueprint", sub: "Technical Cyan" },
                  { id: "chalk", label: "Slate Chalk", sub: "Soft Texture" },
                ].map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setSelectedStyle(st.id as "expo" | "blueprint" | "chalk")}
                    className={cn(
                      "p-2.5 rounded-xl border text-left transition-all",
                      selectedStyle === st.id
                        ? "bg-orange-50 border-orange-300 text-zinc-900 shadow-xs"
                        : "bg-zinc-50/50 border-zinc-200 text-zinc-600 hover:bg-zinc-100/50"
                    )}
                  >
                    <p className="text-xs font-bold">{st.label}</p>
                    <p className="text-[10px] text-zinc-500 font-mono mt-0.5">{st.sub}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Render MP4 Toggle */}
            <div className="flex items-center justify-between p-3.5 bg-zinc-50 rounded-xl border border-zinc-200">
              <div className="flex items-center gap-3">
                <FileVideo size={16} className="text-orange-600" />
                <div>
                  <p className="text-xs font-bold text-zinc-900">Full MP4 Video Compilation</p>
                  <p className="text-[10px] text-zinc-500 font-mono">Launch Remotion Headless Chromium</p>
                </div>
              </div>
              <input 
                type="checkbox" 
                checked={renderVideo} 
                onChange={(e) => setRenderVideo(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-300 text-orange-600 focus:ring-orange-500/30 cursor-pointer accent-orange-600"
              />
            </div>

            {/* Orchestrate Video CTA */}
            <button
              onClick={handleGenerate}
              disabled={!extractedText || stage === "generating" || job?.status === "running" || job?.status === "rendering"}
              className={cn(
                "w-full py-3.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all flex items-center justify-center gap-2",
                !extractedText || stage === "generating" || job?.status === "running" || job?.status === "rendering"
                  ? "bg-zinc-100 text-zinc-400 cursor-not-allowed border border-zinc-200"
                  : "bg-orange-600 hover:bg-orange-700 text-white shadow-xs hover:scale-[1.01] active:scale-[0.99]"
              )}
            >
              {stage === "generating" || job?.status === "running" || job?.status === "rendering" ? (
                <>
                  <Loader2 size={16} className="animate-spin text-white" />
                  <span>Directing Whiteboard Scenes...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Direct & Render Whiteboard Video</span>
                </>
              )}
            </button>
          </div>

          {/* Station 3: Extracted Script Inspector */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-6 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText size={15} className="text-zinc-500" />
                <h3 className="text-xs font-bold text-zinc-800 uppercase tracking-wider font-mono">
                  Extracted Semantics
                </h3>
              </div>
              <span className="text-[10px] text-zinc-500 font-mono">
                {extractedText ? `${extractedText.length} chars` : "0 chars"}
              </span>
            </div>

            <div className="h-44 overflow-y-auto text-[11px] font-mono text-zinc-600 leading-relaxed custom-scrollbar whitespace-pre-wrap p-3 rounded-xl bg-zinc-50 border border-zinc-200">
              {extractedText || "// Upload a document above and click 'Extract Semantic Script' to view parsed storyboards here."}
            </div>
          </div>
        </div>

        {/* ── Right Rail: Whiteboard Stage & Monitor (7 cols) ── */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Pipeline Stepper (4 stages) */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-zinc-900 tracking-tight">Production Pipeline Tracker</span>
                {elapsedSeconds > 0 && (
                  <span className="text-[10px] font-mono text-orange-700 flex items-center gap-1 bg-orange-50 px-2 py-0.5 rounded border border-orange-200 font-semibold">
                    <Clock size={11} />
                    {elapsedSeconds}s elapsed
                  </span>
                )}
              </div>
              <div className="text-[10px] font-mono text-zinc-500">
                {job?.status ? `STATUS: ${job.status.toUpperCase()}` : "STANDBY"}
              </div>
            </div>

            {/* Stepper Dots & Bars */}
            <div className="grid grid-cols-4 gap-2">
              {[
                { title: "Ingestion", desc: "Normalized Text" },
                { title: "Storyboard", desc: "Gemini 2.5 Director" },
                { title: "Choreography", desc: "SVG Vector Paths" },
                { title: "Render", desc: "Remotion MP4" },
              ].map((st, sIdx) => {
                const isPassed = activeStep > sIdx;
                const isCurrent = activeStep === sIdx;
                return (
                  <div
                    key={sIdx}
                    className={cn(
                      "p-3 rounded-xl border text-left transition-all",
                      isCurrent
                        ? "bg-orange-50 border-orange-300 text-zinc-900 shadow-xs"
                        : isPassed
                        ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                        : "bg-zinc-50 border-zinc-200 text-zinc-500"
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono font-bold">0{sIdx + 1}</span>
                      {isPassed ? (
                        <CheckCircle2 size={13} className="text-emerald-600" />
                      ) : isCurrent ? (
                        <span className="w-2 h-2 rounded-full bg-orange-600 inline-block" />
                      ) : null}
                    </div>
                    <p className="text-xs font-bold truncate">{st.title}</p>
                    <p className="text-[9px] font-mono text-zinc-500 truncate mt-0.5">{st.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Status Feedback Notice */}
            {(statusMsg || isError) && (
              <div className={cn(
                "mt-4 p-3 rounded-xl border text-xs flex items-center gap-2.5 font-mono",
                isError 
                  ? "bg-red-50 border-red-200 text-red-700"
                  : "bg-zinc-50 border-zinc-200 text-zinc-700"
              )}>
                {isError ? <AlertCircle size={15} className="text-red-500 shrink-0" /> : <Sparkles size={15} className="text-orange-600 shrink-0" />}
                <span className="truncate">{statusMsg}</span>
              </div>
            )}
          </div>

          {/* 16:9 Director's Whiteboard Video Monitor (Bright Remotion Surface) */}
          <div className="rounded-2xl border border-zinc-200 bg-white flex-1 min-h-[460px] flex flex-col overflow-hidden shadow-xs relative">
            {/* Monitor Header Chrome */}
            <div className="px-5 py-3 border-b border-zinc-200 bg-zinc-50/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Film size={15} className="text-orange-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-800 font-mono">
                  Whiteboard Video Monitor
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 border border-zinc-200 text-zinc-600 font-semibold">
                  1920x1080 • 30 FPS
                </span>
                {job?.video_path && (
                  <a
                    href={resolveVideoUrl(job.video_path)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white flex items-center gap-1.5 shadow-xs transition-all"
                  >
                    <span>Download MP4</span>
                    <ArrowRight size={13} />
                  </a>
                )}
              </div>
            </div>

            {/* Video / Animation Canvas (Matches Remotion #FDFDFD canvas) */}
            <div className="flex-1 bg-[#FDFDFD] relative flex items-center justify-center p-4">
              <div 
                className="absolute inset-0 opacity-40 pointer-events-none"
                style={{
                  backgroundImage: "radial-gradient(#CBD5E1 1px, transparent 1px)",
                  backgroundSize: "32px 32px",
                }}
              />

              {job?.video_path ? (
                /* Completed Video Playback */
                <video 
                  src={resolveVideoUrl(job.video_path)} 
                  controls 
                  className="w-full h-full max-h-[480px] object-contain rounded-xl border border-zinc-200 shadow-md bg-white" 
                />
              ) : job?.status === "running" || job?.status === "rendering" ? (
                /* Live Rendering Feedback */
                <div className="w-full max-w-lg p-6 rounded-2xl bg-white border border-zinc-200 shadow-md space-y-4 text-center">
                  <div className="w-13 h-13 rounded-2xl border border-zinc-200 bg-white p-2.5 flex items-center justify-center mx-auto shadow-xs">
                    <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain animate-pulse" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">Choreographing Whiteboard Scenes</h3>
                    <p className="text-xs text-zinc-500 font-mono mt-1">
                      {job?.status === "rendering" ? "Remotion rendering SVG frames to MP4..." : "Gemini drafting spoken narrative and vector cues..."}
                    </p>
                  </div>
                  {/* Progress Indicator */}
                  <div className="w-full h-1.5 bg-zinc-200 rounded-full overflow-hidden">
                    <div className="h-full bg-orange-600 w-3/4 rounded-full" />
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 pt-2 border-t border-zinc-100">
                    <span>Node: Headless Chromium</span>
                    <span>Elapsed: {elapsedSeconds}s</span>
                  </div>
                </div>
              ) : (
                /* Idle State */
                <div className="flex flex-col items-center gap-3 text-center p-8 max-w-md">
                  <div className="w-16 h-16 rounded-2xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-400 border-dashed">
                    <Film size={26} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-800">Stage Idle • Awaiting Document</p>
                    <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                      Upload your PDF or outline on the left. The director engine will partition it into scenes and render your whiteboard explainer here.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Telemetry & Node Health */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-zinc-200 bg-white flex items-center justify-between shadow-xs">
              <div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block">Job Session ID</span>
                <span className="text-xs font-mono text-zinc-800 font-medium">
                  {job?.job_id ? job.job_id.slice(0, 16) + "..." : "NONE_ACTIVE"}
                </span>
              </div>
              {job?.job_id && (
                <button
                  onClick={copyJobId}
                  className="p-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-700 transition-colors border border-zinc-200"
                  title="Copy Job ID"
                >
                  {copiedJobId ? <Check size={14} className="text-emerald-700" /> : <Copy size={14} />}
                </button>
              )}
            </div>

            <div className="p-4 rounded-xl border border-zinc-200 bg-white flex items-center justify-between shadow-xs">
              <div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider block">Renderer Subprocess</span>
                <span className="text-xs font-mono text-emerald-700 font-bold flex items-center gap-1.5 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block" />
                  Isolated Worker Active
                </span>
              </div>
              <span className="text-[10px] font-mono text-zinc-600 bg-zinc-100 px-2 py-1 rounded border border-zinc-200 font-medium">
                Remotion 4.0
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
