"""Agentic flow diagram for the deck: user input -> reasoning -> tool calls -> external systems -> output, with the decision loop."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
import math

W, H = landscape(A4)
INK = colors.HexColor("#1f2937"); GREY = colors.HexColor("#6b7280"); EDGE = colors.HexColor("#4f46e5")
COL = {"in": colors.HexColor("#fff7ed"), "reason": colors.HexColor("#eef2ff"), "tool": colors.HexColor("#ecfdf5"), "ext": colors.HexColor("#f1f5f9"), "out": colors.HexColor("#fdf2f8")}
c = canvas.Canvas("flow.pdf", pagesize=landscape(A4))
c.setFillColor(INK); c.setFont("Helvetica-Bold", 16); c.drawString(30, H - 36, "GovEase agentic flow: one request, 12 autonomous tool calls, one consent gate")

def box(x, y, w, h, fill, lines, bold_first=True):
    c.setFillColor(fill); c.setStrokeColor(colors.HexColor("#c7d2fe")); c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
    c.setFillColor(INK)
    for i, t in enumerate(lines):
        c.setFont("Helvetica-Bold" if (i == 0 and bold_first) else "Helvetica", 9 if i == 0 else 8)
        c.drawCentredString(x + w / 2, y + h - 13 - i * 10.5, t)

def arrow(x1, y1, x2, y2, label="", dashed=False):
    c.setStrokeColor(EDGE); c.setLineWidth(1.2)
    c.setDash(4, 3) if dashed else c.setDash()
    c.line(x1, y1, x2, y2); c.setDash()
    ang = math.atan2(y2 - y1, x2 - x1); p = c.beginPath(); p.moveTo(x2, y2)
    p.lineTo(x2 - 8 * math.cos(ang - 0.4), y2 - 8 * math.sin(ang - 0.4)); p.lineTo(x2 - 8 * math.cos(ang + 0.4), y2 - 8 * math.sin(ang + 0.4)); p.close()
    c.setFillColor(EDGE); c.drawPath(p, fill=1, stroke=0)
    if label:
        c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(GREY); c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 5, label)

# column headers
cols = [(30, "1  USER INPUT", COL["in"]), (190, "2  AGENT REASONING (Claude on Bedrock)", COL["reason"]), (400, "3  TOOL CALLS (Strands tools)", COL["tool"]), (600, "4  AWS SERVICES", COL["ext"]), (760, "5  OUTPUT", COL["out"])]
for x, t, f in cols:
    c.setFont("Helvetica-Bold", 9); c.setFillColor(GREY); c.drawString(x, H - 62, t)

# column 1
box(30, 300, 140, 70, COL["in"], ["Omar, in Arabic:", "'I moved my bakery to Al Quoz,", "my license expires soon.", "Renew it and update my address.'"])
box(30, 170, 140, 50, COL["in"], ["Consent:", "'نعم، أؤكد'"])

# column 2 reasoning steps
box(190, 400, 190, 55, COL["reason"], ["Identify linked services", "license renewal depends on", "address, tax clearance, valid ID"])
box(190, 320, 190, 55, COL["reason"], ["Read every document and", "check validity flags", "EXPIRED? address mismatch?"])
box(190, 235, 190, 60, COL["reason"], ["DECISION: prerequisites missing?", "yes -> add tax clearance service,", "reorder plan; no -> proceed", "(loop until plan is rejection-free)"])
box(190, 150, 190, 55, COL["reason"], ["Present plan + fees + timeline", "WAIT for explicit consent", "(submit tool refuses otherwise)"])
box(190, 65, 190, 55, COL["reason"], ["Submit in dependency order,", "then notify in citizen's language;", "later: status + overdue check"])

# column 3 tools
tools = [(430, "get_citizen_profile"), (400, "search_service_policy  x2"), (370, "list_services"), (340, "list_citizen_documents"), (310, "extract_document  x4"), (180, "submit_application  x3"), (150, "notify_citizen"), (100, "check_application_status")]
for y, t in tools:
    box(400, y - 8, 180, 24, COL["tool"], [t])

# column 4 services
svcs = [(430, "DynamoDB citizens"), (400, "Knowledge Base (S3 Vectors)"), (370, "DynamoDB services"), (340, "S3 documents bucket"), (310, "Amazon Textract"), (180, "DynamoDB applications"), (150, "Amazon Translate + SNS"), (100, "DynamoDB applications")]
for y, t in svcs:
    box(600, y - 8, 140, 24, COL["ext"], [t], bold_first=False)
    arrow(580, y + 4, 600, y + 4)

# column 5 outputs
box(760, 300, 75, 70, COL["out"], ["Plan in Arabic", "3 services", "170 AED", "12 days"])
box(760, 150, 75, 60, COL["out"], ["3 tracking ids", "+ Arabic", "notification"])
box(760, 50, 75, 50, COL["out"], ["Refusal:", "won't backdate", "documents"])

# flows
arrow(170, 335, 190, 427, "request")
arrow(285, 400, 285, 375); arrow(285, 320, 285, 295); arrow(285, 235, 285, 205); arrow(285, 150, 285, 120)
arrow(380, 427, 400, 434); arrow(380, 427, 400, 404, ""); arrow(380, 347, 400, 344); arrow(380, 347, 400, 314); arrow(380, 427, 400, 374)
arrow(380, 265, 400, 404, "policy re-check", dashed=True)
arrow(380, 177, 760, 335, "plan, ask consent")
arrow(170, 195, 190, 177, "confirm")
arrow(380, 92, 400, 184); arrow(380, 92, 400, 154); arrow(380, 92, 400, 104)
arrow(580, 184, 760, 180); arrow(580, 104, 760, 75, "later visit")
c.setFont("Helvetica", 8); c.setFillColor(GREY)
c.drawString(30, 22, "Decision points in blue column are model reasoning, not scripted routing. The guardrail (Bedrock Guardrails) and the system prompt refuse document tampering; the submit tool rejects calls without citizen_confirmed=true.")
c.showPage(); c.save(); print("flow.pdf written")
