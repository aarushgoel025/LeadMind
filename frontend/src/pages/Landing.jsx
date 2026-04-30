import { ShieldCheck, BrainCircuit, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function GithubIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-73px)] p-6">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 text-text-primary">
          Secure by <span className="text-armorclaw-accent">Default</span>
        </h1>
        <p className="text-xl text-text-secondary mb-10 leading-relaxed">
          AI-powered security and code quality audit tool for tech leads.
        </p>
        <button
          onClick={() => {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            window.location.href = `${API_URL}/auth/github`;
          }}
          className="bg-text-primary text-background font-bold py-3 px-8 rounded-lg flex items-center gap-3 mx-auto hover:bg-opacity-90 transition-all text-lg"
        >
          <GithubIcon className="w-6 h-6" />
          Connect with GitHub
        </button>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto w-full mb-16">
        <div className="bg-surface-elevated p-8 rounded-xl border border-border">
          <ShieldCheck className="w-12 h-12 text-armorclaw-accent mb-6" />
          <h3 className="text-xl font-bold mb-3">ArmorClaw Scanning</h3>
          <p className="text-text-secondary">Automatically detect secrets, injections, and vulnerable dependencies with industry-grade static analysis.</p>
        </div>
        <div className="bg-surface-elevated p-8 rounded-xl border border-border">
          <BrainCircuit className="w-12 h-12 text-suggestion mb-6" />
          <h3 className="text-xl font-bold mb-3">AI Code Analysis</h3>
          <p className="text-text-secondary">Gemini 2.5 Flash analyzes logic errors, performance bottlenecks, and generates actionable fixes.</p>
        </div>
        <div className="bg-surface-elevated p-8 rounded-xl border border-border">
          <Users className="w-12 h-12 text-armoriq-accent mb-6" />
          <h3 className="text-xl font-bold mb-3">Human-in-the-Loop</h3>
          <p className="text-text-secondary">Nothing touches the repo without explicit human approval. Full audit logging via ArmorIQ SDK.</p>
        </div>
      </div>

      <footer className="mt-auto text-sm text-text-secondary text-center">
        Your code is never stored. All analysis runs in isolated containers.
      </footer>
    </div>
  );
}
