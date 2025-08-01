from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch

# Updated markdown content with 'Validate' column
md_text = """# Cluster Storage - Vendor Security Assessment Checklist

- Date: 2025-0730
- Version: 1.1

## Network Security

| Management Backend | Service Frontend | Requirement | Level | Validate | Weight |
| ------------------ | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| TRUE | FALSE | The management plane **MUST** support management interfacing through a different network interface than the storage endpoints servicing customers. | MUST |  | |
| TRUE | FALSE | The management plane **MUST** support TLS 1.2, and **MUST** block unencrypted communication. | MUST |  | |
| TRUE | FALSE | The management plane **SHOULD** support TLS 1.3. | SHOULD |  | |
| TRUE | TRUE | The management interface **SHOULD** support blocking SSH access. | SHOULD |  | |
| TRUE | TRUE | The service **SHOULD** support external, valid SSL certificate. | SHOULD |  | |
| FALSE | TRUE | The service **MUST** support Kerberos Authentication for NFS (krb5p specifically) that includes authentication and encrypts all traffic between the storage system and the target server. | MUST |  | |


## Access Control

| Management Backend | Service Frontend | Requirement | Level | Validate | Weight |
| ------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| TRUE | TRUE | Access **MUST** support an external, different identity provider for the management backend vs. the servicing endpoints. | MUST |  | |
| FALSE | TRUE | Access **SHOULD** support multiple different identity providers for the storage-servicing endpoints. | SHOULD |  | |
| TRUE | TRUE | The system **SHOULD** support MFA for local accounts (in cases where federation is not done). | SHOULD |  | |
| TRUE | TRUE | Configuration **MUST** support role-based access control on the principle of least privilege for management interface, provisioned volumes, and S3-compatible object storage (bucket/object-level actions, CRUD granularity, segmented permissions, etc.). | MUST |  | |
| FALSE | TRUE | The system **SHOULD** support any amount of clientIDs and secrets for object storage (e.g., a single bucket may have 15 different access IDs/secrets). | SHOULD |  | |
| FALSE | TRUE | The system **MUST** support least-privilege object-storage access down to the object level (e.g., granular folder/file permissions and scoped create/list/read/change rights). | MUST |  | |
| TRUE | TRUE | For local users, the system **MUST** enforce complex password policies (≥ 12 chars, upper/lower/number/special, history ≥ 20, 90-day rotation, 5-try lockout, etc.). | MUST |  | |
| TRUE | TRUE | For local users, the system **SHOULD** enforce additional password policies (vendor/common-password dictionaries, custom dictionary, etc.). | SHOULD |  | |
| TRUE | FALSE | The management plane **MUST** support configurable web-session time-outs. | MUST |  | |
| TRUE | TRUE | The service **SHOULD** expose RESTful APIs for management, monitoring, and data operations (CRUD). | MUST |  | |
| FALSE | TRUE | While using Object Storage, the service **MUST** authenticate the user for **each** request. | MUST |  | |
| FALSE | TRUE | The service **MUST** authorize **every** request across Object Storage and NFS. | MUST |  | |


## Logging & Auditing

| Management Backend | Service Frontend | Requirement | Level | Validate | Weight |
| ------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| TRUE | TRUE | The service **MUST** log every user interaction (timestamp, user, action, resource, outcome). | MUST |  | |
| TRUE | TRUE | The service **MUST** log both successful **and** failed attempts. | MUST |  | |
| TRUE | TRUE | The service **MUST** store logs locally for at least 7 days. | MUST |  | |
| TRUE | TRUE | The service **MUST** send logs via Syslog to a central logging system. | MUST |  | |
| FALSE | TRUE | Customer audit trail **SHOULD** support routing event logs to separate object stores per definition (e.g., volume-based bucket targets). | SHOULD |  | |


## Data Security

| Management Backend | Service Frontend | Requirement | Level | Validate | Weight |
| ------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| TRUE | FALSE | The management plane **MUST** integrate with an external encryption-key management system. | MUST |  | |
| FALSE | TRUE | Key exchange and lifecycle management **MUST** use the KMIP protocol. | MUST |  | |
| TRUE | TRUE | The service **MUST NOT** allow export of encryption keys. | MUST |  | |
| FALSE | TRUE | The service **SHOULD** support file/versioning on both Volumes and Object Storage. | SHOULD |  | |
| FALSE | TRUE | The service **MUST** support different encryption keys per volume and/or per bucket. | MUST |  | |
| FALSE | TRUE | The service **SHOULD** support client-side encryption (similar to S3). | SHOULD |  | |
| FALSE | TRUE | The system **SHOULD** implement a hierarchical key model (Master → Customer → Tenant → Project → Data Key) and may offer BYOK; Data Keys **SHOULD** be at least per volume/bucket. | SHOULD |  | |
"""

# Write markdown to file
md_path = "/mnt/data/cluster_storage_vendor_security_checklist_validate.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write(md_text)


# Helper to parse markdown into sections with tables
def parse_md(md_lines):
    sections = []
    i = 0
    while i < len(md_lines):
        line = md_lines[i].strip()
        if line.startswith("## "):
            heading = line[3:].strip()
            i += 1
            while i < len(md_lines) and not md_lines[i].startswith("|"):
                i += 1
            if i >= len(md_lines):
                break
            header_line = md_lines[i]
            separator_line = md_lines[i + 1] if i + 1 < len(md_lines) else ""
            i += 2
            rows = [header_line]
            while i < len(md_lines) and md_lines[i].startswith("|"):
                rows.append(md_lines[i])
                i += 1
            sections.append((heading, rows))
        else:
            i += 1
    return sections


with open(md_path, "r", encoding="utf-8") as f:
    lines = [l.rstrip("\n") for l in f]

sections = parse_md(lines)

# Styles
styles = getSampleStyleSheet()
body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_LEFT)
header_style = ParagraphStyle('header', parent=styles['Normal'], fontSize=8, leading=10, alignment=TA_CENTER,
                              textColor=colors.white)

# Column widths
col_widths = [1.0 * inch, 1.0 * inch, 6.1 * inch, 0.7 * inch, 0.5 * inch, 0.5 * inch]

# Create PDF
pdf_path = "/mnt/data/cluster_storage_vendor_security_checklist_landscape_v1_1_validate.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36,
                        bottomMargin=36)
story = []

# Title and meta
story.append(Paragraph("<b>Cluster Storage - Vendor Security Assessment Checklist</b>", styles['Title']))
story.append(Spacer(1, 6))
story.append(Paragraph("• Date: 2025-0730<br/>• Version: 1.1", styles['Normal']))
story.append(Spacer(1, 12))

# Build tables
for heading, table_lines in sections:
    story.append(Paragraph(f"<b>{heading}</b>", styles['Heading2']))
    story.append(Spacer(1, 6))

    header_cells = [c.strip() for c in table_lines[0].strip('|').split('|')]
    data_rows = [[c.strip() for c in row.strip('|').split('|')] for row in table_lines[1:]]

    table_data = [[Paragraph(cell, header_style) for cell in header_cells]]
    for row in data_rows:
        table_data.append([Paragraph(cell, body_style) for cell in row])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))

doc.build(story)

pdf_path
