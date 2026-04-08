import { useState, useEffect } from 'react';
import './App.css';
import LandingPage from './components/LandingPage.tsx';
import Dashboard from './components/Dashboard.tsx';
import AdminLogin from './components/AdminLogin.tsx';

function App() {
  const [view, setView] = useState<'landing' | 'login' | 'dashboard'>('landing');
  const [token, setToken] = useState<string | null>(localStorage.getItem('admin_token'));

  useEffect(() => {
    if (token) {
      localStorage.setItem('admin_token', token);
      if (view === 'login') setView('dashboard');
    } else {
      localStorage.removeItem('admin_token');
    }
  }, [token, view]);

  const handleLogout = () => {
    setToken(null);
    setView('landing');
  };

  return (
    <div className="app-container">
      {view === 'landing' && (
        <LandingPage onGetStarted={() => setView(token ? 'dashboard' : 'login')} />
      )}
      
      {view === 'login' && (
        <AdminLogin onLogin={setToken} onBack={() => setView('landing')} />
      )}
      
      {view === 'dashboard' && token && (
        <Dashboard token={token} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;
