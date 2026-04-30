import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Loader2, AlertCircle } from 'lucide-react';
import api from '../api/client';

export default function ScanProgress() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [scanData, setScanData] = useState({ progress: 0, status_message: 'Initializing...', status: 'pending' });
  const [error, setError] = useState(null);

  useEffect(() => {
    let interval;
    
    async function pollStatus() {
      try {
        const res = await api.get(`/scan/${id}`);
        setScanData(res.data);
        
        if (res.data.status === 'complete') {
          clearInterval(interval);
          setTimeout(() => navigate(`/scan/${id}/report`), 1000);
        } else if (res.data.status === 'failed') {
          clearInterval(interval);
          setError(res.data.status_message);
        }
      } catch (err) {
        console.error("Failed to poll scan status", err);
        clearInterval(interval);
        setError("Connection lost or scan not found.");
      }
    }

    // Poll every 2 seconds
    pollStatus();
    interval = setInterval(pollStatus, 2000);
    
    return () => clearInterval(interval);
  }, [id, navigate]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6">
        <div className="bg-surface border border-critical/50 p-10 rounded-2xl max-w-lg w-full text-center">
          <AlertCircle className="w-16 h-16 text-critical mx-auto mb-6" />
          <h2 className="text-2xl font-bold mb-4 text-critical">Scan Failed</h2>
          <p className="text-text-secondary">{error}</p>
          <button 
            onClick={() => navigate('/dashboard')}
            className="mt-8 bg-surface-elevated hover:bg-border px-6 py-2 rounded-lg transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6">
      <div className="bg-surface border border-border p-10 rounded-2xl max-w-lg w-full text-center">
        <Loader2 className="w-16 h-16 text-armorclaw-accent animate-spin mx-auto mb-8" />
        
        <h2 className="text-2xl font-bold mb-2">Scanning Repository</h2>
        <p className="text-text-secondary h-6 mb-8 transition-all">{scanData.status_message}</p>

        <div className="w-full bg-surface-elevated rounded-full h-3 mb-4 overflow-hidden border border-border">
          <div 
            className="bg-armorclaw-accent h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${scanData.progress}%` }}
          ></div>
        </div>
        <p className="text-sm font-medium text-text-secondary text-right">{Math.round(scanData.progress)}%</p>
      </div>
    </div>
  );
}
