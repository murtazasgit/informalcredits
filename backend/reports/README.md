# Module: Transparency Report (PDF)

## Goal
Generate a downloadable PDF that explains the Accept/Reject credit decision for a user —
this is a required output per the spec.

## Tech stack
**WeasyPrint** — write an HTML/CSS template, render to PDF. (Alternative: ReportLab if someone on
the team already knows it well — steeper learning curve otherwise.)

## Input (from `backend/api/`)
```json
{
  "user_id": "U1001",
  "total_score": 742,
  "risk_category": "Good",
  "decision": "Accept",
  "factors": [
    {"label": "On-time bill payments", "points": 15, "direction": "positive"}
  ],
  "recommended_products": [
    {"name": "Starter Credit Card", "interest_rate": 24.0}
  ]
}
```

## Output
A PDF file (bytes or saved path), e.g. `report_U1001.pdf`, downloadable via the API.

## Starter code
```python
from weasyprint import HTML
from jinja2 import Template

TEMPLATE = Template("""
<html><head><style>
  body { font-family: sans-serif; padding: 40px; }
  .score { font-size: 48px; color: {{ '#1a7f37' if decision == 'Accept' else '#c0392b' }}; }
  .factor { padding: 4px 0; }
</style></head>
<body>
  <h1>AltCredit Transparency Report</h1>
  <p>User: {{ user_id }}</p>
  <div class="score">{{ total_score }} / 1000 — {{ risk_category }}</div>
  <h2>Decision: {{ decision }}</h2>
  <h3>Factor Analysis</h3>
  {% for f in factors %}
    <div class="factor">{{ f.label }}: {{ '+' if f.points >= 0 else '' }}{{ f.points }} pts</div>
  {% endfor %}
  <h3>Recommended Products</h3>
  {% for p in recommended_products %}
    <div>{{ p.name }} — {{ p.interest_rate }}% interest</div>
  {% endfor %}
</body></html>
""")

def generate_report(data: dict, out_path: str):
    html_content = TEMPLATE.render(**data)
    HTML(string=html_content).write_pdf(out_path)
    return out_path
```

## Tasks checklist
- [ ] Build the Jinja2 HTML template (make it look clean — this is user-facing)
- [ ] Implement `generate_report(data, out_path) -> str`
- [ ] Wire a `/report/{user_id}` endpoint in `backend/api/` that returns the PDF as a file response

## Handoff
Expose `generate_report(data: dict, out_path: str) -> str` for `backend/api/`.
