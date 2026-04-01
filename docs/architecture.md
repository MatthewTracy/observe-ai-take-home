# Solution Architecture

## System Architecture Diagram

```mermaid
flowchart LR
    subgraph Caller
        A[📞 Phone / PSTN]
    end

    subgraph VAPI["VAPI Platform"]
        B[Telephony<br/>SIP/PSTN Gateway]
        C[Deepgram Nova-3<br/>STT]
        D[GPT-5-mini<br/>LLM]
        E[ElevenLabs<br/>TTS]
        B --> C --> D --> E --> B
    end

    subgraph Backend["FastAPI Webhook Server"]
        F[POST /vapi/webhook]
        G[lookup_caller Handler]
        H[log_interaction Handler]
        I[end-of-call Fallback]
    end

    subgraph Data["Airtable"]
        J[(Callers Table<br/>Phone, Name, Claim Status)]
        K[(Interactions Table<br/>Name, Summary, Sentiment)]
    end

    subgraph Monitoring["Monitoring & Logging"]
        L[VAPI Dashboard<br/>Call Analytics]
        M[FastAPI Logs<br/>Webhook Events]
        N[Airtable<br/>Interaction Records]
    end

    A <-->|Voice| B
    D -->|"function-call"| F
    F --> G
    F --> H
    F --> I
    G -->|Read| J
    H -->|Write| K
    I -->|Write| K
    B -.->|Metrics| L
    F -.->|Logs| M
    K -.->|Records| N

    style VAPI fill:#e3f2fd
    style Backend fill:#f3e5f5
    style Data fill:#e8f5e9
    style Monitoring fill:#fff3e0
```

## Component Details

### Voice Pipeline (VAPI)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Telephony | VAPI SIP/PSTN | Receives inbound calls, manages phone numbers |
| STT | Deepgram Nova-3 | Real-time speech-to-text with low latency |
| LLM | GPT-5-mini | Conversation logic, tool calling, response generation |
| TTS | ElevenLabs | Natural, human-like voice synthesis |

### Webhook Server (FastAPI)
| Endpoint | Trigger | Action |
|----------|---------|--------|
| `POST /vapi/webhook` | Every VAPI event | Routes to appropriate handler |
| `lookup_caller` handler | LLM calls tool | Queries Airtable Callers table by phone |
| `log_interaction` handler | LLM calls tool at end of call | Writes record to Airtable Interactions table |
| `end-of-call` handler | Call ends | Fallback logging if LLM didn't log |
| `GET /health` | Health checks | Returns service status |

### Data Layer (Airtable)
| Table | Access | Schema |
|-------|--------|--------|
| Callers | Read | First Name, Last Name, Phone, Claim Status, Claim ID, Policy Number |
| Interactions | Write | Caller Name, Phone, Summary, Sentiment, Timestamp, Authenticated |

### Monitoring Touchpoints
| Point | What's Captured | Where |
|-------|----------------|-------|
| VAPI Dashboard | Call duration, latency, completion rate, transcripts | VAPI web console |
| Webhook Logs | Function call timing, errors, Airtable response times | FastAPI stdout / log aggregator |
| Interaction Records | Every call outcome: who called, what happened, sentiment | Airtable Interactions table |
| Error Logging | Failed lookups, Airtable errors, unknown function calls | FastAPI structured logs |

## Data Flow: Happy Path

```mermaid
sequenceDiagram
    participant Caller
    participant VAPI
    participant LLM as GPT-5-mini
    participant Server as FastAPI
    participant DB as Airtable

    Caller->>VAPI: Dials phone number
    VAPI->>Caller: "Thank you for calling Observe Insurance..."
    Caller->>VAPI: "My number is 555-123-4567"
    VAPI->>LLM: [transcript] caller said phone number
    LLM->>Server: function-call: lookup_caller("5551234567")
    Server->>DB: Query Callers where Phone = "5551234567"
    DB-->>Server: {Sarah Johnson, Approved, CLM-2024-001}
    Server-->>LLM: "Found account. Name: Sarah Johnson..."
    LLM->>VAPI: "Am I speaking with Sarah Johnson?"
    VAPI->>Caller: TTS: identity confirmation
    Caller->>VAPI: "Yes, that's me"
    LLM->>VAPI: "Great news! Your claim has been approved..."
    VAPI->>Caller: TTS: claim status
    Caller->>VAPI: "That's all, thank you"
    LLM->>Server: function-call: log_interaction(...)
    Server->>DB: Create Interactions record
    DB-->>Server: record created
    LLM->>VAPI: "Thank you for calling. Have a wonderful day!"
    VAPI->>Caller: TTS: goodbye
```

## Data Flow: Error Path (Phone Not Found)

```mermaid
sequenceDiagram
    participant Caller
    participant VAPI
    participant LLM as GPT-5-mini
    participant Server as FastAPI
    participant DB as Airtable

    Caller->>VAPI: Dials phone number
    VAPI->>Caller: "Thank you for calling..."
    Caller->>VAPI: "My number is 555-999-0000"
    LLM->>Server: function-call: lookup_caller("5559990000")
    Server->>DB: Query Callers where Phone = "5559990000"
    DB-->>Server: No records found
    Server-->>LLM: "No account found for that phone number..."
    LLM->>VAPI: "I wasn't able to find an account..."
    VAPI->>Caller: TTS: no account found
    Caller->>VAPI: "No, that's the only number I have"
    LLM->>VAPI: "I'll arrange for a representative to call you back..."
    LLM->>Server: function-call: log_interaction(Unknown Caller, ...)
    Server->>DB: Create Interactions record (unauthenticated)
    LLM->>VAPI: "Thank you for calling. Goodbye!"
```
