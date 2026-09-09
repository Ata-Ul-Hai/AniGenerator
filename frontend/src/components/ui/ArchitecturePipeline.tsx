import React from "react";
import { FileUp, Cpu, Volume2, Video, ArrowRight, CheckCircle2 } from "lucide-react";

export const ArchitecturePipeline: React.FC = () => {
  const stages = [
    {
      step: "01",
      icon: <FileUp size={18} className="text-blue-600" />,
      title: "Document Ingestion",
      subhead: "PyMuPDF & AST Parser",
      input: "Raw PDF / DOCX / Markdown",
      output: "Normalized Semantic Markdown",
      description: "Extracts body text while discarding layout headers, page margins, and bibliography noise. Partitions key hypotheses into logical chapters.",
    },
    {
      step: "02",
      icon: <Cpu size={18} className="text-purple-600" />,
      title: "Pedagogical Director",
      subhead: "Gemini 2.5 Flash",
      input: "Normalized Document Chunks",
      output: "Storyboard JSON (Scenes & Cues)",
      description: "Structures the narrative arc, generates conversational spoken voiceover text, and plans dynamic spatial vector drawing coordinates.",
    },
    {
      step: "03",
      icon: <Volume2 size={18} className="text-emerald-600" />,
      title: "Speech Synthesis",
      subhead: "Neural TTS & Phoneme Clocks",
      input: "Spoken Script Strings",
      output: "Timestamped Audio MP3s",
      description: "Generates natural audio voiceover and exports syllable-accurate millisecond markers to dictate visual keyframe completion.",
    },
    {
      step: "04",
      icon: <Video size={18} className="text-orange-600" />,
      title: "Remotion Composition",
      subhead: "Headless Chromium + FFmpeg",
      input: "Vector Cues + Neural Audio",
      output: "1080p 30fps H.264 MP4",
      description: "Animates organic SVG stroke trajectories synchronized to narration, rendering broadcast-grade video directly on Cloud Run.",
    },
  ];

  return (
    <section id="pipeline" className="py-24 md:py-32 px-4 sm:px-6 relative border-t border-zinc-200 bg-[#FBFBFD]">
      <div className="max-w-7xl mx-auto space-y-14">
        {/* Section Header */}
        <div className="max-w-3xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-orange-600 inline-block" />
            <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-orange-700">
              Compilation Pipeline
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-zinc-900 leading-tight">
            Deterministic document-to-video execution
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            Every video is compiled through a strict four-stage pipeline designed for repeatability, exact audio synchronization, and zero manual timeline editing.
          </p>
        </div>

        {/* Horizontal Connected Pipeline Flow */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 relative">
          {stages.map((stage, idx) => (
            <div
              key={stage.step}
              className="rounded-2xl border border-zinc-200 bg-white p-6 flex flex-col justify-between shadow-xs hover:border-zinc-300 transition-all relative group"
            >
              <div className="space-y-4">
                {/* Step Top Bar */}
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-zinc-50 border border-zinc-200 flex items-center justify-center shadow-xs">
                      {stage.icon}
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-zinc-400 font-semibold block">STAGE {stage.step}</span>
                      <strong className="text-xs font-bold text-zinc-900">{stage.title}</strong>
                    </div>
                  </div>
                  {idx < stages.length - 1 && (
                    <ArrowRight size={14} className="text-zinc-300 hidden lg:block" />
                  )}
                </div>

                <p className="text-xs text-zinc-600 leading-relaxed min-h-[50px]">
                  {stage.description}
                </p>

                {/* Contract Specs */}
                <div className="space-y-1.5 pt-2 border-t border-zinc-100 font-mono text-[10px]">
                  <div className="flex items-center justify-between text-zinc-500">
                    <span>IN:</span>
                    <span className="text-zinc-800 font-medium truncate max-w-[170px]">{stage.input}</span>
                  </div>
                  <div className="flex items-center justify-between text-zinc-500">
                    <span>OUT:</span>
                    <span className="text-blue-700 font-bold truncate max-w-[170px]">{stage.output}</span>
                  </div>
                </div>
              </div>

              {/* Status Footer */}
              <div className="mt-5 pt-3 border-t border-zinc-100 flex items-center justify-between text-[10px] font-mono text-zinc-500">
                <span className="text-zinc-400">{stage.subhead}</span>
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <CheckCircle2 size={11} /> Verified
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Pipeline Telemetry Strip */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 flex flex-wrap items-center justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <div>
              <p className="text-xs font-bold text-zinc-900">Cloud Run Processing Cluster</p>
              <p className="text-[11px] font-mono text-zinc-500">FastAPI • Python 3.12 • Remotion 4.0 • Headless Chromium • FFmpeg</p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-3 py-1 rounded-lg bg-zinc-50 border border-zinc-200 text-zinc-700">
              Zero GPU Dependency
            </span>
            <span className="px-3 py-1 rounded-lg bg-zinc-50 border border-zinc-200 text-zinc-700">
              Parallel Render Scaling
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
