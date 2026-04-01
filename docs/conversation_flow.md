# Conversation Flow

## Voice Flow Chart

```mermaid
flowchart TD
    A[📞 Inbound Call] --> B[Greeting & Ask for Phone Number]
    B --> C{Caller Provides Phone?}
    C -->|Yes| D[Call lookup_caller API]
    C -->|No / Refuses| E[Offer Human Callback]

    D --> F{Record Found?}
    F -->|Yes| G["Confirm Identity:<br/>'Am I speaking with {name}?'"]
    F -->|No| H[Ask for Alternative Number]

    H --> I{Try Again?}
    I -->|Yes| D
    I -->|No| E

    G --> J{Identity Confirmed?}
    J -->|Yes ✓| K[Deliver Claim Status]
    J -->|No ✗| L[Apologize & Offer Human Rep]

    K --> M{Claim Status}
    M -->|Approved| N["Share approval details<br/>+ payment timeline"]
    M -->|Pending| O["Share review timeline<br/>+ email notification info"]
    M -->|Requires Docs| P["Explain required docs<br/>+ upload/email instructions"]

    N --> Q[Ask: Anything else?]
    O --> Q
    P --> Q

    Q --> R{More Questions?}
    R -->|Yes| S{Question Type}
    R -->|No| T[Call log_interaction API]

    S -->|FAQ| U[Answer from Knowledge Base]
    S -->|Request Human| E
    S -->|Emergency 🚨| V["Instruct: Hang up & dial 911"]
    S -->|Off-topic| W[Redirect to Claims Scope]

    U --> Q
    W --> Q

    E --> T
    L --> T
    T --> X[Say Goodbye & End Call]
    V --> X

    style A fill:#4CAF50,color:white
    style X fill:#f44336,color:white
    style V fill:#ff9800,color:white
    style K fill:#2196F3,color:white
    style T fill:#9C27B0,color:white
```

## Flow Description

| Step | Action | Integration Point |
|------|--------|-------------------|
| 1. Greeting | Welcome caller, ask for phone number | VAPI TTS → Caller |
| 2. Phone Lookup | Call `lookup_caller` tool | Webhook → Airtable (Callers) |
| 3. Identity Confirmation | Confirm name with caller | VAPI STT ← Caller |
| 4. Claim Status | Deliver status based on record | LLM generates response |
| 5. FAQ / Follow-up | Answer additional questions | LLM + embedded knowledge |
| 6. Escalation | Transfer/callback if requested | LLM handles gracefully |
| 7. Interaction Log | Call `log_interaction` tool | Webhook → Airtable (Interactions) |
| 8. Goodbye | End call politely | VAPI TTS → Caller |
