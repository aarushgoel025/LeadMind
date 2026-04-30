import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, PlayCircle, Clock } from 'lucide-react';
import api from '../api/client';

export default function Dashboard() {
  const navigate = useNavigate();
  const [isScanning, setIsScanning] = useState(false);
  const [user, setUser] = useState(null);
  const [repos, setRepos] = useState([]);
  const [recentScans, setRecentScans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [userRes, reposRes, scansRes] = await Promise.all([
          api.get('/auth/me'),
          api.get('/repos'),
          api.get('/scans/history')
        ]);
        setUser(userRes.data);
        setRepos(reposRes.data);
        setRecentScans(scansRes.data);
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
      navigate('/');
    } catch (err) {
      console.error(err);
    }
  };

  const startScan = async (repoFullName) => {
    setIsScanning(true);
    try {
      const res = await api.post('/scan', { repo_full_name: repoFullName });
      navigate(`/scan/${res.data.scan_id}/progress`);
    } catch (err) {
      console.error("Failed to start scan", err);
      setIsScanning(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-text-secondary">Loading dashboard...</div>;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-10">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-border rounded-full flex items-center justify-center overflow-hidden border-2 border-armorclaw-accent">
            <img src={user?.avatar_url || "https://github.com/github.png"} alt="Avatar" className="w-full h-full object-cover" />
          </div>
          <div>
            <h2 className="text-2xl font-bold">Welcome, {user?.name || user?.login || 'Tech Lead'}</h2>
            <p className="text-text-secondary text-sm">GitHub connected</p>
          </div>
        </div>
        <button onClick={handleLogout} className="flex items-center gap-2 text-text-secondary hover:text-critical transition-colors">
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>

      <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
        <Clock className="w-5 h-5 text-armoriq-accent" /> Your Repositories
      </h3>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        {repos.map(repo => {
          // Find if there's a recent scan for this repo
          const recentScan = recentScans.find(s => s.repo_full_name === repo.fullName);
          const score = recentScan && recentScan.status === 'complete' ? recentScan.health_score : null;
          
          return (
            <div key={repo.id} className="bg-surface p-6 rounded-xl border border-border hover:border-text-secondary transition-colors group">
              <div className="flex justify-between items-start mb-4">
                <h4 className="font-bold text-lg text-text-primary truncate" title={repo.fullName}>{repo.name}</h4>
                <span className="text-xs font-medium px-2 py-1 bg-surface-elevated rounded-md border border-border text-text-secondary">
                  {repo.language}
                </span>
              </div>
              
              <div className="flex justify-between items-end">
                <div>
                  <p className="text-xs text-text-secondary mb-1">Last scanned</p>
                  <p className="text-sm font-medium">{recentScan ? new Date(recentScan.scanned_at).toLocaleDateString() : 'Never'}</p>
                  {score !== null && (
                    <div className="mt-2 text-sm flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-success"></span>
                      Score: <span className="font-bold text-success">{score}/100</span>
                    </div>
                  )}
                </div>
                <button 
                  onClick={() => startScan(repo.fullName)}
                  disabled={isScanning}
                  className="bg-armorclaw-accent hover:bg-opacity-80 text-white p-2 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  <PlayCircle className="w-5 h-5" />
                  <span className="text-sm font-bold">{isScanning ? 'Starting...' : 'Scan'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <h3 className="text-xl font-bold mb-6">Recent Scans</h3>
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-surface-elevated text-text-secondary text-sm">
            <tr>
              <th className="p-4 font-medium">Repository</th>
              <th className="p-4 font-medium">Date</th>
              <th className="p-4 font-medium">Status</th>
              <th className="p-4 font-medium">Health Score</th>
              <th className="p-4 font-medium">Findings</th>
              <th className="p-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {recentScans.length === 0 ? (
              <tr><td colSpan="6" className="p-4 text-center text-text-secondary">No recent scans found.</td></tr>
            ) : (
              recentScans.map(scan => (
                <tr key={scan.id}>
                  <td className="p-4 font-medium">{scan.repo_full_name}</td>
                  <td className="p-4 text-text-secondary">{new Date(scan.scanned_at).toLocaleDateString()}</td>
                  <td className="p-4 text-text-secondary">{scan.status}</td>
                  <td className="p-4 text-success font-bold">{scan.health_score ?? '-'}</td>
                  <td className="p-4">{scan.findings_count ?? 0}</td>
                  <td className="p-4 text-right">
                    {scan.status === 'complete' ? (
                      <button 
                        onClick={() => navigate(`/scan/${scan.id}/report`)}
                        className="text-armoriq-accent hover:underline text-sm font-medium"
                      >
                        View Report
                      </button>
                    ) : (
                      <button 
                        onClick={() => navigate(`/scan/${scan.id}/progress`)}
                        className="text-text-secondary hover:underline text-sm font-medium"
                      >
                        View Progress
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
