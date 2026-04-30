import { useState, useEffect } from 'react';
import { Download, ExternalLink, Loader2, AlertTriangle } from 'lucide-react';
import api from '../api/client';

export default function AuditTrail() {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAudits() {
      try {
        const res = await api.get('/audit-trail');
        setAudits(res.data);
      } catch (err) {
        console.error("Failed to fetch audit trail", err);
        setError("Failed to load audit history.");
      } finally {
        setLoading(false);
      }
    }
    fetchAudits();
  }, []);

  const exportCSV = () => {
    if (audits.length === 0) return;
    
    // Convert to CSV
    const headers = ['Date', 'Repository', 'Finding', 'Severity', 'Action', 'Decided By', 'ArmorIQ ID'];
    const rows = audits.map(log => [
      log.decided_at ? new Date(log.decided_at).toLocaleString() : '',
      log.repo_full_name,
      log.finding_title,
      log.severity,
      log.action,
      log.decided_by,
      log.armoriq_audit_log_id
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(',') + "\n"
      + rows.map(e => e.map(cell => `"${cell}"`).join(",")).join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "audit_trail.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6">
        <Loader2 className="w-12 h-12 text-armorclaw-accent animate-spin mb-4" />
        <p className="text-text-secondary">Loading audit trail...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6 text-center">
        <AlertTriangle className="w-16 h-16 text-critical mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-critical mb-4">Error</h2>
        <p className="text-text-secondary mb-8">{error}</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-bold">Audit Trail</h2>
          <p className="text-text-secondary text-sm mt-1">Full history of decisions verified by ArmorIQ.</p>
        </div>
        <button onClick={exportCSV} className="bg-surface-elevated hover:bg-border text-text-primary py-2 px-4 rounded-lg flex items-center gap-2 text-sm border border-border transition-colors">
          <Download className="w-4 h-4" /> Export CSV
        </button>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="p-4 border-b border-border bg-surface-elevated flex gap-4">
          <input type="text" placeholder="Filter by repo..." className="bg-background border border-border rounded px-3 py-1.5 text-sm w-48 text-text-primary" />
          <select className="bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary">
            <option>All Actions</option>
            <option>Accepted</option>
            <option>Edited</option>
            <option>Dismissed</option>
          </select>
        </div>
        
        <table className="w-full text-left">
          <thead className="bg-surface-elevated text-text-secondary text-sm border-b border-border">
            <tr>
              <th className="p-4 font-medium">Date</th>
              <th className="p-4 font-medium">Repository</th>
              <th className="p-4 font-medium">Finding</th>
              <th className="p-4 font-medium">Action</th>
              <th className="p-4 font-medium">Decided By</th>
              <th className="p-4 font-medium text-right">ArmorIQ ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-sm">
            {audits.length === 0 && (
              <tr><td colSpan="6" className="p-4 text-center text-text-secondary">No audit history found.</td></tr>
            )}
            {audits.map(log => (
              <tr key={log.id} className="hover:bg-surface-elevated/50 transition-colors">
                <td className="p-4 text-text-secondary">{log.decided_at ? new Date(log.decided_at).toLocaleString() : ''}</td>
                <td className="p-4 font-medium">{log.repo_full_name}</td>
                <td className="p-4">
                  <div>{log.finding_title}</div>
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded mt-1 inline-block ${
                    log.severity === 'critical' ? 'bg-critical/20 text-critical border border-critical/30' : 
                    log.severity === 'warning' ? 'bg-warning/20 text-warning border border-warning/30' : 
                    'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  }`}>
                    {log.severity}
                  </span>
                </td>
                <td className="p-4">
                  <span className={`font-medium ${
                    log.action === 'accepted' ? 'text-success' : 
                    log.action === 'edited' ? 'text-warning' : 
                    'text-text-secondary'
                  }`}>
                    {log.action}
                  </span>
                </td>
                <td className="p-4">{log.decided_by}</td>
                <td className="p-4 text-right">
                  <span className="font-mono text-armoriq-accent text-xs">
                    {log.armoriq_audit_log_id}
                  </span>
                  {log.github_issue_url && (
                    <a href={log.github_issue_url} target="_blank" rel="noreferrer" className="block text-blue-400 flex items-center justify-end gap-1 hover:underline mt-1">
                      GitHub Issue <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
