import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, ShieldAlert, ShieldCheck, AlertTriangle, Info, Check, X, Edit2, Loader2 } from 'lucide-react';
import api from '../api/client';

export default function Report() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchReport() {
      try {
        const res = await api.get(`/scan/${id}/report`);
        setReportData(res.data);
      } catch (err) {
        console.error("Failed to fetch report", err);
        setError("Failed to load report. It may not exist or is not complete yet.");
      } finally {
        setLoading(false);
      }
    }
    fetchReport();
  }, [id]);

  const handleAction = async (findingId, action) => {
    try {
      await api.post(`/finding/${findingId}/decide`, { action });
      // Update local state to reflect action
      setReportData(prev => ({
        ...prev,
        findings: prev.findings.map(f => 
          f.id === findingId ? { ...f, status: action } : f
        )
      }));
    } catch (err) {
      console.error(`Failed to ${action} finding`, err);
      if (err.response?.data?.detail) {
        alert(err.response.data.detail);
      } else {
        alert(`Failed to perform action: ${action}`);
      }
    }
  };

  const exportPDF = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6">
        <Loader2 className="w-12 h-12 text-armorclaw-accent animate-spin mb-4" />
        <p className="text-text-secondary">Loading report...</p>
      </div>
    );
  }

  if (error || !reportData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6 text-center">
        <AlertTriangle className="w-16 h-16 text-critical mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-critical mb-4">Report Error</h2>
        <p className="text-text-secondary mb-8">{error}</p>
        <button onClick={() => navigate('/dashboard')} className="bg-surface-elevated hover:bg-border px-6 py-2 rounded-lg">Back to Dashboard</button>
      </div>
    );
  }

  const { scan, findings, summary } = reportData;

  return (
    <div className="flex h-[calc(100vh-73px)] print:block print:h-auto">
      {/* Sidebar */}
      <div className="w-64 border-r border-border bg-surface p-6 overflow-y-auto flex-shrink-0 print:hidden">
        <h3 className="font-bold mb-4 text-sm text-text-secondary uppercase tracking-wider">Filters</h3>
        
        <div className="mb-6">
          <h4 className="text-sm font-medium mb-2">Severity</h4>
          {['Critical', 'Warning', 'Suggestion'].map(s => (
            <label key={s} className="flex items-center gap-2 mb-2 text-sm">
              <input type="checkbox" defaultChecked className="rounded border-border bg-background text-armorclaw-accent" />
              {s}
            </label>
          ))}
        </div>

        <div className="mb-6">
          <h4 className="text-sm font-medium mb-2">Source</h4>
          {['ArmorClaw', 'Gemini AI'].map(s => (
            <label key={s} className="flex items-center gap-2 mb-2 text-sm">
              <input type="checkbox" defaultChecked className="rounded border-border bg-background text-armorclaw-accent" />
              {s}
            </label>
          ))}
        </div>

        <div className="mt-8 space-y-3">
          <button onClick={exportPDF} className="w-full bg-surface-elevated hover:bg-border text-text-primary py-2 px-4 rounded-lg flex items-center justify-center gap-2 text-sm transition-colors border border-border">
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-8 print:p-0">
        {/* Top Summary */}
        <div className="bg-surface border border-border rounded-xl p-6 mb-8 flex justify-between items-center print:border-none print:shadow-none">
          <div>
            <h1 className="text-2xl font-bold mb-1">{scan.repo_full_name}</h1>
            <p className="text-text-secondary text-sm">Scanned {new Date(scan.scanned_at).toLocaleString()} by {scan.scanned_by}</p>
          </div>
          
          <div className="flex items-center gap-8">
            <div className="flex gap-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-critical">{summary.critical}</p>
                <p className="text-xs text-text-secondary uppercase">Critical</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-warning">{summary.warning}</p>
                <p className="text-xs text-text-secondary uppercase">Warnings</p>
              </div>
            </div>
            
            <div className="relative w-24 h-24 flex items-center justify-center rounded-full border-4 border-warning">
              <div className="text-center">
                <span className="text-2xl font-bold text-warning">{scan.health_score}</span>
                <span className="block text-[10px] text-text-secondary uppercase mt-[-4px]">Score</span>
              </div>
            </div>
          </div>
        </div>

        {/* Findings List */}
        <div className="space-y-6 max-w-4xl">
          <h2 className="text-xl font-bold mb-4">Findings ({summary.total})</h2>
          
          {findings.length === 0 && (
            <div className="p-8 text-center text-text-secondary bg-surface rounded-xl border border-border">
              <ShieldCheck className="w-12 h-12 text-success mx-auto mb-4" />
              <p>No vulnerabilities found! Great job.</p>
            </div>
          )}

          {findings.map(finding => {
            if (finding.status === 'dismissed') return null;

            const isCritical = finding.severity === 'critical';
            
            return (
              <div key={finding.id} className={`bg-surface rounded-xl border ${finding.status === 'accepted' ? 'border-success bg-success/5' : isCritical ? 'border-critical/50' : 'border-border'} p-6 transition-all print:break-inside-avoid`}>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs font-bold rounded-md uppercase tracking-wider ${isCritical ? 'bg-critical/20 text-critical border border-critical/30' : finding.severity === 'warning' ? 'bg-warning/20 text-warning border border-warning/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'}`}>
                      {finding.severity}
                    </span>
                    <span className="text-xs text-text-secondary">[{finding.category}]</span>
                  </div>
                  <div className="text-xs text-text-secondary text-right">
                    Source: <span className={finding.source === 'armorclaw' ? 'text-armorclaw-accent font-medium' : 'text-armoriq-accent font-medium'}>{finding.source}</span>
                    <br/>Conf: {Math.round(finding.confidence * 100)}%
                  </div>
                </div>

                <h3 className="text-lg font-bold mb-1">{finding.title}</h3>
                <p className="text-sm font-mono text-text-secondary mb-4 bg-surface-elevated p-2 rounded border border-border inline-block">
                  {finding.file_path}:{finding.line_start}
                </p>

                <p className="text-sm mb-6 text-text-primary leading-relaxed">{finding.explanation}</p>

                {finding.suggested_fix && (
                  <div className="mb-6">
                    <p className="text-xs text-text-secondary mb-2 uppercase tracking-wider font-semibold">Suggested Fix:</p>
                    <pre className="bg-[#0d0f14] p-4 rounded-lg overflow-x-auto border border-border text-sm font-mono text-[#a3b3cc]">
                      {finding.suggested_fix}
                    </pre>
                  </div>
                )}

                {finding.armoriq_policy_blocked && (
                  <div className="flex items-center gap-2 text-warning text-sm bg-warning/10 p-3 rounded-lg mb-6 border border-warning/20">
                    <AlertTriangle className="w-4 h-4" />
                    <strong>Policy Blocked:</strong> Cannot dismiss this finding.
                  </div>
                )}

                {finding.status === 'accepted' ? (
                  <div className="flex items-center gap-2 text-success text-sm bg-success/10 p-3 rounded-lg border border-success/20">
                    <ShieldCheck className="w-5 h-5" />
                    Fix accepted and GitHub Issue created.
                  </div>
                ) : (
                  <div className="flex gap-3 mt-6 print:hidden">
                    <button 
                      onClick={() => handleAction(finding.id, 'accepted')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
                    >
                      <Check className="w-4 h-4" /> Accept
                    </button>
                    <button 
                      onClick={() => alert("Edit fix dialog coming soon.")}
                      className="bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
                    >
                      <Edit2 className="w-4 h-4" /> Edit
                    </button>
                    <button 
                      onClick={() => handleAction(finding.id, 'dismissed')}
                      disabled={finding.armoriq_policy_blocked}
                      className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors ${finding.armoriq_policy_blocked ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-slate-600 hover:bg-slate-500 text-white'}`}
                    >
                      <X className="w-4 h-4" /> Dismiss
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
