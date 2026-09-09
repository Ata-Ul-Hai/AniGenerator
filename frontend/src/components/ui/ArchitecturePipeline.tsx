import React from "react";
import { Server, FileCode, CheckCircle } from "lucide-react";

export const ArchitecturePipeline: React.FC = () => {
  const steps = [
    {
      num: "01",
      name: "Document Ingestion",
      tag: "FASTAPI / PYTHON 3.12",
      desc: "Upload PDFs, DOCX, or TXT (up to 20MB). Normalizes text blocks, strips header artifacts, and chunks logical concepts.",
      color: "border-orange-200 text-orange-700 bg-orange-50",
    },
    {
      num: "02",
      name: "LLM Storyboarder",
      tag: "GEMINI 2.5 FLASH",
      desc: "Prompts multi-modal Gemini to partition the document into pedagogical narrative scenes, spoken script, and vector cues.",
      color: "border-sky-200 text-sky-700 bg-sky-50",
    },
    {
      num: "03",
      name: "Audio Synthesizer",
      tag: "NEURAL TTS & TIMECODES",
      desc: "Asynchronously generates neural voiceover audio files and maps exact millisecond syllable durations for keyframe alignment.",
      color: "border-amber-200 text-amber-700 bg-amber-50",
    },
    {
      num: "04",
      name: "Remotion Video Engine",
      tag: "HEADLESS CHROMIUM & FFMPEG",
      desc: "Renders dynamically animated SVG stroke paths synced to voiceover, encoding broadcast-grade 1080p MP4 artifacts.",
      color: "border-emerald-200 text-emerald-700 bg-emerald-50",
    },
  ];

  return (
    <section id="pipeline" className="py-24 md:py-32 px-4 sm:px-6 relative border-t border-zinc-200 bg-zinc-50/50">
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200">
            <Server size={13} />
            Cloud Run Architecture
          </span>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-zinc-900">
            The Remotion & Gemini Pipeline
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            A fully decoupled, asynchronous video generation pipeline engineered for deterministic execution and scale.
          </p>
        </div>

        {/* 4-Step Pipeline Flow */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step) => (
            <div
              key={step.num}
              className="rounded-2xl border border-zinc-200 bg-white p-6 flex flex-col justify-between relative group hover:border-zinc-300 transition-all shadow-xs"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-2xl font-black font-mono text-zinc-300 group-hover:text-zinc-900 transition-colors">
                    {step.num}
                  </span>
                  <span className={`text-[9px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded border ${step.color}`}>
                    {step.tag}
                  </span>
                </div>
                <h3 className="text-base font-bold text-zinc-900 mb-2">{step.name}</h3>
                <p className="text-xs text-zinc-600 leading-relaxed">{step.desc}</p>
              </div>

              <div className="mt-6 pt-4 border-t border-zinc-100 flex items-center justify-between text-[11px] font-mono text-zinc-500">
                <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                  <CheckCircle size={12} /> Ready
                </span>
                <span>Subprocess Safe</span>
              </div>
            </div>
          ))}
        </div>

        {/* Stack Specs Chip Row */}
        <div className="mt-12 p-5 rounded-2xl border border-zinc-200 bg-white flex flex-wrap items-center justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-700">
              <FileCode size={16} />
            </div>
            <div>
              <p className="text-xs font-bold text-zinc-900">Full Stack Specifications</p>
              <p className="text-[10px] text-zinc-500 font-mono">React 19 • Vite • FastAPI • Alembic • Remotion • FFmpeg</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-600">
            <span className="px-2.5 py-1 rounded-md bg-zinc-50 border border-zinc-200">1080p H.264</span>
            <span className="px-2.5 py-1 rounded-md bg-zinc-50 border border-zinc-200">Sub-10s TTFB</span>
            <span className="px-2.5 py-1 rounded-md bg-zinc-50 border border-zinc-200">Cloud SQL</span>
          </div>
        </div>
      </div>
    </section>
  );
};
