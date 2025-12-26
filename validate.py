import argparse
import datetime
from pathlib import Path

# -----------------------------
# Helpers
# -----------------------------

def read_csv_rows(path):
    if not path.exists():
        return []
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    headers = lines[0].split(",")
    rows = []
    for line in lines[1:]:
        values = line.split(",")
        rows.append(dict(zip(headers, values)))
    return rows


def li(items):
    return "\n".join(f"<li>{item}</li>" for item in items)


# -----------------------------
# Validation
# -----------------------------

def validate(evidence_dir):
    findings = []
    observations = []
    recommendations = []

    # Article 30
    ropa = evidence_dir / "processing_register.csv"
    ropa_rows = read_csv_rows(ropa)
    if ropa.exists() and ropa_rows:
        processing_register_status = "Present"
        observations.append(f"Record of Processing Activities exists ({len(ropa_rows)} entries).")
    else:
        processing_register_status = "Missing"
        findings.append("Missing Record of Processing Activities (Article 30).")
        recommendations.append("Create and maintain a Record of Processing Activities.")

    # Articles 12–14
    privacy = evidence_dir / "privacy_policy.pdf"
    if privacy.exists() and privacy.stat().st_size > 0:
        privacy_policy_status = "Present"
        observations.append("Privacy policy documentation is available.")
    else:
        privacy_policy_status = "Missing"
        findings.append("Missing privacy policy documentation (Articles 12–14).")
        recommendations.append("Publish and maintain a GDPR‑compliant privacy policy.")

    # Article 35
    dpia_dir = evidence_dir / "dpia"
    dpia_pdfs = list(dpia_dir.glob("*.pdf")) if dpia_dir.exists() else []
    if dpia_pdfs:
        dpia_status = "Present"
        observations.append("DPIA documentation is available.")
    else:
        dpia_status = "Missing"
        findings.append("No DPIA documentation found (Article 35).")
        recommendations.append("Assess DPIA applicability and document DPIAs where required.")

    # Articles 15–22
    dsr = evidence_dir / "data_subject_requests" / "dsr_log.csv"
    dsr_rows = read_csv_rows(dsr)
    late = []
    for r in dsr_rows:
        try:
            if int(r.get("response_days", 0)) > 30:
                late.append(r.get("request_id"))
        except:
            late.append(r.get("request_id"))

    if dsr.exists() and dsr_rows:
        if late:
            dsr_status = "Warning"
            findings.append("Some Data Subject Requests exceeded statutory timelines.")
            recommendations.append("Ensure DSR responses are completed within 30 days.")
        else:
            dsr_status = "Present"
            observations.append("Data Subject Requests are handled within statutory timelines.")
    else:
        dsr_status = "Missing"
        findings.append("No Data Subject Requests log found.")
        recommendations.append("Maintain a Data Subject Requests log.")

    # Articles 33–34
    breach = evidence_dir / "breach_log.csv"
    if breach.exists():
        breach_status = "Present"
        observations.append("Personal data breach log is maintained.")
    else:
        breach_status = "Missing"
        findings.append("No personal data breach log found.")
        recommendations.append("Maintain a personal data breach log.")

    total_findings = len(findings)
    critical_findings = sum(1 for f in findings if "Missing Record of Processing" in f)

    if critical_findings > 0:
        compliance_level = "low"
    elif total_findings > 2:
        compliance_level = "moderate"
    else:
        compliance_level = "good"

    return {
        "processing_register_status": processing_register_status,
        "privacy_policy_status": privacy_policy_status,
        "dpia_status": dpia_status,
        "dsr_status": dsr_status,
        "breach_status": breach_status,
        "total_findings": total_findings,
        "critical_findings": critical_findings,
        "observations": li(observations),
        "recommendations": li(recommendations),
        "compliance_level": compliance_level
    }


# -----------------------------
# Render
# -----------------------------

def render(template, context):
    html = template
    for key, value in context.items():
        html = html.replace(f"{{{{ {key} }}}}", str(value))
    return html


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    evidence_dir = Path(args.input)
    template = Path("report_template.html").read_text(encoding="utf-8")

    context = validate(evidence_dir)
    context["assessment_date"] = datetime.date.today().isoformat()

    report = render(template, context)
    Path(args.output).write_text(report, encoding="utf-8")

    print("Report generated:", args.output)


if __name__ == "__main__":
    main()
