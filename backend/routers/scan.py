"""
Scan router — contains the full async pipeline:
POST /scan          → start scan
GET  /scan/{id}     → poll status + progress
GET  /scan/{id}/report → full report with findings
GET  /scans/history → all past scans
POST /finding/{id}/decide → accept/edit/dismiss with ArmorIQ + GitHub Issue
GET  /audit-trail   → all decisions
"""
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from github import Github, GithubException

from database import get_db
from models import Scan, Finding, Decision
from routers.auth import require_auth
from scanner.fetcher import fetch_repo_files
from scanner.armorclaw_adapter import run_armorclaw_scan
from scanner.gemini_analyzer import analyze_with_gemini
from scanner.armoriq_client import armoriq

router = APIRouter(tags=["scans"])


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    repo_full_name: str


class DecisionRequest(BaseModel):
    action: str          # accepted | edited | dismissed
    edited_fix: Optional[str] = None


# ─── Health score ──────────────────────────────────────────────────────────────

def calculate_health_score(findings: list) -> float:
    score = 100.0
    for f in findings:
        if f["severity"] == "critical":
            score -= 15
        elif f["severity"] == "warning":
            score -= 5
        elif f["severity"] == "suggestion":
            score -= 1
    return max(0.0, round(score, 1))


# ─── GitHub Issue creation ─────────────────────────────────────────────────────

def create_github_issue(
    repo_full_name: str,
    token: str,
    finding: Finding,
    fix: str,
    audit_log_id: str,
    decided_by: str,
) -> Optional[str]:
    try:
        g = Github(token)
        repo = g.get_repo(repo_full_name)

        body = f"""## Security Finding — {finding.severity.upper()}

**File:** `{finding.file_path}` (Lines {finding.line_start}–{finding.line_end})

**Issue:** {finding.explanation}

**Suggested Fix:**
```
{fix}
```

**Detected by:** {finding.source}
**Confidence:** {int(finding.confidence * 100)}%
**ArmorIQ Audit ID:** `{audit_log_id}`

*Approved by {decided_by} via LeadMind*
"""
        labels_to_create = ["leadmind", finding.severity, finding.category]
        existing_labels = {l.name for l in repo.get_labels()}

        label_objs = []
        color_map = {"critical": "EF4444", "warning": "F59E0B", "suggestion": "3B82F6",
                     "security": "8B5CF6", "bug": "EF4444", "quality": "06B6D4",
                     "performance": "10B981", "leadmind": "1A1D27"}

        for lname in labels_to_create:
            if lname not in existing_labels:
                try:
                    repo.create_label(name=lname, color=color_map.get(lname, "AAAAAA"))
                except GithubException:
                    pass
            try:
                label_objs.append(repo.get_label(lname))
            except GithubException:
                pass

        issue = repo.create_issue(
            title=f"[LeadMind] {finding.title}",
            body=body,
            labels=label_objs,
        )
        return issue.html_url
    except Exception as e:
        print(f"[GitHub Issue] Failed to create issue: {e}")
        return None


# ─── Background scan pipeline ──────────────────────────────────────────────────

async def run_full_pipeline(scan_id: str, repo_full_name: str, token: str):
    """Full async scan pipeline that runs as a background task."""
    from database import SessionLocal
    db = SessionLocal()

    def update(status: str = "running", progress: int = 0, message: str = ""):
        scan = db.get(Scan, scan_id)
        if scan:
            scan.status = status
            scan.progress = progress
            scan.status_message = message
            db.commit()

    try:
        update(progress=5, message="Fetching repository files...")

        # Step 1: Fetch files
        try:
            files = fetch_repo_files(repo_full_name, token)
        except Exception as e:
            update("failed", 0, f"Failed to fetch repository: {str(e)[:120]}")
            return

        scan = db.get(Scan, scan_id)
        if scan:
            scan.total_files = len(files)
            db.commit()

        update(progress=20, message=f"Fetched {len(files)} files. Running ArmorClaw security scan...")

        # Step 2: ArmorClaw (static analysis)
        armorclaw_findings_raw = []
        try:
            armorclaw_findings_raw = run_armorclaw_scan(files)
        except Exception as e:
            print(f"[ArmorClaw] Scan failed: {e}. Continuing with Gemini only.")

        update(progress=45, message=f"ArmorClaw complete ({len(armorclaw_findings_raw)} findings). Analyzing with Gemini AI...")

        # Step 3: Gemini analysis
        gemini_findings_raw = []
        try:
            gemini_findings_raw = await analyze_with_gemini(files)
        except Exception as e:
            print(f"[Gemini] Analysis failed: {e}. Continuing with ArmorClaw results only.")

        update(progress=70, message=f"Gemini complete ({len(gemini_findings_raw)} findings). Verifying critical findings with ArmorIQ...")

        # Step 4: ArmorIQ intent verification for critical findings
        all_raw = armorclaw_findings_raw + gemini_findings_raw
        db_findings = []

        for raw in all_raw:
            policy_blocked = False
            intent_verified = False

            if raw["severity"] == "critical":
                try:
                    result = armoriq.verify_intent(
                        finding_id=raw["id"],
                        code_snippet=raw.get("suggested_fix", ""),
                        rule_violated=raw["title"],
                        severity=raw["severity"],
                        rule_id=raw.get("armorclaw_rule_id"),
                    )
                    policy_blocked = result["policy_blocked"]
                    intent_verified = result["verified"]
                except Exception as e:
                    print(f"[ArmorIQ] verify_intent failed: {e}")

            f = Finding(
                id=raw["id"],
                scan_id=scan_id,
                severity=raw["severity"],
                category=raw["category"],
                file_path=raw["file_path"],
                line_start=raw["line_start"],
                line_end=raw["line_end"],
                title=raw["title"],
                explanation=raw["explanation"],
                suggested_fix=raw.get("suggested_fix", ""),
                confidence=raw["confidence"],
                source=raw["source"],
                armorclaw_rule_id=raw.get("armorclaw_rule_id"),
                armoriq_intent_verified=intent_verified,
                armoriq_policy_blocked=policy_blocked,
                status="pending",
            )
            db.add(f)
            db_findings.append(raw)

        db.commit()
        update(progress=85, message="Calculating health score...")

        # Step 5: Health score
        health_score = calculate_health_score(all_raw)

        scan = db.get(Scan, scan_id)
        if scan:
            scan.health_score = health_score
            scan.status = "complete"
            scan.progress = 100
            scan.status_message = "Report ready!"
            db.commit()

    except Exception as e:
        print(f"[Pipeline] Unexpected error: {e}")
        update("failed", 0, f"Scan failed: {str(e)[:120]}")
    finally:
        db.close()


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.post("/scan")
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    repo_name = request.repo_full_name
    scan = Scan(
        repo_full_name=repo_name,
        repo_url=f"https://github.com/{repo_name}",
        scanned_by=current_user["login"],
        status="pending",
        progress=0,
        status_message="Scan queued...",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(
        run_full_pipeline,
        scan_id=scan.id,
        repo_full_name=repo_name,
        token=current_user["token"],
    )
    return {"scan_id": scan.id}


@router.get("/scan/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db), current_user: dict = Depends(require_auth)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return {
        "id": scan.id,
        "repo_full_name": scan.repo_full_name,
        "status": scan.status,
        "progress": scan.progress,
        "status_message": scan.status_message,
        "health_score": scan.health_score,
        "total_files": scan.total_files,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
    }


@router.get("/scan/{scan_id}/report")
def get_report(scan_id: str, db: Session = Depends(get_db), current_user: dict = Depends(require_auth)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.status != "complete":
        raise HTTPException(400, f"Scan is not complete yet (status: {scan.status})")

    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

    return {
        "scan": {
            "id": scan.id,
            "repo_full_name": scan.repo_full_name,
            "health_score": scan.health_score,
            "total_files": scan.total_files,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            "scanned_by": scan.scanned_by,
        },
        "findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "category": f.category,
                "file_path": f.file_path,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "title": f.title,
                "explanation": f.explanation,
                "suggested_fix": f.suggested_fix,
                "confidence": f.confidence,
                "source": f.source,
                "status": f.status,
                "armoriq_policy_blocked": f.armoriq_policy_blocked,
                "armoriq_intent_verified": f.armoriq_intent_verified,
            }
            for f in sorted(findings, key=lambda x: {"critical": 0, "warning": 1, "suggestion": 2}[x.severity])
        ],
        "summary": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.severity == "critical"),
            "warning": sum(1 for f in findings if f.severity == "warning"),
            "suggestion": sum(1 for f in findings if f.severity == "suggestion"),
            "armorclaw": sum(1 for f in findings if f.source == "armorclaw"),
            "gemini": sum(1 for f in findings if f.source == "gemini"),
            "policy_blocked": sum(1 for f in findings if f.armoriq_policy_blocked),
        }
    }


@router.get("/scans/history")
def scan_history(db: Session = Depends(get_db), current_user: dict = Depends(require_auth)):
    scans = (
        db.query(Scan)
        .filter(Scan.scanned_by == current_user["login"])
        .order_by(Scan.scanned_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": s.id,
            "repo_full_name": s.repo_full_name,
            "status": s.status,
            "health_score": s.health_score,
            "total_files": s.total_files,
            "scanned_at": s.scanned_at.isoformat() if s.scanned_at else None,
            "findings_count": len(s.findings),
        }
        for s in scans
    ]


@router.post("/finding/{finding_id}/decide")
def make_decision(
    finding_id: str,
    request: DecisionRequest,
    req: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, "Finding not found")

    # Guard 1: Policy block check
    if finding.armoriq_policy_blocked and request.action == "dismissed":
        raise HTTPException(
            403,
            "Policy violation: this finding cannot be dismissed. "
            "It requires remediation per organizational security policy."
        )

    # Guard 2: Log to ArmorIQ (if unavailable, block the action)
    try:
        audit = armoriq.log_decision(
            scan_id=finding.scan_id,
            finding_id=finding_id,
            action=request.action,
            decided_by=current_user["login"],
            finding_title=finding.title,
            severity=finding.severity,
            edited_fix=request.edited_fix,
        )
    except Exception as e:
        raise HTTPException(
            503,
            f"Audit logging unavailable. Cannot process decision. ({e})"
        )

    audit_log_id = audit["audit_log_id"]

    # Guard 3: Create GitHub Issue if accepted or edited
    github_url = None
    if request.action in ("accepted", "edited"):
        fix = request.edited_fix or finding.suggested_fix or "Review and fix this issue."
        github_url = create_github_issue(
            repo_full_name=finding.scan.repo_full_name,
            token=current_user["token"],
            finding=finding,
            fix=fix,
            audit_log_id=audit_log_id,
            decided_by=current_user["login"],
        )

    # Update finding status
    finding.status = request.action
    db.add(finding)

    # Save decision record
    decision = Decision(
        finding_id=finding_id,
        scan_id=finding.scan_id,
        action=request.action,
        edited_fix=request.edited_fix,
        decided_by=current_user["login"],
        decided_at=datetime.now(timezone.utc),
        armoriq_audit_log_id=audit_log_id,
        github_issue_url=github_url,
    )
    db.add(decision)
    db.commit()

    return {
        "armoriq_audit_id": audit_log_id,
        "github_issue_url": github_url,
        "action": request.action,
    }


@router.get("/audit-trail")
def audit_trail(db: Session = Depends(get_db), current_user: dict = Depends(require_auth)):
    decisions = (
        db.query(Decision)
        .filter(Decision.decided_by == current_user["login"])
        .order_by(Decision.decided_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": d.id,
            "repo_full_name": d.scan.repo_full_name if d.scan else "—",
            "finding_title": d.finding.title if d.finding else "—",
            "severity": d.finding.severity if d.finding else "—",
            "action": d.action,
            "decided_by": d.decided_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "armoriq_audit_log_id": d.armoriq_audit_log_id,
            "github_issue_url": d.github_issue_url,
        }
        for d in decisions
    ]
