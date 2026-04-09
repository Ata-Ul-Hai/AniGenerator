import { useRef } from "react";
import { motion } from "framer-motion";
import { Vortex } from "./ui/vortex";
import { TypewriterEffect } from "./ui/typewriter-effect";
import { BentoGrid, BentoGridItem } from "./ui/bento-grid";
import { EvervaultCard } from "./ui/evervault-card";
import { FileText, Film, Zap, Lock, Clock, Layers } from "lucide-react";

const FEATURES = [
  { icon: FileText, title: "Document Parsing", description: "Extracts clean semantic structure from PDFs, DOCX, and plain text with precision.", span: "md:col-span-2" },
  { icon: Zap, title: "LLM Scene Direction", description: "Gemini orchestrates each scene with choreography optimized for comprehension.", span: "" },
  { icon: Film, title: "Whiteboard Rendering", description: "Remotion draws SVG-first animations synced frame-by-frame to narration audio.", span: "" },
  { icon: Lock, title: "Admin-Gated Access", description: "JWT-secured endpoints ensure only authorized users trigger generation.", span: "" },
  { icon: Clock, title: "Async Job Queue", description: "Jobs persist in PostgreSQL, surviving container restarts and scaling events.", span: "md:col-span-2" },
  { icon: Layers, title: "Cloud-Native Storage", description: "Artifacts are uploaded to GCS and served globally with minimal latency.", span: "" },
];

interface Props {
  onGetStarted: () => void;
}

export default function LandingPage({ onGetStarted }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 overflow-x-hidden" ref={scrollRef}>

      {/* HERO */}
      <Vortex
        containerClassName="min-h-screen flex flex-col items-center justify-center px-6 text-center relative"
        className="flex flex-col items-center gap-8 max-w-4xl mx-auto w-full"
        particleCount={500}
        baseHue={0}
      >
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: "easeOut" }}
          className="space-y-7"
        >
          <span className="inline-block text-[10px] tracking-[0.35em] uppercase text-zinc-500 border border-zinc-800 rounded-full px-4 py-1.5">
            Document → Video Pipeline
          </span>

          <h1 className="text-5xl md:text-7xl font-bold leading-[1.1] text-zinc-100">
            <TypewriterEffect
              words={[
                { text: "Turn documents into" },
                { text: " whiteboard videos." },
              ]}
            />
          </h1>

          <p className="text-zinc-400 text-lg max-w-xl mx-auto leading-relaxed">
            Upload any document. AniGenerator extracts content, orchestrates scenes,
            synthesizes narration, and renders a hand-drawn animation — fully autonomous.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4 justify-center pt-2">
            <button
              onClick={onGetStarted}
              className="group px-8 py-3.5 bg-zinc-100 text-zinc-900 rounded-xl font-semibold text-sm
                         hover:bg-white transition-all duration-200 hover:scale-105 active:scale-95"
            >
              Launch Control Room
              <span className="ml-2 group-hover:translate-x-1 inline-block transition-transform">→</span>
            </button>
            <a
              href="https://github.com/Ata-Ul-Hai/AniGenerator"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-3.5 border border-zinc-800 text-zinc-500 rounded-xl font-medium text-sm
                         hover:border-zinc-600 hover:text-zinc-300 transition-all duration-200"
            >
              View Source
            </a>
          </div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2, duration: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-[9px] tracking-[0.4em] text-zinc-700 uppercase">Scroll</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
            className="w-px h-8 bg-gradient-to-b from-zinc-700 to-transparent"
          />
        </motion.div>
      </Vortex>

      {/* HOW IT WORKS */}
      <section className="py-32 px-6 border-t border-zinc-900">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
            className="text-center mb-16"
          >
            <p className="text-[10px] tracking-[0.35em] uppercase text-zinc-600 mb-4">How It Works</p>
            <h2 className="text-4xl font-bold text-zinc-100">Three stages. One video.</h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-zinc-900 border border-zinc-900 rounded-2xl overflow-hidden">
            {[
              { step: "01", label: "Parse", desc: "Your document is read and chunked into semantic units." },
              { step: "02", label: "Direct", desc: "Gemini composes scenes — narration, SVG visuals, timing." },
              { step: "03", label: "Render", desc: "Remotion renders a frame-perfect MP4 with synced audio." },
            ].map((s, i) => (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.12, duration: 0.5 }}
                className="bg-zinc-950 p-10 hover:bg-zinc-900/50 transition-colors duration-300"
              >
                <span className="text-6xl font-black text-zinc-900">{s.step}</span>
                <h3 className="text-xl font-semibold text-zinc-100 mt-4">{s.label}</h3>
                <p className="text-zinc-600 text-sm mt-2 leading-relaxed">{s.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* BENTO FEATURES */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <p className="text-[10px] tracking-[0.35em] uppercase text-zinc-600 mb-4">Under the Hood</p>
            <h2 className="text-4xl font-bold text-zinc-100">The system, laid bare.</h2>
          </motion.div>

          <BentoGrid>
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.07 }}
                className={f.span}
              >
                <EvervaultCard className="h-full min-h-[160px]">
                  <BentoGridItem
                    icon={<f.icon size={18} />}
                    title={f.title}
                    description={f.description}
                    className="border-0 bg-transparent p-6 h-full"
                  />
                </EvervaultCard>
              </motion.div>
            ))}
          </BentoGrid>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="border-t border-zinc-900 py-28 px-6">
        <div className="max-w-xl mx-auto text-center space-y-6">
          <h2 className="text-4xl font-bold text-zinc-100">Ready to generate?</h2>
          <p className="text-zinc-600 text-sm">Authorized administrators can access the pipeline directly.</p>
          <button
            onClick={onGetStarted}
            className="px-10 py-4 bg-zinc-100 text-zinc-900 rounded-xl font-semibold text-sm
                       hover:bg-white hover:scale-105 active:scale-95 transition-all duration-200"
          >
            Open Control Room →
          </button>
        </div>
        <p className="text-center text-zinc-800 text-[10px] mt-16 tracking-[0.4em] uppercase">
          AniGenerator · 2025
        </p>
      </section>
    </div>
  );
}
