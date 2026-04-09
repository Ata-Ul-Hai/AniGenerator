import React, { useState, useRef, useEffect } from "react";
import { cn } from "../lib/utils";
import { 
  Upload, Zap, LogOut, Loader2, FileVideo, 
  FileText, Settings, BarChart3, RefreshCw, AlertCircle, ArrowRight
} from "lucide-react";
import { GlassPanel } from "./common/GlassPanel";

interface Props {
  token: string;
  onLogout: () => void;
}

type JobStatus = "queued" | "running" | "completed" | "failed";

interface JobState {
  job_id: string;
  status: JobStatus;
  error?: string;
  video_path?: string;
}

const Dashboard: React.FC<Props> = ({ token, onLogout }) => {
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [maxScenes, setMaxScenes] = useState(15);
  const [renderVideo, setRenderVideo] = useState(true);
  const [job, setJob] = useState<JobState | null>(null);
  const [stage, setStage] = useState<"idle" | "extracting" | "extracted" | "generating">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [isError, setIsError] = useState(false);
  const pollRef = useRef<any>(null);

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const headers = { Authorization: `Bearer ${token}` };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const pollJob = (jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`, { headers });
        if (!res.ok) throw new Error("Status poll failed");
        const data = await res.json();
        setJob(data);
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(pollRef.current);
          setStage("idle");
          setIsError(data.status === "failed");
          setStatusMsg(data.status === "completed" ? "Generation successful" : `Engine Error: ${data.error || "Unknown error"}`);
        }
      } catch (err: any) {
        clearInterval(pollRef.current);
        setIsError(true);
        setStatusMsg(`Network Error: ${err.message}`);
      }
    }, 3000);
  };

  const handleExtract = async () => {
    if (!file) return;
    setStage("extracting");
    setIsError(false);
    setStatusMsg("Analyzing document structure...");
    
    const form = new FormData();
    form.append("file", file);
    
    try {
      const res = await fetch(`${API_BASE_URL}/upload`, { method: "POST", headers, body: form });
      const data = await res.json();
      
      if (!res.ok) {
        setIsError(true);
        setStatusMsg(`Extraction Failed: ${data.detail || JSON.stringify(data)}`);
        setStage("idle");
        return;
      }

      setExtractedText(data.extracted_text || "");
      setStage("extracted");
      setStatusMsg(`Successfully extracted ${data.chunk_count ?? 0} semantic units.`);
    } catch (err: any) {
      setIsError(true);
      setStatusMsg(`Connection Error: ${err.message}`);
      setStage("idle");
    }
  };

  const handleGenerate = async () => {
    if (!extractedText) return;
    setStage("generating");
    setIsError(false);
    setStatusMsg("Composing scenes with Gemini...");
    
    try {
      const res = await fetch(`${API_BASE_URL}/generate/async`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ extracted_text: extractedText, max_scenes: maxScenes, render_video: renderVideo }),
      });
      const data = await res.json();

      if (!res.ok) {
        setIsError(true);
        setStatusMsg(`Orchestration Failed: ${data.detail || JSON.stringify(data)}`);
        setStage("idle");
        return;
      }

      setJob(data);
      pollJob(data.job_id);
    } catch (err: any) {
      setIsError(true);
      setStatusMsg(`Composition Error: ${err.message}`);
      setStage("idle");
    }
  };

  return (
    <div className="min-h-screen bg-background text-zinc-100 flex flex-col font-sans">
      <nav className="h-16 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-accent-blue/20 rounded-lg flex items-center justify-center border border-accent-blue/30">
            <Zap size={16} className="text-accent-blue" />
          </div>
          <h1 className="text-sm font-bold tracking-tight">AniGenerator <span className="text-zinc-600 font-normal ml-2">Control Room</span></h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/10 text-[10px] uppercase tracking-wider text-zinc-500 font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Active Mode: Local/Docker
          </div>
          <button onClick={onLogout} className="flex items-center gap-2 text-xs text-zinc-500 hover:text-white transition-colors">
            <LogOut size={14} />
            Sign Out
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 md:p-10 max-w-[1600px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-8">
          <GlassPanel className="p-8 space-y-6 bg-surface/30">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent-blue/10 rounded-lg border border-accent-blue/20">
                  <Upload size={18} className="text-accent-blue" />
                </div>
                <h2 className="text-lg font-bold tracking-tight">1. Source</h2>
              </div>

              <label className={cn(
                "flex flex-col items-center justify-center h-48 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300 group",
                file ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/5 bg-background hover:bg-white/[0.02] hover:border-white/10 shadow-inner"
              )}>
                <div className="flex flex-col items-center gap-3">
                  <Upload size={24} className={cn("transition-transform group-hover:-translate-y-1", file ? "text-emerald-500" : "text-zinc-700")} />
                  <div className="text-center px-4">
                    <p className="text-sm font-medium text-zinc-400 break-all">{file ? file.name : "Choose document"}</p>
                    <p className="text-[10px] text-zinc-700 mt-1 uppercase tracking-widest font-bold">PDF, DOCX, TXT</p>
                  </div>
                </div>
                <input type="file" className="hidden" onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setFile(e.target.files[0]);
                    setExtractedText("");
                    setJob(null);
                    setStatusMsg("");
                    setIsError(false);
                    setStage("idle");
                  }
                }} />
              </label>

              <button
                onClick={handleExtract}
                disabled={!file || stage === "extracting"}
                className={cn(
                  "w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all",
                  !file || stage === "extracting" ? "bg-zinc-900 text-zinc-700 cursor-not-allowed border border-white/5" : "bg-white text-background hover:bg-zinc-100 shadow-premium-sm"
                )}
              >
                {stage === "extracting" ? "Analyzing..." : "Extract Semantics"}
              </button>
            </div>

            <div className="space-y-4 pt-6 border-t border-white/5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent-purple/10 rounded-lg border border-accent-purple/20">
                  <Settings size={18} className="text-accent-purple" />
                </div>
                <h2 className="text-lg font-bold tracking-tight">2. Parameters</h2>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <label className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Max Scenes</label>
                    <span className="text-[10px] font-mono text-accent-purple font-bold">{maxScenes}</span>
                  </div>
                  <input 
                    type="range" min="1" max="24" step="1" 
                    value={maxScenes} onChange={(e) => setMaxScenes(+e.target.value)}
                    className="w-full h-1 bg-zinc-900 rounded-lg appearance-none accent-accent-purple"
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-background/50 rounded-xl border border-white/5 shadow-inner">
                  <div className="flex items-center gap-3">
                    <FileVideo size={14} className="text-zinc-600" />
                    <span className="text-xs font-medium text-zinc-500">Render MP4 Artifact</span>
                  </div>
                  <input 
                    type="checkbox" checked={renderVideo} onChange={(e) => setRenderVideo(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-800 bg-zinc-950 text-accent-purple focus:ring-accent-purple/50"
                  />
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={!extractedText || stage === "generating" || job?.status === "running"}
                className={cn(
                  "w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all group",
                  !extractedText || stage === "generating" || job?.status === "running"
                    ? "bg-zinc-900 text-zinc-700 cursor-not-allowed border border-white/5"
                    : "bg-accent-purple text-white hover:bg-accent-purple/90 shadow-glow-purple"
                )}
              >
                <div className="flex items-center justify-center gap-2">
                  {stage === "generating" || job?.status === "running" ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} className="group-hover:animate-pulse" />}
                  Orchestrate Video
                </div>
              </button>
            </div>
          </GlassPanel>
        </div>

        <div className="lg:col-span-8 flex flex-col gap-8">
          <GlassPanel className={cn(
            "p-6 flex items-center justify-between transition-colors duration-500",
            isError ? "border-red-500/20 bg-red-500/[0.02]" : "border-accent-blue/10 bg-accent-blue/[0.02]"
          )}>
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center border transition-all",
                isError ? "bg-red-500/10 border-red-500/20" : 
                job?.status === "running" ? "bg-accent-blue/10 border-accent-blue/20 animate-pulse shadow-glow-blue" : "bg-white/5 border-white/10"
              )}>
                {isError ? <AlertCircle size={20} className="text-red-500" /> : 
                 job?.status === "running" ? <RefreshCw size={20} className="text-accent-blue animate-spin" /> : 
                 <BarChart3 size={20} className="text-zinc-600" />}
              </div>
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Pipeline Observer</p>
                <p className={cn("text-xs font-bold transition-all", isError ? "text-red-400" : "text-white")}>
                  {statusMsg || "Standby - Waiting for document ingestion"}
                </p>
              </div>
            </div>
            {job?.status === "running" && (
                <div className="text-[10px] font-mono text-accent-blue/70 animate-pulse">POLLING_ACTIVE_...</div>
            )}
          </GlassPanel>

          <GlassPanel className="flex-1 min-h-[500px] flex flex-col overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.01] to-transparent pointer-events-none" />
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-zinc-950/20">
              <div className="flex items-center gap-3">
                <FileVideo size={16} className="text-zinc-600" />
                <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-400">Whiteboard Preview</h2>
              </div>
              {job?.video_path && (
                <a 
                  href={job.video_path.startsWith('http') ? job.video_path : `${API_BASE_URL}/${job.video_path.replace(/^\//, '')}`}
                  target="_blank" rel="noreferrer"
                  className="text-[10px] font-bold uppercase tracking-widest text-accent-blue hover:text-white transition-colors flex items-center gap-1.5"
                >
                  Download Artifact <ArrowRight size={10} />
                </a>
              )}
            </div>
            
            <div className="flex-1 bg-[#050505] relative flex items-center justify-center">
              {job?.video_path ? (
                <video src={job.video_path.startsWith('http') ? job.video_path : `${API_BASE_URL}/${job.video_path.replace(/^\//, '')}`} controls className="w-full h-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/5 flex items-center justify-center border-dashed">
                    <FileVideo size={24} className="text-zinc-800" />
                  </div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-700">Waiting for Render Engine</p>
                </div>
              )}
            </div>
          </GlassPanel>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <GlassPanel className="p-6 space-y-4 bg-surface/20">
              <div className="flex items-center gap-3">
                <FileText size={16} className="text-zinc-700" />
                <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Extracted Semantics</h3>
              </div>
              <div className="h-40 overflow-y-auto text-[11px] font-mono text-zinc-500 leading-relaxed custom-scrollbar whitespace-pre-wrap px-1">
                {extractedText || "// ANALYZE_SOURCE_TO_VIEW_CHUNKS"}
              </div>
            </GlassPanel>
            
            <GlassPanel className="p-6 space-y-4 bg-surface/20 border-white/5">
              <div className="flex items-center gap-3">
                <BarChart3 size={16} className="text-zinc-700" />
                <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Pipeline Health</h3>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-zinc-700 uppercase">Process ID</span>
                  <span className="text-[10px] font-mono text-zinc-500">{job?.job_id?.slice(0, 16) || "EMPTY_ID"}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-zinc-700 uppercase">Scenes Predicted</span>
                  <span className="text-[10px] font-mono text-zinc-500">{job ? maxScenes : "0"}</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-white/5">
                  <span className="text-[10px] font-bold text-zinc-700 uppercase">Node Registry</span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[9px] font-bold uppercase">Healthy</span>
                </div>
              </div>
            </GlassPanel>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
