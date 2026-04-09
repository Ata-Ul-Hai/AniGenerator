import React, { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "../lib/utils";

interface Props {
  onLogin: (token: string) => void;
  onBack: () => void;
}

const AdminLogin: React.FC<Props> = ({ onLogin, onBack }) => {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) throw new Error("Invalid credentials");
      const data = await resp.json();
      onLogin(data.access_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Server error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <p className="text-[10px] tracking-[0.35em] uppercase text-zinc-600 mb-3">AniGenerator</p>
          <h1 className="text-3xl font-bold text-zinc-100">Control Room Access</h1>
          <p className="text-zinc-600 text-sm mt-2">Administrator credentials required</p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-[10px] text-zinc-500 tracking-[0.2em] uppercase">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className={cn(
                  "w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-100 text-sm",
                  "focus:outline-none focus:border-zinc-600 transition-colors"
                )}
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] text-zinc-500 tracking-[0.2em] uppercase">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className={cn(
                  "w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-100 text-sm",
                  "focus:outline-none focus:border-zinc-600 transition-colors"
                )}
                placeholder="••••••••"
              />
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-red-400 text-sm"
              >
                {error}
              </motion.p>
            )}

            <button
              type="submit"
              disabled={loading}
              className={cn(
                "w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200",
                loading
                  ? "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                  : "bg-zinc-100 text-zinc-900 hover:bg-white hover:scale-[1.02] active:scale-[0.98]"
              )}
            >
              {loading ? "Authenticating..." : "Sign In →"}
            </button>
          </form>
        </div>

        <button
          onClick={onBack}
          className="block w-full text-center mt-6 text-zinc-700 hover:text-zinc-400 text-sm transition-colors"
        >
          ← Back to Home
        </button>
      </motion.div>
    </div>
  );
};

export default AdminLogin;
