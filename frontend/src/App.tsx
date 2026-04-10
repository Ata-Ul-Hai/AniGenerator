import { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage.tsx";
import AdminLogin from "./components/AdminLogin.tsx";
import Dashboard from "./components/Dashboard.tsx";

/**
 * Decode a JWT payload without verifying signature (client-side expiry check only).
 */
function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return false;
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

function App() {
  const [view, setView] = useState<"landing" | "login" | "dashboard">("landing");
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem("admin_token");
    // Don't restore expired tokens
    if (stored && isTokenExpired(stored)) {
      localStorage.removeItem("admin_token");
      return null;
    }
    return stored;
  });

  useEffect(() => {
    if (token) {
      localStorage.setItem("admin_token", token);
    } else {
      localStorage.removeItem("admin_token");
    }
  }, [token]);

  const handleLogin = (t: string) => { setToken(t); setView("dashboard"); };
  const handleLogout = () => { setToken(null); setView("landing"); };
  const handleGetStarted = () => setView(token ? "dashboard" : "login");

  return (
    <div className="dark">
      {view === "landing" && <LandingPage onGetStarted={handleGetStarted} />}
      {view === "login" && <AdminLogin onLogin={handleLogin} onBack={() => setView("landing")} />}
      {view === "dashboard" && token && <Dashboard token={token} onLogout={handleLogout} />}
    </div>
  );
}

export default App;
