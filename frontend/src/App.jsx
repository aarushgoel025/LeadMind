import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import ScanProgress from './pages/ScanProgress';
import Report from './pages/Report';
import AuditTrail from './pages/AuditTrail';
import { Shield } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col">
        <header className="bg-surface border-b border-border py-4 px-6 flex justify-between items-center">
          <Link to="/" className="flex items-center gap-2 text-xl font-bold text-text-primary">
            <Shield className="text-armorclaw-accent w-6 h-6" />
            LeadMind
          </Link>
          <nav className="flex items-center gap-4 text-sm font-medium">
            <Link to="/dashboard" className="text-text-secondary hover:text-text-primary transition-colors">Dashboard</Link>
            <Link to="/audit" className="text-text-secondary hover:text-text-primary transition-colors">Audit Trail</Link>
          </nav>
        </header>

        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/scan/:id/progress" element={<ScanProgress />} />
            <Route path="/scan/:id/report" element={<Report />} />
            <Route path="/audit" element={<AuditTrail />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
