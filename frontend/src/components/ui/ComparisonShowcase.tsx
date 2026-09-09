import React from "react";
import { FileText, Film, Check, X, Sparkles, Brain } from "lucide-react";

export const ComparisonShowcase: React.FC = () => {
  return (
    <section id="comparison" className="py-24 md:py-32 px-4 sm:px-6 relative border-t border-zinc-200 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase tracking-wider text-sky-700 bg-sky-50 border border-sky-200">
            <Sparkles size={13} />
            The Retention Gap
          </span>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight text-zinc-900">
            Why Whiteboard Explainer Videos?
          </h2>
          <p className="text-zinc-600 text-sm md:text-base leading-relaxed">
            Human minds are wired for visual progression. When concepts are drawn out step-by-step alongside spoken narration, comprehension jumps by over 3x compared to static text.
          </p>
        </div>

        {/* Side-by-Side Comparison Container */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Left: The Raw Document */}
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6 sm:p-8 flex flex-col justify-between">
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-zinc-200/80 flex items-center justify-center text-zinc-700">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">Raw Technical Document</h3>
                    <p className="text-xs text-zinc-500 font-mono">28-Page PDF Manuscript</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded bg-red-50 text-red-700 border border-red-200 font-bold">
                  Static Format
                </span>
              </div>

              {/* Mock dense text preview */}
              <div className="p-4 rounded-xl bg-white border border-zinc-200 text-[11px] font-mono text-zinc-600 space-y-2 select-none shadow-xs">
                <p className="font-bold text-zinc-800">1. INTRODUCTION AND BACKGROUND MATRICES</p>
                <p className="leading-relaxed">
                  In formalizing state transitions within non-deterministic distributed consensus topologies, conventional quorum replication suffers from acute vulnerability during network partitioning events wherein heartbeat telemetry exhibits high jitter...
                </p>
                <p className="leading-relaxed">
                  As established by Fischer, Lynch, and Paterson (1985), no asynchronous algorithm can guarantee consensus with even a single unannounced fail-stop failure without augmenting synchronous bounds...
                </p>
              </div>

              {/* Disadvantages list */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-red-500 shrink-0" />
                  <span>Average 35–45 minutes required to comprehend core thesis</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-red-500 shrink-0" />
                  <span>High cognitive load; difficult for cross-functional stakeholders</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-600">
                  <X size={15} className="text-red-500 shrink-0" />
                  <span>Only ~18% retention after 48 hours</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-zinc-200 flex items-center justify-between text-xs text-zinc-500 font-mono">
              <span>Status: Low Engagement</span>
              <span>Fatigue Rate: High</span>
            </div>
          </div>

          {/* Right: The AniGenerator Whiteboard Video */}
          <div className="rounded-2xl border border-orange-200 bg-orange-50/30 p-6 sm:p-8 flex flex-col justify-between shadow-xs">
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-orange-200 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-orange-100 border border-orange-200 flex items-center justify-center text-orange-700">
                    <Film size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-900">AniGenerator Whiteboard Story</h3>
                    <p className="text-xs text-orange-700 font-mono font-medium">85-Second Choreographed Video</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded bg-orange-100 text-orange-800 border border-orange-200 font-bold">
                  Drawn Out
                </span>
              </div>

              {/* Visual preview frame */}
              <div className="p-4 rounded-xl bg-white border border-orange-200 space-y-3 shadow-xs">
                <div className="flex items-center justify-between text-[10px] font-mono text-orange-800 font-bold">
                  <span>SCENE 01: THE CONSENSUS DILEMMA</span>
                  <span className="flex items-center gap-1 text-emerald-700 font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 inline-block" />
                    LIVE DRAW
                  </span>
                </div>
                <div className="h-28 rounded-lg bg-[#FDFDFD] border border-zinc-200 flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-dot-grid opacity-40" />
                  <svg className="w-4/5 h-20 relative z-10" viewBox="0 0 300 70">
                    <circle cx="50" cy="35" r="16" fill="#FFF7ED" stroke="#EA580C" strokeWidth="2" />
                    <text x="44" y="39" fill="#EA580C" fontSize="11" fontWeight="bold" fontFamily="monospace">N1</text>
                    <path d="M 68 35 L 140 35" stroke="#0284C7" strokeWidth="2" strokeDasharray="4 2" />
                    <circle cx="150" cy="35" r="16" fill="#F0F9FF" stroke="#0284C7" strokeWidth="2" />
                    <text x="144" y="39" fill="#0284C7" fontSize="11" fontWeight="bold" fontFamily="monospace">N2</text>
                    <path d="M 168 35 L 240 35" stroke="#16A34A" strokeWidth="2" />
                    <circle cx="250" cy="35" r="16" fill="#F0FDF4" stroke="#16A34A" strokeWidth="2" />
                    <text x="244" y="39" fill="#16A34A" fontSize="11" fontWeight="bold" fontFamily="monospace">N3</text>
                  </svg>
                </div>
                <p className="text-[11px] text-zinc-700 font-mono italic">
                  "Instead of waiting indefinitely, nodes elect a temporary leader using randomized countdown timers."
                </p>
              </div>

              {/* Advantages list */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-orange-600 shrink-0" />
                  <span>Under 90 seconds to grasp complex architectural tradeoffs</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-orange-600 shrink-0" />
                  <span>Dual-channel retention: simultaneous auditory narration & visual drawing</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-700 font-medium">
                  <Check size={15} className="text-orange-600 shrink-0" />
                  <span>Over 86% concept retention tested across engineering teams</span>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-orange-200 flex items-center justify-between text-xs text-orange-800 font-mono font-medium">
              <span className="flex items-center gap-1.5">
                <Brain size={14} className="text-orange-600" />
                Dual-Coding Theory Validated
              </span>
              <span className="font-bold text-zinc-900">3.4x Faster Uptake</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
