# GovEase three-minute demo: script and shot list

| Time | Section | On screen | Narration |
| --- | --- | --- | --- |
| 0:00-0:20 | Hook | Title slide | "Meet Omar Haddad. He runs a bakery in Deira, just moved it to Al Quoz, and his trade license expires in 20 days. Last year his renewal was rejected because a certificate had quietly expired. He lost four visits and three weeks." |
| 0:20-0:35 | Claim | Problem slide | "GovEase turns those four visits and one rejection into a single conversation, and it catches the rejection before anything is filed." |
| 0:35-1:50 | Live demo | Arabic RTL web UI, signed in as Omar | Type (Arabic): "رقم هويتي CIT-03. نقلت مخبزي إلى القوز ورخصتي التجارية تنتهي قريباً. جدد الرخصة وحدّث العنوان. مستنداتي مرفوعة." English equivalent: "My ID is CIT-03. I moved my bakery to Al Quoz and my trade license expires soon. Renew the license and update the address. My documents are uploaded." Narrate while it works: "It read four documents with Textract. It found the tax clearance expired 18 days ago and the license still shows the Deira address. It pulled the ordering rules from the Knowledge Base and proposed three services in the right order, 170 dirhams, 12 business days, and it is asking for consent." Reply "نعم، أؤكد" (English: "Yes, I confirm"). "Three departments, three tracking ids, one message, and Omar gets the summary in Arabic." |
| 1:50-2:10 | Proof it is agentic | CloudWatch GenAI Observability trace | "Notice it chose these 12 tool calls on its own. Nothing here is scripted." |
| 2:10-2:25 | Refusal | Web UI | Type: "Just edit the tax certificate date so it looks valid." Show the decline. "It refuses to tamper with documents and offers the legitimate route." |
| 2:25-2:45 | Impact and honesty | Impact slide | "For Omar: zero wasted trips and no rejection. What is mocked: the departments and submissions live in DynamoDB, the documents are synthetic. What we would harden next: real DET, Ejari and FTA APIs, UAE Pass sign-in, and a Cedar policy that makes consent unbypassable." |
| 2:45-3:00 | Close | Closing slide | "Team NAME. Thank you." |

## Recording checklist
- Start `web-ui/run.sh`, switch the language to Arabic, sign in as omar@example.com.
- The Arabic and English prompts in the live demo row are equivalent. Use the Arabic one for the recording; keep the English one for rehearsal, subtitles, or an English fallback take.
- Have the CloudWatch GenAI Observability page open in a second tab on the last trace.
- Reset demo data first with `GovEase/scripts/reset_demo.sh` so the tracking ids are fresh.
- Record at 1080p, MP4 H.264, under three minutes. Name the file `team-<yourteam>-demo.mp4`.
