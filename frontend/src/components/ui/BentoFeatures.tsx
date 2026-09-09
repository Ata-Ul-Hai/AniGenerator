import React from "react";
import { FileSearch, Wand2, PenTool, Mic2, Check, Sparkles } from "lucide-react";

export const BentoFeatures: React.FC = () => {
  return (
    <section id="capabilities" className="py-24 md:py-32 px-4 sm:px-6 relative bg-zinc-50/60 border-t border-zinc-200">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-wider text-orange-700 bg-orange-50 border border-orange-200">
            <Sparkles size={13} />
            Studio Core Capabilities
          </span>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-zinc-900">
            Engineered for <span className="text-orange-600">clarity</span>, not just decoration.
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            Most video tools simply splice together generic stock clips. AniGenerator builds a custom whiteboard animation from scratch, choreographing stroke vectors to match your document's thesis.
          </p>
        </div>

        {/* Bento Grid Layout in Bright Theme */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Card 1: Semantic Document Parsing (7 cols) */}
          <div className="md:col-span-7 rounded-2xl border border-zinc-200 bg-white p-7 flex flex-col justify-between group hover:border-zinc-300 transition-all shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600">
                  <FileSearch size={20} />
                </div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest px-2.5 py-1 rounded bg-zinc-100 border border-zinc-200 font-semibold">
                  Stage 01 • Parsing
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Hierarchical Document Ingestion
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-6">
                Directly parses complex PDFs, technical specifications, and academic manuscripts up to 20MB. Strips out bibliography noise and extracts semantic milestones.
              </p>
            </div>

            {/* Visual Micro-Card: Diff of Raw vs Parsed */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 border-b border-zinc-200 pb-2">
                <span>INGESTION_PIPELINE.PY</span>
                <span className="text-emerald-700 font-bold flex items-center gap-1">
                  <Check size={12} /> Normalized
                </span>
              </div>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex gap-2 text-zinc-400">
                  <span className="line-through">§ 12.4 References, footnotes, header metadata</span>
                </div>
                <div className="flex gap-2 text-zinc-800 font-medium">
                  <span className="text-orange-600 font-bold">→</span>
                  <span>Core Hypothesis: Distributed consensus requires 2F+1 quorum</span>
                </div>
                <div className="flex gap-2 text-zinc-800 font-medium">
                  <span className="text-orange-600 font-bold">→</span>
                  <span>Visual Metaphor: Voting ring with heartbeat signals</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Gemini 2.5 Flash as Director (5 cols) */}
          <div className="md:col-span-5 rounded-2xl border border-zinc-200 bg-white p-7 flex flex-col justify-between group hover:border-zinc-300 transition-all shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600">
                  <Wand2 size={20} />
                </div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest px-2.5 py-1 rounded bg-zinc-100 border border-zinc-200 font-semibold">
                  Stage 02 • Directing
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Multi-Modal Scene Storyboarding
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-6">
                Gemini 2.5 Flash acts as pedagogical director. It generates both natural spoken voiceover scripts and choreographed spatial diagrams.
              </p>
            </div>

            {/* Visual Micro-Card: Scene Beat Card */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-[10px] text-sky-700 font-semibold">
                <span>STORYBOARD_DIRECTOR.JSON</span>
                <span>SCENE 01 / 04</span>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-zinc-200 text-[10px] text-zinc-700">
                <code>{`{"timing": "00:15s", "actor": "LeaderNode", "action": "draw_circle", "label": "Quorum Leader"}`}</code>
              </div>
            </div>
          </div>

          {/* Card 3: Remotion Dynamic Stroke Choreography (5 cols) */}
          <div className="md:col-span-5 rounded-2xl border border-zinc-200 bg-white p-7 flex flex-col justify-between group hover:border-zinc-300 transition-all shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
                  <PenTool size={20} />
                </div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest px-2.5 py-1 rounded bg-zinc-100 border border-zinc-200 font-semibold">
                  Stage 03 • Vectors
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Dynamic SVG Stroke Physics
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-6">
                Powered by Remotion in headless Chromium. Computes realistic stroke-dasharray animations with natural hand-drawing velocity curves.
              </p>
            </div>

            {/* Visual Micro-Card: Vector Path Preview */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-amber-700 font-semibold">
                <span>STROKE_DASHARRAY</span>
                <span>VELOCITY: EASE_OUT</span>
              </div>
              <div className="h-12 bg-white rounded-lg flex items-center justify-center p-2 border border-zinc-200">
                <svg className="w-full h-8" viewBox="0 0 200 40">
                  <path
                    d="M 10 20 Q 50 5, 100 20 T 190 20"
                    stroke="#EA580C"
                    strokeWidth="2.5"
                    fill="none"
                    strokeDasharray="4 2"
                  />
                  <circle cx="190" cy="20" r="4" fill="#EA580C" />
                </svg>
              </div>
            </div>
          </div>

          {/* Card 4: Frame-Matched Neural Audio (7 cols) */}
          <div className="md:col-span-7 rounded-2xl border border-zinc-200 bg-white p-7 flex flex-col justify-between group hover:border-zinc-300 transition-all shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
                  <Mic2 size={20} />
                </div>
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest px-2.5 py-1 rounded bg-zinc-100 border border-zinc-200 font-semibold">
                  Stage 04 • Audio Sync
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Sub-Second Voiceover Synchronization
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-6">
                Neural TTS voiceover timing dictates video render keyframes. Pen drawings conclude the exact millisecond narration concludes each idea.
              </p>
            </div>

            {/* Visual Micro-Card: Waveform & Timecode */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 flex items-center justify-between gap-4 font-mono text-xs">
              <div className="flex items-center gap-1 flex-1 h-8">
                {[40, 70, 90, 30, 85, 60, 45, 95, 35, 75, 50, 80, 65, 30, 90, 40, 85, 60].map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-emerald-600/30 rounded-full"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
              <div className="text-right shrink-0">
                <span className="text-emerald-700 font-bold block text-[11px]">SYNC_ACCURACY: &plusmn;12ms</span>
                <span className="text-[10px] text-zinc-500">Bitrate: 320kbps MP3</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
