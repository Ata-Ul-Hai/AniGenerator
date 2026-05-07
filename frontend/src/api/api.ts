import axios from 'axios';

// When deployed to Vercel, this /api path is proxied to Google Cloud
// Locally, it talks to localhost:8000 via the Vite proxy (or direct if configured)
const API_BASE_URL = '/api'; 

const api = axios.create({
  baseURL: `${API_BASE_URL}/v1`,
  withCredentials: true, // Crucial for HttpOnly Cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
