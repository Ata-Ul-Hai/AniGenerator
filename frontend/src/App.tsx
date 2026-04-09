import { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage.tsx";
import AdminLogin from "./components/AdminLogin.tsx";
import Dashboard from "./components/Dashboard.tsx";

function App() {
  const [view, setView] = useState<"landing" | "login" | "dashboard">("landing");
  const [token, setToken] = useState<string | null>(localStorage.getItem("admin_token"));

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
