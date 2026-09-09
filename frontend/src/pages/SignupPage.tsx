import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { ArrowRight, Eye, EyeOff, Lock, User, Mail, CheckCircle2, ArrowLeft } from "lucide-react";
import anigenLogo from "../assets/AnigenLogo.png";
import api from "../api/api";

const SignupPage: React.FC = () => {
  const [formData, setFormData] = useState({ username: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.post("/auth/signup", formData);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 3000);
    } catch (err: unknown) {
      let msg = "Signup request failed";
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 422) {
          const detail = err.response.data.detail;
          msg = Array.isArray(detail)
            ? detail.map((d: { msg: string }) => d.msg).join(", ")
            : detail;
        } else {
          msg = err.response?.data?.detail || msg;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col justify-between selection:bg-orange-100 selection:text-orange-900 font-sans">
      {/* Top Header */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-zinc-200 bg-white">
        <Link to="/" className="flex items-center gap-2 text-xs text-zinc-600 hover:text-zinc-900 transition-colors group">
          <ArrowLeft size={16} className="group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to AniGenerator Studio</span>
        </Link>
        <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
          Beta Program Registration
        </span>
      </header>

      {/* Main Container in Bright Theme */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-12 rounded-2xl border border-zinc-200 bg-white overflow-hidden shadow-lg">
          {/* Left: Brand Story (5 cols) */}
          <div className="lg:col-span-5 bg-zinc-50 p-8 md:p-10 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-zinc-200">
            <div className="space-y-5">
              <div className="w-12 h-12 rounded-xl border border-zinc-200 bg-white p-2 flex items-center justify-center shadow-xs">
                <img src={anigenLogo} alt="AniGenerator" className="w-full h-full object-contain" />
              </div>

              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-orange-700">
                  Early Access Program
                </span>
                <h2 className="text-2xl font-extrabold text-zinc-900 mt-1 leading-tight">
                  Join the AniGenerator Director Beta.
                </h2>
                <p className="text-xs text-zinc-600 mt-2 leading-relaxed">
                  Request access to generate whiteboard animations from technical docs. We review and approve accounts daily to safeguard rendering queue capacity.
                </p>
              </div>

              {/* Perks */}
              <div className="space-y-2.5 pt-2">
                {[
                  "Free daily Remotion 1080p render quota",
                  "Document upload up to 20MB",
                  "Gemini 2.5 Flash pedagogical storyboards",
                  "Priority Discord & GitHub community access",
                ].map((pt, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs text-zinc-700">
                    <CheckCircle2 size={14} className="text-orange-600 shrink-0" />
                    <span>{pt}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 pt-4 border-t border-zinc-200 text-[11px] font-mono text-zinc-500">
              <span>Managed by AniGenerator Cloud Run Engine</span>
            </div>
          </div>

          {/* Right: Signup Form or Success (7 cols) */}
          <div className="lg:col-span-7 p-8 md:p-12 flex flex-col justify-center bg-white">
            <div className="max-w-sm w-full mx-auto space-y-6">
              {success ? (
                <div className="text-center space-y-4 py-8">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mx-auto">
                    <CheckCircle2 size={32} />
                  </div>
                  <h2 className="text-2xl font-bold text-zinc-900">Application Received!</h2>
                  <p className="text-xs text-zinc-600 leading-relaxed max-w-sm mx-auto">
                    Your account request has been added to our beta review queue. An admin will authorize your profile shortly.
                  </p>
                  <p className="text-xs font-mono text-orange-700 pt-2 font-medium">
                    Redirecting to Sign In in 3 seconds...
                  </p>
                  <Link
                    to="/login"
                    className="inline-block mt-4 text-xs text-zinc-700 hover:text-zinc-900 underline font-mono"
                  >
                    Go to Sign In immediately &rarr;
                  </Link>
                </div>
              ) : (
                <>
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Request Beta Access</h1>
                    <p className="text-xs text-zinc-500 mt-1">Fill out the details below to join the waitlist.</p>
                  </div>

                  {error && (
                    <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-mono">
                      {error}
                    </div>
                  )}

                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700">Username</label>
                      <div className="relative">
                        <input
                          type="text"
                          value={formData.username}
                          onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                          className="w-full px-4 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 placeholder-zinc-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none transition-all pl-10"
                          placeholder="choose a username"
                          required
                        />
                        <User size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700">Email Address</label>
                      <div className="relative">
                        <input
                          type="email"
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          className="w-full px-4 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 placeholder-zinc-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none transition-all pl-10"
                          placeholder="you@company.com"
                          required
                        />
                        <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-zinc-700">Password</label>
                      <div className="relative">
                        <input
                          type={showPassword ? "text" : "password"}
                          value={formData.password}
                          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                          className="w-full px-4 py-2.5 bg-white border border-zinc-200 rounded-xl text-xs text-zinc-900 placeholder-zinc-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-100 outline-none transition-all pl-10 pr-10"
                          placeholder="••••••••"
                          required
                        />
                        <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                        >
                          {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-3 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-xl text-xs uppercase tracking-wider transition-all shadow-xs flex items-center justify-center gap-2 mt-2"
                    >
                      {loading ? (
                        <span>Submitting Request...</span>
                      ) : (
                        <>
                          <span>Request Beta Access</span>
                          <ArrowRight size={14} />
                        </>
                      )}
                    </button>
                  </form>

                  <div className="pt-4 border-t border-zinc-100 text-center">
                    <p className="text-xs text-zinc-600">
                      Already registered?{" "}
                      <Link to="/login" className="text-orange-700 hover:text-orange-900 font-semibold hover:underline">
                        Sign In here
                      </Link>
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="px-6 py-4 text-center text-xs text-zinc-400 font-mono border-t border-zinc-200 bg-white">
        &copy; {new Date().getFullYear()} AniGenerator Studio. All rights reserved.
      </footer>
    </div>
  );
};

export default SignupPage;
