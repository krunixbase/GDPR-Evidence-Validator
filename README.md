# GDPR Evidence Validator

GDPR Evidence Validator is an offline compliance validation tool designed to assess the availability and completeness of key GDPR evidence artifacts.  
It enables security, compliance, and privacy teams to quickly verify whether required GDPR documentation exists and is audit‑ready, without relying on live system integrations.

The validator operates on structured evidence files and generates a professional, client‑ready HTML report summarizing findings, gaps, and recommendations aligned with GDPR requirements.

---

## Key Features

- Validates the presence of mandatory GDPR evidence artifacts
- Maps evidence to relevant GDPR Articles
- Identifies missing or incomplete compliance documentation
- Generates a structured, audit‑ready HTML report
- Operates fully offline on provided evidence files
- Designed for consulting, internal audits, and readiness assessments

---

## Evidence Scope

The validator evaluates evidence related to:

- Records of Processing Activities (Article 30)
- Privacy notices and transparency documentation (Articles 12–14)
- Data Protection Impact Assessments (Article 35)
- Data Subject Rights handling and response timelines (Articles 15–22)
- Personal data breach logging and notification readiness (Articles 33–34)

---

## Repository Structure

gdpr-evidence-validator/
├── validate.py
├── report_template.html
├── report.html
├── controls.json
├── examples/
│   └── evidence/
│       ├── processing_register.csv
│       ├── privacy_policy.pdf
│       ├── dpia/
│       │   └── dpia_customer_data.pdf
│       ├── data_subject_requests/
│       │   └── dsr_log.csv
│       └── breach_log.csv
└── README.md
