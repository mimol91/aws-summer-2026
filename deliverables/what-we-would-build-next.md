# What we would build next

GovEase today proves the agentic loop on synthetic documents and mocked departments: it reads a citizen's documents, catches the rejection before it happens, sequences the linked services, and submits with consent. The next steps take it from prototype to a service Dubai could run.

1. **Real integrations behind the same tools.** Replace the DynamoDB mocks with the Department of Economy and Tourism trade-license API, Ejari for tenancy validation and the Federal Tax Authority for clearance certificates. The Gateway tool contract stays the same, so the agent does not change.
2. **UAE Pass sign-in.** Swap the Cognito demo user for UAE Pass so the citizen's identity and documents come from the national identity wallet instead of uploads.
3. **Proactive follow-up.** Use AgentCore Memory plus a scheduled check so the agent messages Omar when an application goes overdue or a document is 30 days from expiry, before he asks.
4. **Policy-enforced consent.** A Cedar policy on the Gateway that forbids submit_application unless a confirmation event exists in the session, so even a prompt injection cannot file an application.
5. **Quality gates.** An AgentCore evaluator that scores every session on "verified requirements before submitting" and alarms on regressions.
6. **Accessibility and voice.** Screen-reader audit of the right-to-left interface and a voice channel for citizens who prefer to call.
