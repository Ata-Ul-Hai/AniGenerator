import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Video } from "lucide-react";
import { IconBrandGithub } from "@tabler/icons-react";
import { useAuth } from "../../context/AuthContext";
import anigenLogo from "../../assets/AnigenLogo.png";

interface StudioNavbarProps {
  onLaunchStudio?: () => void;
}

export const StudioNavbar: React.FC<StudioNavbarProps> = ({ onLaunchStudio }) => {
  const { user } = useAuth();
  const [activeSection, setActiveSection] = useState<string>("");

  useEffect(() => {
    const sectionIds = ["compiler", "capabilities", "pipeline", "comparison"];

    const handleScroll = () => {
      const scrollPosition = window.scrollY + 140;

      for (const id of sectionIds) {
        const element = document.getElementById(id);
        if (element) {
          const top = element.offsetTop;
          const height = element.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            setActiveSection(id);
            return;
          }
        }
      }

      // If at top or past sections
      if (window.scrollY < 200) {
        setActiveSection("");
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll(); // Initial check

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navItems = [
    { id: "compiler", label: "Deconstruction Bench", href: "#compiler" },
    { id: "capabilities", label: "Capabilities", href: "#capabilities" },
    { id: "pipeline", label: "Pipeline", href: "#pipeline" },
    { id: "comparison", label: "Cognitive Science", href: "#comparison" },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-200/80 bg-white/90 backdrop-blur-md transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl border border-zinc-200 overflow-hidden flex items-center justify-center p-1 bg-white shadow-xs group-hover:border-zinc-300 transition-all">
            <img src={anigenLogo} alt="AniGenerator Logo" className="w-full h-full object-contain" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-tight text-zinc-900 text-base">AniGenerator</span>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-200/60">
                Studio
              </span>
            </div>
            <span className="text-[10px] text-zinc-600 -mt-0.5 tracking-tight font-medium">Document to Whiteboard Video</span>
          </div>
        </Link>

        {/* Center navigation links with subtle, non-flashy highlight */}
        <nav className="hidden md:flex items-center gap-1 font-medium text-xs">
          {navItems.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <a
                key={item.id}
                href={item.href}
                className={`px-3.5 py-1.5 rounded-lg text-xs transition-all duration-200 ${
                  isActive
                    ? "bg-zinc-100 text-zinc-900 font-semibold border border-zinc-200/80 shadow-xs"
                    : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50 border border-transparent"
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Right side CTAs */}
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/Ata-Ul-Hai/AniGenerator"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 text-xs font-medium transition-all shadow-xs"
          >
            <IconBrandGithub size={16} />
            <span>GitHub</span>
          </a>

          {user ? (
            <Link
              to="/dashboard"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold shadow-xs transition-all"
            >
              <Video size={14} />
              <span>Enter Studio</span>
            </Link>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-3 py-1.5 text-xs text-zinc-600 hover:text-zinc-900 transition-colors font-medium"
              >
                Sign In
              </Link>
              <button
                onClick={onLaunchStudio}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold shadow-xs transition-all hover:scale-[1.01] active:scale-[0.99]"
              >
                <span>Launch Studio</span>
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
