import argparse
import datetime as dt
import html
import json
from pathlib import Path


# ----------------------------
# Helpers
# ----------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_csv_rows(csv_path: Path) -> list[dict]:
    """
    Very small CSV reader (no external deps). Assumes:
    - UTF-8
    - header in first line
    - comma-separated
    - no quoted commas (sufficient for demo evidence)
    """
    if not csv_path.exists():
        return []

    lines = [ln.strip() for ln in read_text(csv_path).splitlines() if ln.strip()]
    if len(lines) < 2:
        return []

    headers = [h.strip() for h in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        cols = [c.strip() for c in ln.split(",")]
        row = {headers[i]: (cols[i] if i < len(cols) else "") for i in range(len(headers))}
        rows.append(row)
    return rows


def status_class(status_text: str) -> str:
    """
    CSS class used in template; keep these consistent with your HTML styles.
    """
    if status_text.lower() == "present":
        return "ok"
    if status_text.lower() == "missing":
        return "critical"
    return "warning"


def make_li(items: list[str]) -> str:
    return "\n".join(f"<li>{html.escape(x)}</li>" for x in items)


# ----------------------------
# Validation logic
# ----------------------------

def validate_evidence(evidence_dir: Path) -> dict:
    """
    Returns a dict with:
    - statuses per evidence area
    - findings + recommendations
    - computed compliance level
    """
    findings: list[dict] = []
    observations: list[str] = []
    recommendations: list[str] = []

    # Evidence paths
    processing_register = evidence_dir / "processing_register.csv"
    privacy_policy = evidence_dir / "privacy_policy.pdf"
    dpia_dir = evidence_dir / "dpia"
    dsr_log = evidence_dir / "data_subject_requests" / "dsr_log.csv"
    breach_log = evidence_dir / "breach_log.csv"

    # ----------------------------
    # Art. 30 – RoPA
    # ----------------------------
    ropa_rows = load_csv_rows(processing_register)
    if processing_register.exists() and len(ropa_rows) > 0:
        ropa_status = "Present"
        observations.append(f"Record of Processing Activities exists ({len(ropa_rows)} entries).")
    else:
        ropa_status = "Missing"
        findings.append({
            "severity": "Critical",
            "title": "Missing Record of Processing Activities (Article 30)",
            "detail": "No processing register was found, or it contains no entries."
        })
        recommendations.append("Create and maintain a Record of Processing Activities (RoPA) aligned to Article 30.")

    # ----------------------------
    # Arts. 12–14 – Privacy notice / transparency
    # ----------------------------
    if privacy_policy.exists() and privacy_policy.stat().st_size > 0:
        privacy_status = "Present"
        observations.append("Privacy policy documentation is available.")
    else:
        privacy_status = "Missing"
        findings.append({
            "severity": "High",
            "title": "Missing privacy policy / transparency documentation (Articles 12–14)",
            "detail": "No privacy policy PDF was found in the expected location."
        })
        recommendations.append("Publish and maintain an up-to-date privacy notice covering Articles 12–14 requirements.")

    # ----------------------------
    # Art. 35 – DPIA (presence-based)
    # ----------------------------
    dpia_pdfs = []
    if dpia_dir.exists() and dpia_dir.is_dir():
        dpia_pdfs = sorted([p for p in dpia_dir.glob("*.pdf") if p.is_file() and p.stat().st_size > 0])

    if dpia_pdfs:
        dpia_status = "Present"
        observations.append(f"DPIA evidence exists ({len(dpia_pdfs)} PDF file(s)).")
    else:
        # Not always mandatory, but for a readiness validator we treat it as a gap unless explicitly out of scope.
        dpia_status = "Missing"
        findings.append({
            "severity": "Medium",
            "title": "No DPIA evidence found (Article 35)",
            "detail": "No DPIA PDF files were found. If high-risk processing occurs, DPIA is typically required."
        })
        recommendations.append("Confirm whether DPIA is required; if yes, create DPIA documentation for relevant processing.")

    # ----------------------------
    # Arts. 15–22 – Data Subject Requests (SLA check)
    # ----------------------------
    dsr_rows = load_csv_rows(dsr_log)
    dsr_over_30 = []
    if dsr_log.exists() and len(dsr_rows) > 0:
        # Expect columns: request_id,type,status,response_days
        for r in dsr_rows:
            rid = r.get("request_id", "").strip() or "UNKNOWN"
            try:
                days = int((r.get("response_days") or "").strip())
                if days > 30:
                    dsr_over_30.append((rid, days))
            except Exception:
                # malformed rows are a quality finding
                dsr_over_30.append((rid, None))

        if dsr_over_30:
            dsr_status = "Warning"
            findings.append({
                "severity": "Medium",
                "title": "Potential DSR response timeline gaps (Articles 15–22)",
                "detail": "One or more requests show response time issues or malformed response_days values."
            })
            recommendations.append("Ensure DSR tracking includes accurate response timelines and stays within statutory deadlines.")
            observations.append(f"DSR log exists ({len(dsr_rows)} entries) with timeline exceptions.")
        else:
            dsr_status = "Present"
            observations.append(f"DSR log exists ({len(dsr_rows)} entries) with response timelines within 30 days.")
    else:
        dsr_status = "Missing"
        findings.append({
            "severity": "High",
            "title": "Missing Data Subject Requests log (Articles 15–22)",
            "detail": "No DSR log was found, or it contains no entries."
        })
        recommendations.append("Maintain a DSR log tracking request type, status, and response timelines.")

    # ----------------------------
    # Arts. 33–34 – Breach log (presence-based)
    # ----------------------------
    breach_rows = load_csv_rows(breach_log)
    if breach_log.exists() and (len(breach_rows) > 0 or breach_log.stat().st_size > 0):
        breach_status = "Present"
        # If CSV exists but has no rows, still ok (might mean no incidents); we treat as present.
        observations.append("Breach log is available.")
    else:
        breach_status = "Missing"
        findings.append({
            "severity": "High",
            "title": "Missing personal data breach log (Articles 33–34)",
            "detail": "No breach log was found in the expected location."
        })
        recommendations.append("Maintain a breach log and document notification decision-making for Articles 33–34.")

    # ----------------------------
    # Findings counts + compliance level
    # ----------------------------
    total_findings = len(findings)
    critical_findings = sum(1 for f in findings if f["severity"].lower() == "critical")

    if critical_findings > 0:
        compliance_level = "low"
    elif total_findings >= 3:
        compliance_level = "moderate"
    elif total_findings in (1, 2):
        compliance_level = "good"
    else:
        compliance_level = "good"

    return {
        "processing_register_status": ropa_status,
        "privacy_policy_status": privacy_status,
        "dpia_status": dpia_status,
        "dsr_status": dsr_status,
        "breach_status": breach_status,
        "total_findings": total_findings,
        "critical_findings": critical_findings,
        "compliance_level": compliance_level,
        "findings": findings,
        "observations": observations,
        "recommendations": recommendations,
    }


# ----------------------------
# Report rendering
# ----------------------------

def render_report(template_html: str, context: dict) -> str:
    # Build observations/recommendations HTML
    obs_html = make_li(context.get("observations", []))

    # Findings -> include detail lines in observations for readability
    findings = context.get("findings", [])
    if findings:
        findings_lines = []
        for f in findings:
            title = f"{f.get('severity', 'Finding')}: {f.get('title', '')}"
            detail = f.get("detail", "")
            if detail:
                findings_lines.append(f"{title} — {detail}")
            else:
                findings_lines.append(title)
        obs_html = obs_html + ("\n" if obs_html else "") + make_li(findings_lines)

    rec_html = make_li(context.get("recommendations", []))

    # Replace placeholders (simple {{ key }} style)
    replacements = {
        "assessment_date": context["assessment_date"],
        "processing_register_status": context["processing_register_status"],
        "privacy_policy_status": context["privacy_policy_status"],
        "dpia_status": context["dpia_status"],
        "dsr_status": context["dsr_status"],
        "breach_status": context["breach_status"],
        "total_findings": str(context["total_findings"]),
        "critical_findings": str(context["critical_findings"]),
        "observations": obs_html,
        "recommendations": rec_html,
        "compliance_level": context["compliance_level"],
    }

    out = template_html
    for k, v in replacements.items():
        out = out.replace(f"{{{{ {k} }}}}", v)
        out = out.replace(f"{{{{{k}}}}}", v)  # allow {{key}} too

    # Also swap CSS classes if template uses class="{{ x_status }}"
    out = out.replace('class="{{ processing_register_status }}"', f'class="{status_class(context["processing_register_status"])}"')
    out = out.replace('class="{{ privacy_policy_status }}"', f'class="{status_class(context["privacy_policy_status"])}"')
    out = out.replace('class="{{ dpia_status }}"', f'class="{status_class(context["dpia_status"])}"')
    out = out.replace('class="{{ dsr_status }}"', f'class="{status_class(context["dsr_status"])}"')
    out = out.replace('class="{{ breach_status }}"', f'class="{status_class(context["breach_status"])}"')

    return out


# ----------------------------
# CLI
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="GDPR Evidence Validator (offline, evidence-driven).")
    parser.add_argument("--input", required=True, help="Path to evidence directory (e.g., examples/evidence).")
    parser.add_argument("--output", required=True, help="Path to output HTML report (e.g., report.html).")
    parser.add_argument("--template", default="report_template.html", help="Path to HTML template.")
    parser.add_argument("--controls", default="controls.json", help="Optional controls mapping JSON (not required).")
    args = parser.parse_args()

    evidence_dir = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    template_path = Path(args.template).resolve()
    controls_path = Path(args.controls).resolve()

    if not evidence_dir.exists() or not evidence_dir.is_dir():
        raise SystemExit(f"Evidence directory not found: {evidence_dir}")

    if not template_path.exists():
        raise SystemExit(f"Template not found: {template_path}")

    # Load template
    template_html = read_text(template_path)

    # Controls are optional; kept for repo completeness and future expansion
    if controls_path.exists():
        try:
            _ = json.loads(read_text(controls_path))
        except Exception:
            # Don't block report generation for demo repos
            pass

    # Validate + render
    results = validate_evidence(evidence_dir)
    context = {
        **results,
        "assessment_date": dt.date.today().isoformat(),
    }

    report_html = render_report(template_html, context)
    write_text(output_path, report_html)

    print(f"Report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

