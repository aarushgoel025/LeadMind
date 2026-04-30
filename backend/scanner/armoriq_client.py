"""
ArmorIQ Client — realistic mock that enforces policy logic.

Interface is designed so that when real ArmorIQ credentials are available,
you only replace the method bodies here. All callers remain unchanged.
"""
import os
import uuid
from datetime import datetime, timezone


# Rules that can never be dismissed per organizational policy
POLICY_BLOCK_RULE_IDS = {
    "HARDCODED_SECRET", "SQL_INJECTION", "B105", "B106", "B107",  # Bandit hardcoded password rules
    "B608",  # Bandit SQL injection
}

POLICY_BLOCK_TITLE_KEYWORDS = {
    "secret", "injection", "hardcoded", "sql", "credentials", "api key", "password"
}


class ArmorIQClient:
    """
    Simulates the ArmorIQ SDK.
    Policy enforcement is real: certain finding types are always blocked.
    Audit log IDs are generated deterministically for traceability.
    """

    def __init__(self):
        self.org_id = os.getenv("ARMORIQ_ORG_ID", "leadmind_default_org")
        self.api_key = os.getenv("ARMORIQ_API_KEY", "mock_key")

    def _is_policy_blocked(self, rule_id: str | None, title: str, severity: str) -> bool:
        """Determine if a finding is policy-blocked (cannot be dismissed)."""
        if rule_id and rule_id in POLICY_BLOCK_RULE_IDS:
            return True
        title_lower = title.lower()
        for keyword in POLICY_BLOCK_TITLE_KEYWORDS:
            if keyword in title_lower:
                return True
        return False

    def verify_intent(
        self,
        finding_id: str,
        code_snippet: str,
        rule_violated: str,
        severity: str,
        rule_id: str | None = None,
    ) -> dict:
        """
        Verify whether a critical finding is intentional or a real issue.
        Returns whether the finding is policy-blocked (cannot be dismissed).

        Real ArmorIQ would send this to their API for ML-based verification.
        """
        blocked = self._is_policy_blocked(rule_id, rule_violated, severity)

        return {
            "verified": True,
            "policy_blocked": blocked,
            "reason": (
                f"Organization policy: '{rule_violated}' findings of {severity} severity "
                "cannot be dismissed without security team approval."
            ) if blocked else "Finding can be reviewed and dismissed by the tech lead.",
            "armoriq_check_id": f"chk_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def log_decision(
        self,
        scan_id: str,
        finding_id: str,
        action: str,
        decided_by: str,
        finding_title: str,
        severity: str,
        edited_fix: str | None = None,
    ) -> dict:
        """
        Log a tech lead decision to the ArmorIQ audit trail.
        Returns a unique, traceable audit log ID.

        Real ArmorIQ would POST this to their API and return a permanent record.
        """
        audit_id = f"ariq_{uuid.uuid4().hex}"

        # In production: requests.post("https://api.armoriq.com/v1/audit", json={...}, headers={"X-API-Key": self.api_key})
        print(
            f"[ArmorIQ Audit] org={self.org_id} | scan={scan_id[:8]} | "
            f"finding={finding_id[:8]} | action={action} | by={decided_by} | "
            f"title='{finding_title}' | severity={severity} | audit_id={audit_id}"
        )

        return {
            "audit_log_id": audit_id,
            "org_id": self.org_id,
            "scan_id": scan_id,
            "finding_id": finding_id,
            "action": action,
            "decided_by": decided_by,
            "finding_title": finding_title,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "logged",
        }


# Singleton — imported by all routers
armoriq = ArmorIQClient()
