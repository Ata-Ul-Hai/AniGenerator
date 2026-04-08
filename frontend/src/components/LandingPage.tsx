import React from 'react';

interface Props {
  onGetStarted: () => void;
}

const LandingPage: React.FC<Props> = ({ onGetStarted }) => {
  return (
    <div className="landing-page">
      <header className="hero">
        <h1>Transform Documents into <br /> Whiteboard Magic</h1>
        <p>
          The ultimate Document-to-Video engine powered by AI. 
          Upload your PDFs, DOCX, or text files and watch as they turn into 
          professional, educational whiteboard animations.
        </p>
        <button className="btn-primary" style={{ padding: '16px 40px', fontSize: '1.2rem' }} onClick={onGetStarted}>
          Launch Control Room
        </button>
      </header>

      <section style={{ padding: '60px 24px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '40px' }}>
          <div className="card">
            <h3 style={{ marginBottom: '12px', color: 'var(--accent)' }}>Smart Parsing</h3>
            <p style={{ color: 'var(--text-muted)' }}>Automatically extracts key concepts and creates structured lesson choreography.</p>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: '12px', color: 'var(--accent)' }}>AI Narration</h3>
            <p style={{ color: 'var(--text-muted)' }}>Natural-sounding voiceovers synced perfectly with on-screen whiteboard drawing.</p>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: '12px', color: 'var(--accent)' }}>HD Rendering</h3>
            <p style={{ color: 'var(--text-muted)' }}>Powered by Remotion & Manim logic for frame-perfect, high-definition output.</p>
          </div>
        </div>
      </section>
      
      <footer style={{ padding: '40px 24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        &copy; 2026 AniGenerator Production Engine. Built for Educators.
      </footer>
    </div>
  );
};

export default LandingPage;
