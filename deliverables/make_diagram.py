"""Render the GovEase architecture diagram to PDF (submission) and PNG (deck) with reportlab."""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

W, H = landscape(A4)
INK = colors.HexColor("#1f2937")
BOX = colors.HexColor("#eef2ff")
BOX2 = colors.HexColor("#ecfdf5")
BOX3 = colors.HexColor("#fff7ed")
EDGE = colors.HexColor("#4f46e5")
GREY = colors.HexColor("#6b7280")

# (id, x, y, w, h, fill, lines)
NODES = {
    "user": (20, 300, 110, 60, BOX3, ["Omar (citizen)", "Arabic, RTL"]),
    "ui": (150, 300, 140, 60, BOX3, ["Bilingual web UI", "Streamlit + Cognito sign-in"]),
    "runtime": (320, 280, 160, 100, BOX, ["AgentCore Runtime", "Strands agent", "8-step workflow,", "consent gate"]),
    "model": (320, 440, 160, 60, BOX, ["Amazon Bedrock", "Claude Sonnet 4.5 + Guardrail"]),
    "memory": (320, 160, 160, 60, BOX, ["AgentCore Memory", "citizen preferences"]),
    "gateway": (510, 280, 140, 100, BOX, ["AgentCore Gateway*", "MCP, Cognito JWT", "tool spec ready"]),
    "lambda": (680, 280, 145, 100, BOX2, ["Tools (in-process + Lambda)", "extract_document", "submit_application", "check_status, notify..."]),
    "textract": (680, 440, 145, 50, BOX2, ["Amazon Textract", "reads ID, license, Ejari"]),
    "kb": (680, 160, 145, 50, BOX2, ["Knowledge Base", "requirements, linked processes"]),
    "ddb": (680, 90, 145, 50, BOX2, ["DynamoDB", "services, citizens, applications"]),
    "s3": (510, 440, 140, 50, BOX2, ["S3 documents bucket", "private, encrypted"]),
    "sns": (510, 160, 140, 50, BOX2, ["SNS + Amazon Translate", "status updates in Arabic"]),
    "cw": (320, 40, 160, 50, BOX3, ["CloudWatch", "GenAI Observability traces"]),
}
EDGES = [
    ("user", "ui", "chat"), ("ui", "runtime", "invoke"), ("runtime", "model", ""), ("runtime", "memory", ""),
    ("runtime", "gateway", "MCP"), ("gateway", "lambda", ""), ("lambda", "textract", ""), ("lambda", "kb", ""),
    ("lambda", "ddb", ""), ("lambda", "s3", ""), ("lambda", "sns", ""), ("runtime", "cw", "traces"),
]


def center(n):
    x, y, w, h, *_ = NODES[n]
    return x + w / 2, y + h / 2


def edge_points(a, b):
    ax, ay = center(a); bx, by = center(b)
    x, y, w, h, *_ = NODES[a]
    x2, y2, w2, h2, *_ = NODES[b]
    # leave from the facing side of each box
    if abs(bx - ax) > abs(by - ay):
        sx = x + w if bx > ax else x
        ex = x2 if bx > ax else x2 + w2
        return sx, ay, ex, by
    sy = y + h if by > ay else y
    ey = y2 if by > ay else y2 + h2
    return ax, sy, bx, ey


def draw(c: canvas.Canvas):
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 18)
    c.drawString(30, H - 40, "GovEase: agent architecture (Future Vision hackathon, GovEase track)")
    c.setFont("Helvetica", 10); c.setFillColor(GREY)
    c.drawString(30, H - 58, "One request: read documents, catch the rejection, sequence linked services, confirm, submit across departments, notify in Arabic. All in us-west-2.")
    for a, b, label in EDGES:
        sx, sy, ex, ey = edge_points(a, b)
        c.setStrokeColor(EDGE); c.setLineWidth(1.2); c.line(sx, sy, ex, ey)
        # arrow head
        import math
        ang = math.atan2(ey - sy, ex - sx)
        p = c.beginPath(); p.moveTo(ex, ey)
        p.lineTo(ex - 8 * math.cos(ang - 0.4), ey - 8 * math.sin(ang - 0.4))
        p.lineTo(ex - 8 * math.cos(ang + 0.4), ey - 8 * math.sin(ang + 0.4)); p.close()
        c.setFillColor(EDGE); c.drawPath(p, fill=1, stroke=0)
        if label:
            c.setFont("Helvetica-Oblique", 8); c.setFillColor(GREY)
            c.drawString((sx + ex) / 2 - 10, (sy + ey) / 2 + 4, label)
    for n, (x, y, w, h, fill, lines) in NODES.items():
        c.setFillColor(fill); c.setStrokeColor(colors.HexColor("#c7d2fe")); c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
        c.setFillColor(INK)
        for i, t in enumerate(lines):
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 9 if i == 0 else 8)
            c.drawCentredString(x + w / 2, y + h - 14 - i * 11, t)
    c.setFont("Helvetica", 8); c.setFillColor(GREY)
    c.drawString(30, 32, "* Gateway creation is denied to the workshop participant role, so the deployed runtime calls the same tool code in-process; the Lambda target and tool spec are deployed and tested.")
    c.drawString(30, 20, "Real: Textract, Knowledge Base, Bedrock + Guardrail, Runtime, Gateway, Memory, Translate, SNS.  Mocked: departments and submissions are DynamoDB rows; documents and citizens are synthetic.")


c = canvas.Canvas("architecture.pdf", pagesize=landscape(A4))
c.setTitle("GovEase architecture"); draw(c); c.showPage(); c.save()
print("architecture.pdf written")
