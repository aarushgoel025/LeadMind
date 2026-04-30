# LeadMind: Secure by Default 🛡️

**LeadMind** is an AI-powered, Human-in-the-Loop security and code quality auditing platform designed for tech leads. Powered by **ArmorClaw** for blazing-fast static security analysis and the **ArmorIQ SDK** for strict organizational policy enforcement, LeadMind automatically analyzes GitHub repositories, detects critical vulnerabilities, and generates actionable fixes.

With LeadMind, security is no longer a bottleneck. It's an invisible, automated safety net built on top of the Armor ecosystem.

---

## 🌟 The "Human-in-the-Loop" Philosophy

In modern CI/CD pipelines, security tools often generate overwhelming noise, leading developers to ignore warnings or automatically bypass them. 

**LeadMind flips this model on its head by making security decisions explicit, verified, and heavily audited.**

*   **No Code Left Behind:** Automated scanners analyze every file, but *only humans* can decide the fate of a vulnerability.
*   **Intent Verification (Powered by ArmorIQ):** LeadMind integrates with the **ArmorIQ SDK** to enforce organizational policies. If a developer attempts to dismiss a `Critical` vulnerability (e.g., a hardcoded API key), ArmorIQ intercepts the request, verifies the user's intent against active security policies, and can outright block the dismissal if it violates compliance rules.
*   **Immutable Audit Trail:** Every decision—whether a fix is accepted or a warning is dismissed—is cryptographically logged. Compliance teams get a perfect, exportable CSV audit trail showing *who* made the decision, *when*, and the exact *ArmorIQ Audit ID*.
*   **Automated Action:** When a Tech Lead clicks "Accept" on a suggested fix, LeadMind doesn't just check a box. It automatically creates a formatted GitHub Issue in the repository containing the exact code snippet required to patch the vulnerability.

---

## 🏗️ Hybrid Architecture: How It Works

LeadMind uses a powerful two-pass analysis engine to guarantee both speed and deep semantic understanding.

### 1. Phase One: The ArmorClaw Engine (Static Analysis)
ArmorClaw acts as the rapid first line of defense. It parses Abstract Syntax Trees (AST) and uses deterministic pattern matching to find immediate threats.
*   **Python:** Uses industry-standard `Bandit` scanning.
*   **JavaScript/TypeScript:** Uses a custom, high-speed Regex engine to detect hardcoded secrets, SQL injections, insecure randomness (`Math.random()`), overly permissive CORS configurations, and dangerous execution (`eval()`).

### 2. Phase Two: Gemini AI (Semantic Logic Review)
Static scanners can't understand business logic. After ArmorClaw finishes, LeadMind chunks the code by function/class boundaries and passes it to **Gemini 2.5 Flash** via the Google GenAI SDK.
*   Gemini acts as a senior engineer doing a deep architectural review.
*   It detects unhandled promise rejections, race conditions, N+1 database bottlenecks, and complex logic flaws that a standard regex rule would completely miss.
*   It generates specific, contextual code fixes returned in a strict JSON format.

---

## 🚀 Quick Start Guide

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   A Gemini API Key
*   A GitHub OAuth App (Client ID & Secret)

### 1. Setup the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file in the `backend/` directory:
```env
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
FRONTEND_URL=http://localhost:3000
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///./test.db
```
Initialize the DB and start the server:
```bash
python init_db.py
uvicorn main:app --reload
```

### 2. Setup the Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Usage
1. Open `http://localhost:3000`.
2. Click **"Connect with GitHub"** to securely authenticate.
3. Select any of your repositories from the Dashboard and click **Scan**.
4. Watch the real-time background processing.
5. Review the final report, Accept/Dismiss findings, and check your **Audit Trail**.

---

## 🛠️ Tech Stack
*   **Frontend:** React, Vite, Tailwind CSS, Lucide Icons, Axios.
*   **Backend:** Python, FastAPI, SQLAlchemy, SQLite, PyGithub, Google GenAI SDK.
*   **Security:** ArmorClaw (Static), ArmorIQ (Intent/Policy SDK), Gemini (Logical Analysis).
