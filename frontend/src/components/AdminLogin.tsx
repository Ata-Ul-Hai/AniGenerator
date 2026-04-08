import React, { useState } from 'react';

interface Props {
  onLogin: (token: string) => void;
  onBack: () => void;
}

const AdminLogin: React.FC<Props> = ({ onLogin, onBack }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // For hybrid deployment: Set this to your Cloud Run URL in Vercel settings
  const API_BASE_URL = import.meta.env.VITE_API_URL || '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!resp.ok) {
        throw new Error('Invalid credentials or server error');
      }

      const data = await resp.json();
      onLogin(data.access_token);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="card login-card">
        <h2 style={{ marginBottom: '24px', textAlign: 'center' }}>Admin Portal</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Username</label>
            <input 
              className="input-field" 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required
            />
          </div>
          <div className="input-group">
            <label>Password</label>
            <input 
              className="input-field" 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required
            />
          </div>

          {error && <p style={{ color: 'var(--error)', marginBottom: '16px', fontSize: '0.875rem' }}>{error}</p>}

          <button className="btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <button 
          onClick={onBack}
          style={{ 
            width: '100%', 
            background: 'none', 
            border: 'none', 
            color: 'var(--text-muted)', 
            marginTop: '16px',
            cursor: 'pointer'
          }}
        >
          &larr; Back to Landing
        </button>
      </div>
    </div>
  );
};

export default AdminLogin;
