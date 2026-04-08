import React, { useState, useEffect, useRef } from 'react';

interface Props {
  token: string;
  onLogout: () => void;
}

interface Job {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  error?: string;
  video_path?: string;
  render_props?: any;
}

const Dashboard: React.FC<Props> = ({ token, onLogout }) => {
  const [file, setFile] = useState<File | null>(null);
  const [maxScenes, setMaxScenes] = useState(12);
  const [renderVideo, setRenderVideo] = useState(true);
  const [status, setStatus] = useState({ message: 'Welcome to Control Room', type: '' });
  const [job, setJob] = useState<Job | null>(null);
  const [extractedText, setExtractedText] = useState('');
  const pollInterval = useRef<any>(null);

  const API_BASE_URL = import.meta.env.VITE_API_URL || '';

  const stopPolling = () => {
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setStatus({ message: 'Uploading document...', type: 'warn' });
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });

      if (!resp.ok) throw new Error('Upload failed');
      
      const data = await resp.json();
      setExtractedText(data.extracted_text);
      setStatus({ message: 'Extraction successful.', type: 'ok' });
    } catch (err: any) {
      setStatus({ message: err.message, type: 'err' });
    }
  };

  const handleGenerate = async () => {
    if (!extractedText) return;
    setStatus({ message: 'Submitting job...', type: 'warn' });

    try {
      const resp = await fetch(`${API_BASE_URL}/generate/async`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify({
          extracted_text: extractedText,
          max_scenes: maxScenes,
          render_video: renderVideo
        }),
      });

      if (!resp.ok) throw new Error('Generation trigger failed');

      const data = await resp.json();
      setJob({ job_id: data.job_id, status: data.status });
      startPolling(data.job_id);
    } catch (err: any) {
      setStatus({ message: err.message, type: 'err' });
    }
  };

  const startPolling = (jobId: string) => {
    stopPolling();
    pollInterval.current = setInterval(async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!resp.ok) return;

        const data = await resp.json();
        setJob(data);

        if (data.status === 'completed' || data.status === 'failed') {
          stopPolling();
          setStatus({ 
            message: data.status === 'completed' ? 'Generation complete!' : 'Generation failed.', 
            type: data.status === 'completed' ? 'ok' : 'err' 
          });
        }
      } catch (err) {
        console.error('Polling error', err);
      }
    }, 2000);
  };

  return (
    <div className="dashboard">
      <div className="card side-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.25rem' }}>Engine Config</h2>
          <button onClick={onLogout} style={{ background: 'none', border: 'none', color: 'var(--error)', cursor: 'pointer', fontSize: '0.75rem' }}>LOGOUT</button>
        </div>

        <div className="input-group">
          <label>Source Document</label>
          <input type="file" className="input-field" onChange={e => setFile(e.target.files?.[0] || null)} />
        </div>

        <button className="btn-primary" style={{ width: '100%', marginBottom: '24px' }} onClick={handleUpload} disabled={!file}>
          1. Extract Text
        </button>

        <div className="input-group">
          <label>Max Scenes</label>
          <input type="number" className="input-field" value={maxScenes} onChange={e => setMaxScenes(Number(e.target.value))} />
        </div>

        <div className="input-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input type="checkbox" checked={renderVideo} onChange={e => setRenderVideo(e.target.checked)} />
          <label style={{ margin: 0 }}>Render MP4 Video</label>
        </div>

        <button className="btn-primary" style={{ width: '100%', background: 'var(--accent)' }} onClick={handleGenerate} disabled={!extractedText || !!pollInterval.current}>
          2. Generate & Render
        </button>

        <div style={{ marginTop: '24px', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.875rem' }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: '4px' }}>Status:</p>
          <p className={status.type}>{status.message}</p>
        </div>
      </div>

      <div className="main-content">
        <div className="card" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1rem' }}>Whiteboard Preview</h3>
            {job && <span className={`badge badge-${job.status}`}>{job.status}</span>}
          </div>

          <div className="video-container">
            {job?.status === 'completed' && job.video_path ? (
              <video controls src={`${API_BASE_URL}/${job.video_path.replace('artifacts/', 'artifacts/')}`} />
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                {job?.status === 'running' ? 'Rendering in progress...' : 'Ready for generation'}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1rem', marginBottom: '16px' }}>Extracted Text Preview</h3>
          <div style={{ 
            height: '200px', 
            overflowY: 'auto', 
            fontSize: '0.875rem', 
            color: 'var(--text-muted)', 
            whiteSpace: 'pre-wrap',
            padding: '12px',
            background: '#0f172a',
            borderRadius: '8px'
          }}>
            {extractedText || 'No text extracted yet.'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
