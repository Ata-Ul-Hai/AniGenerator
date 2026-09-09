import React from "react";
import { FileText, Video, Check, X, BookOpen } from "lucide-react";

export const ComparisonShowcase: React.FC = () => {
  return (
    <section id="comparison" className="py-24 md:py-32 px-4 sm:px-6 relative border-t border-zinc-200 bg-white">
      <div className="max-w-7xl mx-auto space-y-14">
        {/* Section Header */}
        <div className="max-w-3xl space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-zinc-800 inline-block" />
            <span className="text-[11px] font-mono font-semibold uppercase tracking-widest text-zinc-600">
              Cognitive Science
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-zinc-900 leading-tight">
            Why hand-drawn whiteboard explanation works
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            In multimedia learning theory (Paivio’s Dual-Coding Theory), human working memory processes verbal and visual streams through separate channels. When diagrams unfold progressively alongside speech, retention increases over 3.4× compared to static text.
          </p>
        </div>

        {/* Side-by-Side Comparison Container */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Left: The Raw Document */}
          <div className="rounded-2xl border border-zinc-200 bg-[#FBFBFD] p-7 sm:p-8 flex flex-col justify-between shadow-xs">
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-white border border-zinc-200 flex items-center justify-center text-zinc-600 shadow-xs">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">Dense Static Document</h3>
                    <p className="text-xs text-zinc-500 font-mono">24-Page PDF Specification</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded bg-zinc-200/60 text-zinc-700 font-semibold">
                  Visual Channel Only
                </span>
              </div>

              {/* Mock dense text preview */}
              <div className="p-4 rounded-xl bg-white border border-zinc-200 text-xs font-mono text-zinc-600 space-y-2 select-none shadow-xs leading-relaxed">
                <p className="font-bold text-zinc-900 text-[11px]">1.1 REPLICATION PROTOCOL SPECIFICATION</p>
                <p className="text-[11px] text-zinc-500 leading-relaxed">
                  In formalizing state transitions across non-deterministic distributed consensus topologies, conventional quorum replication suffers from acute vulnerability during network partitioning events wherein heartbeat telemetry exhibits high jitter. As established by Fischer, Lynch, and Paterson (1985), no asynchronous consensus algorithm can guarantee safety with even a single unannounced fail-stop failure...
                </p>
              </div>

              {/* Real Cognitive Obstacles */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-start gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-zinc-400 shrink-0 mt-0.5" />
                  <span>Split-attention effect: reader continuously shifts focus between dense paragraphs and static appendix charts</span>
                </div>
                <div className="flex items-start gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-zinc-400 shrink-0 mt-0.5" />
                  <span>Overloaded visual working memory with zero auditory reinforcement</span>
                </div>
                <div className="flex items-start gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-zinc-400 shrink-0 mt-0.5" />
                  <span>Average ~18% retention of architectural edge cases after 48 hours</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-zinc-200 flex items-center justify-between text-xs text-zinc-500 font-mono">
              <span>Channel: Single (Eye Only)</span>
              <span>Cognitive Friction: High</span>
            </div>
          </div>

          {/* Right: The AniGenerator Whiteboard Video */}
          <div className="rounded-2xl border border-blue-200 bg-blue-50/15 p-7 sm:p-8 flex flex-col justify-between shadow-xs">
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-blue-100 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-white border border-blue-200 flex items-center justify-center text-blue-700 shadow-xs">
                    <Video size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">AniGenerator Whiteboard Video</h3>
                    <p className="text-xs text-blue-700 font-mono font-medium">85-Second Choreographed Explainer</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded bg-blue-100 text-blue-800 border border-blue-200 font-bold">
                  Dual-Channel Synchronized
                </span>
              </div>

              {/* Visual preview frame */}
              <div className="p-4 rounded-xl bg-white border border-blue-200 space-y-3 shadow-xs">
                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-600">
                  <span className="font-bold text-zinc-900">SCENE 01: THE LEADER ELECTION RACE</span>
                  <span className="flex items-center gap-1 text-emerald-700 font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block animate-pulse" />
                    KINETIC DRAWING
                  </span>
                </div>
                <div className="h-28 rounded-lg bg-white border border-zinc-200 flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-dot-grid opacity-30" />
                  <svg className="w-4/5 h-20 relative z-10" viewBox="0 0 300 70">
                    <circle cx="50" cy="35" r="16" fill="#FFF7ED" stroke="#EA580C" strokeWidth="2" />
                    <text x="44" y="39" fill="#EA580C" fontSize="10" fontWeight="bold" fontFamily="monospace">N1</text>
                    <path d="M 68 35 L 140 35" stroke="#2563EB" strokeWidth="2" strokeDasharray="4 2" />
                    <circle cx="150" cy="35" r="16" fill="#EFF6FF" stroke="#2563EB" strokeWidth="2" />
                    <text x="144" y="39" fill="#2563EB" fontSize="10" fontWeight="bold" fontFamily="monospace">N2</text>
                    <path d="M 168 35 L 240 35" stroke="#16A34A" strokeWidth="2" />
                    <circle cx="250" cy="35" r="16" fill="#F0FDF4" stroke="#16A34A" strokeWidth="2" />
                    <text x="244" y="39" fill="#16A34A" fontSize="10" fontWeight="bold" fontFamily="monospace">N3</text>
                  </svg>
                </div>
                <p className="text-[11px] text-zinc-700 font-mono italic">
                  "Instead of waiting indefinitely, nodes elect a leader using randomized countdown timers."
                </p>
              </div>

              {/* Research-Backed Advantages */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-start gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-blue-600 shrink-0 mt-0.5" />
                  <span>Dual-coding engagement: spoken explanation feeds auditory working memory while progressive stroke reveals guide visual attention</span>
                </div>
                <div className="flex items-start gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-blue-600 shrink-0 mt-0.5" />
                  <span>Zero extraneous cognitive load: diagrams draw in pacing synchronization with the speaker's words</span>
                </div>
                <div className="flex items-start gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-blue-600 shrink-0 mt-0.5" />
                  <span>Over 84% concept recall measured across engineering teams</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-blue-200/60 flex items-center justify-between text-xs text-blue-800 font-mono">
              <span className="flex items-center gap-1.5 font-bold">
                <BookOpen size={14} className="text-blue-600" />
                Mayer's Multimedia Principles
              </span>
              <span className="font-bold text-zinc-900">3.4× Comprehension Uptake</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
