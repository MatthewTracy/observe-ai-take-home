# Observe Insurance — AI Claims Support Voice Agent

A VoiceAI agent that handles inbound customer calls for insurance claim status checks. Built with **VAPI**, **GPT-4o-mini**, **FastAPI**, and **Airtable**.

## Live Demo

**Call: +1 (830) 457-9298** — the agent is live 24/7 on Render.

- **Happy path**: Say your number is "555-123-4567" → confirms Sarah Johnson → delivers approved claim status
- **Error path**: Say your number is "555-999-0000" → not found → offers human callback

> API Docs (Swagger): [observe-ai-take-home.onrender.com/docs](https://observe-ai-take-home.onrender.com/docs)

## What It Does

A caller dials in and the AI assistant:
1. **Greets** and asks for their phone number
2. **Authenticates** by looking up their record in Airtable and confirming their name
3. **Delivers claim status** (approved, pending, or requires documentation) with clear next steps
4. **Answers FAQs** about office hours, mailing address, claims process, etc.
5. **Handles edge cases** — unknown numbers, wrong identity, emergency, escalation requests
6. **Logs the interaction** to Airtable with caller name, summary, sentiment, and timestamp

## Architecture

```
Caller → PSTN → VAPI (Deepgram STT → GPT-4o-mini → ElevenLabs TTS)
                         ↓ tool calls
                   FastAPI Webhook Server (Render)
                         ↓
                      Airtable
                  (Callers | Interactions)
```

See [docs/architecture.md](docs/architecture.md) for full system diagrams and [docs/conversation_flow.md](docs/conversation_flow.md) for the conversation flow chart.

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Environment configuration
│   ├── routes/
│   │   ├── vapi_webhook.py     # VAPI webhook handler (core logic)
│   │   └── health.py           # Health check
│   ├── services/
│   │   └── airtable.py         # Airtable read/write client
│   └── models/
│       └── schemas.py          # Pydantic models
├── vapi/
│   └── agent_config.json       # VAPI assistant configuration
├── tests/
│   ├── test_webhook.py         # Webhook handler tests (11 tests)
│   └── test_airtable.py        # Airtable service tests (6 tests)
├── docs/
│   ├── architecture.md         # System architecture diagrams
│   ├── conversation_flow.md    # Conversation flow chart
│   └── technical_writeup.md    # Technical write-up
├── scripts/
│   └── seed_airtable.py        # Seed sample caller data
├── Dockerfile                  # Production container
├── render.yaml                 # Render deployment config
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites
- Python 3.12+
- [VAPI account](https://vapi.ai) (free tier works)
- [Airtable account](https://airtable.com) (free tier works)

### 1. Clone & Install

```bash
git clone https://github.com/MatthewTracy/observe-ai-take-home.git
cd observe-ai-take-home
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Airtable

1. Create a new Airtable base
2. Create a **Callers** table with fields:
   | Field | Type |
   |-------|------|
   | First Name | Single line text |
   | Last Name | Single line text |
   | Phone | Phone number |
   | Claim Status | Single select (`Approved`, `Pending`, `Requires Documentation`) |
   | Claim ID | Single line text |
   | Policy Number | Single line text |

3. Create an **Interactions** table with fields:
   | Field | Type |
   |-------|------|
   | Caller Name | Single line text |
   | Phone | Phone number |
   | Summary | Long text |
   | Sentiment | Single select (`Positive`, `Neutral`, `Negative`) |
   | Timestamp | Single line text |
   | Authenticated | Checkbox |

4. Get your [Personal Access Token](https://airtable.com/create/tokens) and Base ID (from the Airtable URL)

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 4. Seed Sample Data

```bash
python -m scripts.seed_airtable
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Run Tests

```bash
pytest tests/ -v
```

### 7. Docker (Alternative)

```bash
docker build -t observe-voice-agent .
docker run -p 8000:8000 --env-file .env observe-voice-agent
```

### 8. Configure VAPI

1. Go to [VAPI Dashboard](https://dashboard.vapi.ai)
2. Create a new assistant using the config in `vapi/agent_config.json`
3. Set the **Server URL** to your deployment URL + `/vapi/webhook`
4. Assign a phone number to the assistant
5. Call the number to test!

## Branching Workflows

### Happy Path
```
Greeting → Phone Number → Airtable Lookup (found) → "Am I speaking with Sarah Johnson?"
→ Yes → "Your claim CLM-2024-001 has been approved..." → Anything else? → No
→ Log interaction to Airtable → Goodbye
```

### Error Path: Phone Not Found
```
Greeting → Phone Number → Airtable Lookup (not found) → "Try another number?"
→ No → "I'll arrange a human callback" → Log interaction → Goodbye
```

### Error Path: Identity Denied
```
Greeting → Phone Number → Airtable Lookup (found) → "Am I speaking with Sarah Johnson?"
→ No → "Sorry for the confusion, I'll arrange a human representative" → Log interaction → Goodbye
```

### Emergency
```
At any point → Caller mentions emergency → "Please hang up and dial 911 immediately"
```

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Working Voice Agent | **+1 (830) 457-9298** (live) |
| API Docs | [observe-ai-take-home.onrender.com/docs](https://observe-ai-take-home.onrender.com/docs) |
| Conversation Flow Chart | [docs/conversation_flow.md](docs/conversation_flow.md) |
| System Architecture Diagram | [docs/architecture.md](docs/architecture.md) |
| Technical Write-Up | [docs/technical_writeup.md](docs/technical_writeup.md) |
| Test Suite | `pytest tests/ -v` (17 tests) |

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Voice Platform | VAPI | Managed STT/TTS/LLM orchestration with built-in telephony |
| STT | Deepgram Nova-2 | Low-latency streaming transcription optimized for phone audio |
| LLM | GPT-4o-mini | Fast inference, reliable function calling, cost-effective |
| TTS | ElevenLabs | Natural, human-like voice synthesis |
| Backend | Python + FastAPI | Async webhook server with auto-generated API docs |
| Data Store | Airtable | Structured API + visual UI for reviewer access |
| Deployment | Render | Auto-deploy from GitHub, free tier |
| Testing | pytest | 17 tests covering happy paths, error paths, and edge cases |
