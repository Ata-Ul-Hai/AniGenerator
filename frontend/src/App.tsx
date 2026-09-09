import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import LandingPage from "./components/LandingPage.tsx";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import Dashboard from "./components/Dashboard.tsx"; // Will refactor later
import AdminPanel from "./pages/AdminPanel"; // Will create next

function App() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // NOTE: Do NOT block rendering here on `loading`.
  // The landing page is public and must render immediately.
  // ProtectedRoute handles the loading state for auth-gated pages.

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] font-sans selection:bg-orange-100 selection:text-orange-900">
      <Routes>
        <Route path="/" element={<LandingPage onGetStarted={() => navigate("/dashboard")} />} />
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />
        <Route path="/signup" element={user ? <Navigate to="/dashboard" /> : <SignupPage />} />
        
        {/* Protected User Dashboard */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              {user?.is_beta_authorized ? (
                <Dashboard token="cookie" onLogout={logout} />
              ) : (
                <Navigate to="/pending" />
              )}
            </ProtectedRoute>
          } 
        />

        {/* Waitlist Pending View */}
        <Route 
          path="/pending" 
          element={
            <ProtectedRoute>
              <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC] text-[#0F172A] px-4">
                <div className="max-w-md w-full p-8 rounded-2xl border border-zinc-200 bg-white text-center shadow-lg space-y-5">
                  <div className="w-14 h-14 rounded-2xl bg-orange-50 border border-orange-200 flex items-center justify-center text-orange-600 mx-auto">
                    <span className="text-2xl font-mono font-bold">⏳</span>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Account Pending Verification</h1>
                    <p className="text-xs text-zinc-600 mt-2 leading-relaxed">
                      Your application has been received and is currently waiting in the studio queue. An administrator will authorize your account to allocate Remotion GPU render capacity.
                    </p>
                  </div>
                  <div className="pt-3 border-t border-zinc-100 flex items-center justify-between text-xs text-zinc-500 font-mono">
                    <span>Account: {user?.username}</span>
                    <button 
                      onClick={logout} 
                      className="text-orange-700 hover:text-orange-900 font-bold transition-colors"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            </ProtectedRoute>
          }
        />

        {/* Protected Admin Panel */}
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute adminOnly>
              <AdminPanel />
            </ProtectedRoute>
          } 
        />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  );
}

export default App;
