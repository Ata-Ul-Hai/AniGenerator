import React, { useState } from "react";
import { FileText, Cpu, Film, Sparkles, Check } from "lucide-react";

interface Scenario {
  id: string;
  category: string;
  title: string;
  docName: string;
  docExcerpt: string;
  docHighlight: string;
  timecode: string;
  spokenScript: string;
  directorCues: string[];
  renderStats: {
    frames: number;
    fps: number;
    audioDuration: string;
    complexity: string;
  };
  renderGraphic: React.ReactNode;
}

export const CompilerWorkbench: React.FC = () => {
  const scenarios: Scenario[] = [
    {
      id: "raft",
      category: "Distributed Systems RFC",
      title: "Raft Consensus Protocol",
      docName: "raft-extended-consensus.pdf § 5.2",
      docExcerpt:
        "Raft uses a heartbeat mechanism to trigger leader election. When servers start up, they begin as followers. A server remains in follower state as long as it receives valid RPCs from a leader. Leaders send periodic heartbeats (AppendEntries RPCs with no entries) to followers to maintain authority. If a follower receives no communication over an election timeout, it assumes there is no viable leader and initiates an election.",
      docHighlight:
        "If a follower receives no communication over an election timeout, it assumes there is no viable leader and initiates an election to choose a new leader.",
      timecode: "00:00 - 00:19",
      spokenScript:
        "\"In distributed clusters, silence breeds uncertainty. When followers stop receiving leader heartbeats, an election timer expires. The node steps forward as a candidate, increments the current term, and broadcasts vote requests across the network.\"",
      directorCues: [
        "Render 3 cluster nodes: Leader (N1), Follower (N2), Follower (N3)",
        "Animate periodic heartbeat ping: N1 → N2, N3",
        "Trigger election timeout countdown on N2 (turn amber)",
        "Trace dual RequestVote vector arrows from N2 to peers",
      ],
      renderStats: {
        frames: 570,
        fps: 30,
        audioDuration: "19.0s",
        complexity: "Medium (4 Nodes, 6 Directed Arrows)",
      },
      renderGraphic: (
        <svg className="w-full h-full" viewBox="0 0 380 200" fill="none">
          {/* Background drafting dot guides */}
          <circle cx="70" cy="100" r="28" fill="#F8FAFC" stroke="#94A3B8" strokeWidth="2" strokeDasharray="4 2" />
          <text x="70" y="96" textAnchor="middle" fill="#64748B" fontSize="10" fontWeight="bold" fontFamily="monospace">NODE 1</text>
          <text x="70" y="112" textAnchor="middle" fill="#94A3B8" fontSize="8" fontFamily="monospace">Leader (Dead)</text>

          {/* Heartbeat failure symbol */}
          <line x1="58" y1="88" x2="82" y2="112" stroke="#EF4444" strokeWidth="2" />
          <line x1="82" y1="88" x2="58" y2="112" stroke="#EF4444" strokeWidth="2" />

          {/* Candidate Node */}
          <circle cx="210" cy="65" r="32" fill="#FFF7ED" stroke="#EA580C" strokeWidth="2.5" />
          <text x="210" y="60" textAnchor="middle" fill="#EA580C" fontSize="11" fontWeight="bold" fontFamily="monospace">NODE 2</text>
          <text x="210" y="74" textAnchor="middle" fill="#C2410C" fontSize="8" fontWeight="600" fontFamily="monospace">Candidate • T2</text>

          {/* Peer Follower */}
          <circle cx="310" cy="140" r="28" fill="#F0F9FF" stroke="#0284C7" strokeWidth="2" />
          <text x="310" y="136" textAnchor="middle" fill="#0284C7" fontSize="10" fontWeight="bold" fontFamily="monospace">NODE 3</text>
          <text x="310" y="150" textAnchor="middle" fill="#0369A1" fontSize="8" fontFamily="monospace">Follower</text>

          {/* Animated/Drawn Vector Request Arrows */}
          <path d="M 185 85 L 98 95" stroke="#94A3B8" strokeWidth="1.5" strokeDasharray="3 3" markerEnd="url(#arrow-slate)" />
          <path d="M 235 85 L 290 120" stroke="#EA580C" strokeWidth="2.5" markerEnd="url(#arrow-terracotta)" />

          {/* Vector Callout Label */}
          <rect x="235" y="95" width="75" height="18" rx="4" fill="#FFFFFF" stroke="#EA580C" strokeWidth="1" />
          <text x="272" y="107" textAnchor="middle" fill="#C2410C" fontSize="8" fontWeight="bold" fontFamily="monospace">RequestVote</text>

          {/* Quorum status badge */}
          <rect x="20" y="165" width="130" height="22" rx="6" fill="#F0FDF4" stroke="#86EFAC" strokeWidth="1" />
          <text x="85" y="179" textAnchor="middle" fill="#166534" fontSize="9" fontWeight="bold" fontFamily="monospace">✓ Quorum Needed: 2/3</text>

          <defs>
            <marker id="arrow-terracotta" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <polygon points="0 0, 6 3, 0 6" fill="#EA580C" />
            </marker>
            <marker id="arrow-slate" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <polygon points="0 0, 6 3, 0 6" fill="#94A3B8" />
            </marker>
          </defs>
        </svg>
      ),
    },
    {
      id: "transformer",
      category: "Machine Learning Paper",
      title: "Scaled Dot-Product Attention",
      docName: "attention-is-all-you-need.pdf § 3.2",
      docExcerpt:
        "An attention function can be described as mapping a query and a set of key-value pairs to an output. The output is computed as a weighted sum of the values, where the weight assigned to each value is computed by a compatibility function of the query with the corresponding key: Attention(Q, K, V) = softmax(Q · K^T / √d_k) · V.",
      docHighlight:
        "Attention(Q, K, V) = softmax(Q · K^T / √d_k) · V. We compute the dot products of the query with all keys, divide each by √d_k, and apply a softmax function.",
      timecode: "00:00 - 00:22",
      spokenScript:
        "\"Instead of processing words in isolation, self-attention lets each word measure its relationship to every other token. We project the input into Queries, Keys, and Values. The dot product between Query and Key yields an alignment score, scaled to avoid gradient vanishing before weighting the Values.\"",
      directorCues: [
        "Render input sequence tokens: [Token A, Token B, Token C]",
        "Project three parallel linear vectors: Q (Blue), K (Emerald), V (Terracotta)",
        "Draw Matrix Dot-Product Cross: Q · Kᵀ",
        "Normalize through Softmax attention heatmap and scale to V",
      ],
      renderStats: {
        frames: 660,
        fps: 30,
        audioDuration: "22.0s",
        complexity: "High (Matrix Projections & Heatmap)",
      },
      renderGraphic: (
        <svg className="w-full h-full" viewBox="0 0 380 200" fill="none">
          {/* Input embedding tokens */}
          <rect x="25" y="30" width="60" height="24" rx="5" fill="#F8FAFC" stroke="#94A3B8" strokeWidth="1.5" />
          <text x="55" y="45" textAnchor="middle" fill="#334155" fontSize="9" fontWeight="bold" fontFamily="monospace">"Attention"</text>

          {/* Projection branches */}
          <path d="M 85 42 L 140 30" stroke="#2563EB" strokeWidth="2" />
          <path d="M 85 42 L 140 75" stroke="#16A34A" strokeWidth="2" />
          <path d="M 85 42 L 140 120" stroke="#EA580C" strokeWidth="2" />

          {/* Q, K, V boxes */}
          <rect x="140" y="20" width="48" height="20" rx="4" fill="#EFF6FF" stroke="#2563EB" strokeWidth="1.5" />
          <text x="164" y="33" textAnchor="middle" fill="#1E40AF" fontSize="9" fontWeight="bold" fontFamily="monospace">Q (Query)</text>

          <rect x="140" y="65" width="48" height="20" rx="4" fill="#F0FDF4" stroke="#16A34A" strokeWidth="1.5" />
          <text x="164" y="78" textAnchor="middle" fill="#166534" fontSize="9" fontWeight="bold" fontFamily="monospace">K (Key)</text>

          <rect x="140" y="110" width="48" height="20" rx="4" fill="#FFF7ED" stroke="#EA580C" strokeWidth="1.5" />
          <text x="164" y="123" textAnchor="middle" fill="#9A3412" fontSize="9" fontWeight="bold" fontFamily="monospace">V (Value)</text>

          {/* Dot product calculation */}
          <path d="M 188 30 L 230 50" stroke="#64748B" strokeWidth="1.5" strokeDasharray="3 2" />
          <path d="M 188 75 L 230 50" stroke="#64748B" strokeWidth="1.5" strokeDasharray="3 2" />

          <circle cx="245" cy="50" r="15" fill="#FFFFFF" stroke="#0F172A" strokeWidth="1.5" />
          <text x="245" y="53" textAnchor="middle" fill="#0F172A" fontSize="8" fontWeight="bold" fontFamily="monospace">Q·Kᵀ</text>

          {/* Softmax scaling */}
          <path d="M 260 50 L 290 50" stroke="#0F172A" strokeWidth="1.5" />
          <rect x="290" y="40" width="65" height="22" rx="4" fill="#F1F5F9" stroke="#64748B" strokeWidth="1" />
          <text x="322" y="54" textAnchor="middle" fill="#1E293B" fontSize="8" fontWeight="bold" fontFamily="monospace">Softmax / √d</text>

          {/* Final attention context output */}
          <path d="M 322 62 L 322 110" stroke="#0F172A" strokeWidth="1.5" />
          <path d="M 188 120 L 290 120" stroke="#EA580C" strokeWidth="2" />
          <rect x="290" y="110" width="70" height="26" rx="6" fill="#FAF5FF" stroke="#9333EA" strokeWidth="1.5" />
          <text x="325" y="126" textAnchor="middle" fill="#6B21A8" fontSize="8" fontWeight="bold" fontFamily="monospace">Context Output</text>

          <text x="25" y="180" fill="#64748B" fontSize="9" fontFamily="monospace">Formula: Attention(Q, K, V) = softmax(Q·Kᵀ / √d_k) · V</text>
        </svg>
      ),
    },
    {
      id: "lsm",
      category: "Database Engineering",
      title: "LSM-Tree Storage Compaction",
      docName: "lsm-tree-architecture.md § 2.1",
      docExcerpt:
        "Writes in an LSM-tree are appended sequentially to an on-disk Write-Ahead Log (WAL) and stored in memory in a sorted MemTable (typically a Red-Black Tree or SkipList). When the MemTable reaches memory capacity, it is frozen to an immutable MemTable and flushed to disk as a Sorted String Table (SSTable) at Level 0. Background compaction continuously merges overlapping keys.",
      docHighlight:
        "When the MemTable reaches capacity, it is flushed sequentially to disk as an immutable SSTable, completely eliminating random disk write overhead.",
      timecode: "00:00 - 00:18",
      spokenScript:
        "\"Disk random writes kill throughput, but sequential appends run at mechanical hardware limit. Log-Structured Merge Trees accept mutations into memory. When the MemTable fills, it flushes sequentially to disk as an immutable SSTable, deferring deduplication to background compaction.\"",
      directorCues: [
        "Draw incoming write stream: PUT(user:101, 'active')",
        "Draw Append-Only Write-Ahead Log (WAL on Disk)",
        "Draw In-Memory SkipList (MemTable)",
        "Animate sequential flush arrow to Immutable Level 0 SSTable",
      ],
      renderStats: {
        frames: 540,
        fps: 30,
        audioDuration: "18.0s",
        complexity: "Medium (Memory vs Disk Boundaries)",
      },
      renderGraphic: (
        <svg className="w-full h-full" viewBox="0 0 380 200" fill="none">
          {/* Memory vs Disk Boundary */}
          <line x1="190" y1="20" x2="190" y2="180" stroke="#CBD5E1" strokeWidth="1.5" strokeDasharray="4 4" />
          <text x="100" y="22" textAnchor="middle" fill="#2563EB" fontSize="9" fontWeight="bold" fontFamily="monospace">VOLATILE RAM</text>
          <text x="280" y="22" textAnchor="middle" fill="#475569" fontSize="9" fontWeight="bold" fontFamily="monospace">PERSISTENT DISK (NVMe)</text>

          {/* Inbound Write */}
          <rect x="15" y="50" width="70" height="24" rx="4" fill="#FFFFFF" stroke="#0F172A" strokeWidth="1.5" />
          <text x="50" y="65" textAnchor="middle" fill="#0F172A" fontSize="8" fontWeight="bold" fontFamily="monospace">PUT(k, v)</text>

          {/* WAL Write Arrow */}
          <path d="M 85 62 L 210 62" stroke="#475569" strokeWidth="2" strokeDasharray="3 2" />
          <rect x="210" y="50" width="60" height="24" rx="4" fill="#F1F5F9" stroke="#475569" strokeWidth="1.5" />
          <text x="240" y="65" textAnchor="middle" fill="#1E293B" fontSize="8" fontWeight="bold" fontFamily="monospace">WAL (Log)</text>

          {/* MemTable Write */}
          <path d="M 50 74 L 50 110 L 95 110" stroke="#2563EB" strokeWidth="2" />
          <rect x="95" y="95" width="80" height="42" rx="6" fill="#EFF6FF" stroke="#2563EB" strokeWidth="2" />
          <text x="135" y="112" textAnchor="middle" fill="#1E40AF" fontSize="9" fontWeight="bold" fontFamily="monospace">MemTable</text>
          <text x="135" y="126" textAnchor="middle" fill="#3B82F6" fontSize="7" fontFamily="monospace">SkipList (Sorted)</text>

          {/* Sequential Flush Arrow */}
          <path d="M 175 116 L 225 116" stroke="#EA580C" strokeWidth="2.5" markerEnd="url(#arrow-lsm-flush)" />
          <text x="200" y="108" textAnchor="middle" fill="#C2410C" fontSize="7" fontWeight="bold" fontFamily="monospace">Flush (Seq)</text>

          {/* Disk SSTables */}
          <rect x="230" y="100" width="65" height="32" rx="4" fill="#FFF7ED" stroke="#EA580C" strokeWidth="1.5" />
          <text x="262" y="116" textAnchor="middle" fill="#9A3412" fontSize="8" fontWeight="bold" fontFamily="monospace">SSTable L0</text>
          <text x="262" y="126" textAnchor="middle" fill="#EA580C" fontSize="7" fontFamily="monospace">[k1 ... k99]</text>

          <rect x="305" y="100" width="65" height="32" rx="4" fill="#F8FAFC" stroke="#94A3B8" strokeWidth="1" />
          <text x="337" y="116" textAnchor="middle" fill="#475569" fontSize="8" fontWeight="bold" fontFamily="monospace">SSTable L0</text>
          <text x="337" y="126" textAnchor="middle" fill="#64748B" fontSize="7" fontFamily="monospace">[k100 ... k199]</text>

          <defs>
            <marker id="arrow-lsm-flush" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <polygon points="0 0, 6 3, 0 6" fill="#EA580C" />
            </marker>
          </defs>

          <text x="20" y="175" fill="#64748B" fontSize="9" fontFamily="monospace">Guarantee: Zero random disk seeks on ingestion path</text>
        </svg>
      ),
    },
  ];

  const [activeScenarioId, setActiveScenarioId] = useState<string>("raft");
  const activeScenario = scenarios.find((s) => s.id === activeScenarioId) || scenarios[0];

  return (
    <div id="compiler" className="w-full max-w-7xl mx-auto space-y-6 pt-4">
      {/* Station Header & Scenario Switcher */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-zinc-200">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-600 inline-block animate-pulse" />
            <span className="text-[11px] font-mono uppercase tracking-widest text-blue-700 font-bold">
              Interactive Compiler Workbench
            </span>
          </div>
          <h3 className="text-2xl md:text-3xl font-extrabold text-zinc-900 tracking-tight">
            From technical spec to synchronized whiteboard scene
          </h3>
          <p className="text-xs sm:text-sm text-zinc-600 mt-1 max-w-2xl">
            Inspect the real 3-stage compilation pipeline below. Switch scenarios to see how dense documentation is parsed, scripted, and rendered into vector frames.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 bg-zinc-100 p-1.5 rounded-xl border border-zinc-200">
          {scenarios.map((s) => {
            const isActive = s.id === activeScenario.id;
            return (
              <button
                key={s.id}
                onClick={() => setActiveScenarioId(s.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  isActive
                    ? "bg-white text-zinc-900 shadow-xs border border-zinc-200/80 font-bold"
                    : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/60"
                }`}
              >
                <span>{s.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3-Column Interactive Architectural Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        {/* Column 1: Source Document Slice (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6 flex flex-col justify-between shadow-xs">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700">
                  <FileText size={16} />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">Stage 01 • Ingestion</span>
                  <strong className="text-xs font-bold text-zinc-900">Source Document Slice</strong>
                </div>
              </div>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200 font-semibold">
                RAW SPEC
              </span>
            </div>

            <div className="space-y-2">
              <span className="text-[11px] font-mono text-zinc-500 block font-medium">{activeScenario.docName}</span>
              <div className="p-3.5 rounded-xl bg-zinc-50/80 border border-zinc-200 text-xs font-mono text-zinc-600 leading-relaxed space-y-2">
                <p className="text-zinc-400 text-[11px]">{activeScenario.docExcerpt.replace(activeScenario.docHighlight, "...")}</p>
                <div className="bg-orange-50/90 border-l-2 border-orange-600 pl-2.5 py-1.5 rounded-r text-zinc-800 font-medium">
                  "{activeScenario.docHighlight}"
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-zinc-100 flex items-center justify-between text-[11px] font-mono text-zinc-500">
            <span>AST Normalizer: PyMuPDF</span>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <Check size={12} /> Milestone Extracted
            </span>
          </div>
        </div>

        {/* Column 2: Gemini Pedagogical Director (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-blue-200 bg-blue-50/15 p-5 sm:p-6 flex flex-col justify-between shadow-xs">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-blue-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                  <Cpu size={16} />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-blue-600 uppercase tracking-wider block font-semibold">Stage 02 • Directing</span>
                  <strong className="text-xs font-bold text-zinc-900">Gemini 2.5 Flash Script</strong>
                </div>
              </div>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200 font-bold">
                {activeScenario.timecode}
              </span>
            </div>

            {/* Spoken script card */}
            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-white border border-blue-200/80 shadow-xs">
                <span className="text-[10px] font-mono uppercase tracking-wider text-blue-700 font-bold block mb-1.5">
                  Spoken Neural Voiceover:
                </span>
                <p className="text-xs text-zinc-800 leading-relaxed font-sans">
                  {activeScenario.spokenScript}
                </p>
              </div>

              {/* Choreographed director actions */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-bold block">
                  Choreographed Visual Cues:
                </span>
                <div className="space-y-1 bg-white/70 p-2.5 rounded-xl border border-blue-100">
                  {activeScenario.directorCues.map((cue, idx) => (
                    <div key={idx} className="flex items-start gap-1.5 text-[11px] font-mono text-zinc-700">
                      <span className="text-blue-600 font-bold shrink-0">›</span>
                      <span>{cue}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-blue-100 flex items-center justify-between text-[11px] font-mono text-blue-800">
            <span>LLM: Gemini 2.5 Flash</span>
            <span className="font-semibold">Sub-12ms TTS sync</span>
          </div>
        </div>

        {/* Column 3: Remotion Vector Blueprint (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6 flex flex-col justify-between shadow-xs">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center">
                  <Film size={16} />
                </div>
                <div>
                  <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">Stage 03 • Render</span>
                  <strong className="text-xs font-bold text-zinc-900">Remotion Vector Blueprint</strong>
                </div>
              </div>
              <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-200 font-bold">
                1080P 30FPS
              </span>
            </div>

            {/* Canvas Stage */}
            <div className="h-44 rounded-xl bg-white border border-zinc-200 relative overflow-hidden flex items-center justify-center p-2 shadow-inner">
              <div className="absolute inset-0 bg-dot-grid opacity-30" />
              <div className="relative z-10 w-full h-full">
                {activeScenario.renderGraphic}
              </div>
            </div>

            {/* Render Telemetry */}
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-zinc-600">
              <div className="bg-zinc-50 p-2.5 rounded-lg border border-zinc-100">
                <span className="text-zinc-400 block text-[10px]">Total Frames:</span>
                <span className="font-bold text-zinc-800">{activeScenario.renderStats.frames} @ {activeScenario.renderStats.fps}fps</span>
              </div>
              <div className="bg-zinc-50 p-2.5 rounded-lg border border-zinc-100">
                <span className="text-zinc-400 block text-[10px]">Duration:</span>
                <span className="font-bold text-zinc-800">{activeScenario.renderStats.audioDuration}</span>
              </div>
            </div>
          </div>

          <div className="pt-3 mt-3 border-t border-zinc-100 flex items-center justify-between text-[11px] font-mono text-zinc-500">
            <span>Engine: Headless Chromium</span>
            <span className="text-orange-700 font-bold flex items-center gap-1">
              <Sparkles size={12} /> Vector Keyframes
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
