import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { IconBrandGithub } from "@tabler/icons-react";
import anigenLogo from "../assets/AnigenLogo.png";
import { StudioNavbar } from "./layout/StudioNavbar";
import { CompilerWorkbench } from "./ui/CompilerWorkbench";
import { BentoFeatures } from "./ui/BentoFeatures";
import { ComparisonShowcase } from "./ui/ComparisonShowcase";
import { ArchitecturePipeline } from "./ui/ArchitecturePipeline";

interface Props {
  onGetStarted: () => void;
}

const LandingPage: React.FC<Props> = ({ onGetStarted }) => {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] selection:bg-orange-100 selection:text-orange-900 relative overflow-x-hidden font-sans">
      {/* Studio Navigation Bar */}
      <StudioNavbar onLaunchStudio={onGetStarted} />

      {/* Hero Section */}
      <section className="relative pt-28 pb-16 md:pt-36 md:pb-24 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto text-center space-y-7">
          {/* Eyebrow badge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex items-center justify-center"
          >
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono font-medium text-zinc-700 bg-zinc-100 border border-zinc-200 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-blue-600 inline-block animate-pulse" />
              <span>Autonomous Document-to-Video Engine • Remotion + Gemini</span>
            </div>
          </motion.div>

          {/* Main Headline */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="space-y-4"
          >
            <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-zinc-900 leading-[1.08] max-w-4xl mx-auto">
              Compiling technical documents into{" "}
              <span className="text-blue-600">
                hand-drawn whiteboard
              </span>{" "}
              explainers.
            </h1>
            <p className="max-w-2xl mx-auto text-base sm:text-lg text-zinc-600 font-normal leading-relaxed">
              No manual keyframing or animation timelines. AniGenerator parses dense PDFs and RFCs, plans pedagogical spoken narration with Gemini, and choreographs vector sketch paths in Remotion.
            </p>
          </motion.div>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-1"
          >
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-xs hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
            >
              <span>Launch Whiteboard Studio</span>
              <ArrowRight size={17} />
            </button>

            <a
              href="https://github.com/Ata-Ul-Hai/AniGenerator"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 font-semibold text-sm flex items-center justify-center gap-2.5 transition-all shadow-xs"
            >
              <IconBrandGithub size={18} />
              <span>Star on GitHub</span>
            </a>
          </motion.div>

          {/* Trust points */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap items-center justify-center gap-6 pt-2 text-xs text-zinc-500 font-mono"
          >
            <span className="flex items-center gap-1.5">
              <CheckCircle2 size={13} className="text-blue-600" />
              1080p 30fps Remotion MP4
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 size={13} className="text-blue-600" />
              Gemini 2.5 Flash Storyboards
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 size={13} className="text-blue-600" />
              Direct PDF / DOCX Ingestion
            </span>
          </motion.div>

          {/* Interactive Deconstruction Station */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-14 md:mt-20 text-left"
          >
            <CompilerWorkbench />
          </motion.div>
        </div>
      </section>

      {/* Bento Grid Capabilities */}
      <BentoFeatures />

      {/* Comparison: Dense Document vs Whiteboard Video */}
      <ComparisonShowcase />

      {/* Architecture & Pipeline */}
      <ArchitecturePipeline />

      {/* Final Studio Call to Action */}
      <section className="py-24 md:py-32 px-4 sm:px-6 relative border-t border-zinc-200 bg-white">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <div className="w-12 h-12 rounded-xl border border-zinc-200 bg-white p-2 flex items-center justify-center mx-auto shadow-xs">
            <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain" />
          </div>

          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-zinc-900 leading-tight">
            Ready to turn your documentation into captivating whiteboard videos?
          </h2>
          <p className="text-zinc-600 text-sm md:text-base max-w-xl mx-auto">
            Upload your document and let Gemini and Remotion choreograph hand-drawn pedagogical explainers in minutes.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-xs hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
            >
              <span>Enter Director Studio</span>
              <ArrowRight size={17} />
            </button>
            <a
              href="https://github.com/Ata-Ul-Hai/AniGenerator"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-xs"
            >
              <IconBrandGithub size={18} />
              <span>Explore Codebase</span>
            </a>
          </div>
        </div>
      </section>

      {/* Studio Footer */}
      <footer className="border-t border-zinc-200 bg-zinc-50 px-4 sm:px-6 py-10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-zinc-500 font-mono">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg border border-zinc-200 bg-white p-1 flex items-center justify-center shadow-xs">
              <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain" />
            </div>
            <span className="font-bold text-zinc-800">AniGenerator Studio</span>
            <span className="text-zinc-400">|</span>
            <span>Document-to-Whiteboard Engine</span>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/Ata-Ul-Hai/AniGenerator"
              target="_blank"
              rel="noreferrer"
              className="hover:text-zinc-900 transition-colors"
            >
              GitHub Repository
            </a>
            <span>•</span>
            <span>Cloud Run Ready</span>
            <span>•</span>
            <span>MIT License</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
