import React from "react";
import { FileCode, Layers, Activity, Server } from "lucide-react";

export const BentoFeatures: React.FC = () => {
  return (
    <section id="capabilities" className="py-24 md:py-32 px-4 sm:px-6 relative bg-white border-t border-zinc-200">
      <div className="max-w-7xl mx-auto space-y-14">
        {/* Section Header */}
        <div className="max-w-3xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" />
            <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-blue-700">
              Compiler Architecture
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-zinc-900 leading-tight">
            How AniGenerator turns dense documentation into moving visual proof
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            Unlike generic AI video wrappers that splice together stock clips, AniGenerator compiles your source text into a structured Remotion composition with mathematically synchronized stroke animations.
          </p>
        </div>

        {/* Asymmetric Technical Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Card 1: Document Tree Normalization (7 cols) */}
          <div className="md:col-span-7 rounded-2xl border border-zinc-200 bg-[#FBFBFD] p-7 flex flex-col justify-between shadow-xs hover:border-zinc-300 transition-all">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-800 shadow-xs">
                  <FileCode size={20} className="text-blue-600" />
                </div>
                <span className="text-[11px] font-mono text-zinc-500 font-medium">
                  MIME: application/pdf • markdown
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900">
                AST-Aware Semantic Normalization
              </h3>
              <p className="text-zinc-600 text-xs sm:text-sm leading-relaxed">
                Raw technical papers contain two-column layout jumps, equation noise, and footnote clutter that break naive LLM summarizers. AniGenerator parses the document into a clean abstract syntax tree, extracts core hypotheses, and strips non-pedagogical artifacts.
              </p>
            </div>

            {/* Micro-Schema: Normalized Flow */}
            <div className="mt-6 p-4 rounded-xl bg-white border border-zinc-200 font-mono text-xs space-y-2.5 shadow-xs">
              <div className="flex items-center justify-between text-[10px] text-zinc-500 border-b border-zinc-100 pb-2">
                <span>INSPECTOR: DOC_PARSER.RS</span>
                <span className="text-emerald-700 font-bold">2.4MB / 18 Pages Parsed</span>
              </div>
              <div className="space-y-1 text-[11px]">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="line-through">Footnote [14]: Fischer, Lynch, Paterson IEEE 1985</span>
                  <span className="text-[10px] text-zinc-400">STRIPPED</span>
                </div>
                <div className="flex items-center justify-between text-zinc-900 font-medium">
                  <span className="text-blue-600 font-bold">▶ Section 3.1: Heartbeat Invariants</span>
                  <span className="text-[10px] font-bold text-blue-700">EXTRACTED (4 Scenes)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Remotion Vector Physics (5 cols) */}
          <div className="md:col-span-5 rounded-2xl border border-zinc-200 bg-[#FBFBFD] p-7 flex flex-col justify-between shadow-xs hover:border-zinc-300 transition-all">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-800 shadow-xs">
                  <Layers size={20} className="text-orange-600" />
                </div>
                <span className="text-[11px] font-mono text-zinc-500 font-medium">
                  SVG Path Tracing
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900">
                Natural Drawing Velocity Curves
              </h3>
              <p className="text-zinc-600 text-xs sm:text-sm leading-relaxed">
                Rather than static transitions, Remotion calculates dynamic <code className="text-zinc-800 font-mono text-xs bg-zinc-100 px-1 py-0.5 rounded">stroke-dasharray</code> offsets with non-linear easing to replicate the organic deceleration of a dry-erase marker.
              </p>
            </div>

            {/* Kinetic Path Preview */}
            <div className="mt-6 p-4 rounded-xl bg-white border border-zinc-200 space-y-2 shadow-xs">
              <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                <span>EASING: CUBIC_BEZIER(0.25, 0.1, 0.25, 1.0)</span>
                <span className="text-orange-600 font-bold">30 FPS</span>
              </div>
              <div className="h-10 bg-zinc-50 rounded-lg flex items-center justify-center px-3 border border-zinc-100">
                <svg className="w-full h-6" viewBox="0 0 240 24">
                  <path
                    d="M 5 12 Q 60 2, 120 12 T 235 12"
                    stroke="#EA580C"
                    strokeWidth="2.5"
                    fill="none"
                    strokeDasharray="6 3"
                  />
                  <circle cx="235" cy="12" r="3.5" fill="#EA580C" />
                </svg>
              </div>
            </div>
          </div>

          {/* Card 3: Syllable Audio Synchronization (5 cols) */}
          <div className="md:col-span-5 rounded-2xl border border-zinc-200 bg-[#FBFBFD] p-7 flex flex-col justify-between shadow-xs hover:border-zinc-300 transition-all">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-800 shadow-xs">
                  <Activity size={20} className="text-emerald-600" />
                </div>
                <span className="text-[11px] font-mono text-zinc-500 font-medium">
                  ±12ms Alignment
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900">
                Sub-Second Voiceover Timing
              </h3>
              <p className="text-zinc-600 text-xs sm:text-sm leading-relaxed">
                Neural voiceover phoneme durations dictate video render frames. Stroke animations conclude the exact millisecond the corresponding spoken explanation concludes.
              </p>
            </div>

            {/* Audio Waveform Sync Gauge */}
            <div className="mt-6 p-4 rounded-xl bg-white border border-zinc-200 flex items-center justify-between gap-3 font-mono text-xs shadow-xs">
              <div className="flex items-center gap-1 flex-1 h-7">
                {[35, 60, 85, 40, 95, 70, 50, 90, 45, 80, 65, 95, 55, 30, 85, 50, 75].map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-emerald-600/30 rounded-full"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
              <div className="text-right shrink-0">
                <span className="text-emerald-700 font-bold block text-[11px]">TTS_SYNC_LOCK</span>
                <span className="text-[10px] text-zinc-400">Zero Audio Drift</span>
              </div>
            </div>
          </div>

          {/* Card 4: Headless Cloud Run Farm (7 cols) */}
          <div className="md:col-span-7 rounded-2xl border border-zinc-200 bg-[#FBFBFD] p-7 flex flex-col justify-between shadow-xs hover:border-zinc-300 transition-all">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-800 shadow-xs">
                  <Server size={20} className="text-blue-600" />
                </div>
                <span className="text-[11px] font-mono text-zinc-500 font-medium">
                  Headless Chromium + FFmpeg
                </span>
              </div>
              <h3 className="text-xl font-bold text-zinc-900">
                Deterministic Parallel Rendering
              </h3>
              <p className="text-zinc-600 text-xs sm:text-sm leading-relaxed">
                Compositions are bundled into ephemeral containers on Google Cloud Run. Headless Chromium evaluates React DOM keyframes and pipes pixel streams into FFmpeg without GPU reliance, outputting clean 1080p H.264 MP4s.
              </p>
            </div>

            {/* Spec Matrix */}
            <div className="mt-6 grid grid-cols-3 gap-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-400 block">RESOLUTION</span>
                <strong className="text-zinc-900 text-xs font-bold">1920×1080 (16:9)</strong>
              </div>
              <div className="p-3 rounded-xl bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-400 block">CONTAINER</span>
                <strong className="text-zinc-900 text-xs font-bold">MP4 (H.264 / AAC)</strong>
              </div>
              <div className="p-3 rounded-xl bg-white border border-zinc-200 shadow-xs">
                <span className="text-[10px] text-zinc-400 block">ENCODE SPEED</span>
                <strong className="text-blue-700 text-xs font-bold">~1.2x Realtime</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
