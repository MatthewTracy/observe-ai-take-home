# Observe Insurance — AI Claims Support Voice Agent

A VoiceAI agent that handles inbound customer calls for insurance claim status checks. Built with **VAPI**, **GPT-5-mini**, **FastAPI**, and **Airtable**.

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
Caller → PSTN → VAPI (Deepgram STT → GPT-5-mini → ElevenLabs TTS)
                         ↓ function calls
                   FastAPI Webhook Server
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
├── docs/
│   ├── architecture.md         # System architecture diagrams
│   ├── conversation_flow.md    # Conversation flow chart
│   └── technical_writeup.md    # Technical write-up
├── scripts/
│   └── seed_airtable.py        # Seed sample caller data
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites
- Python 3.11+
- [VAPI account](https://vapi.ai) (free tier works)
- [Airtable account](https://airtable.com) (free tier works)
- [ngrok](https://ngrok.com) (for local development)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/observe-ai-take-home.git
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
# Edit .env with your actual keys:
#   AIRTABLE_PAT=pat...
#   AIRTABLE_BASE_ID=app...
```

### 4. Seed Sample Data

```bash
python -m scripts.seed_airtable
```

This creates 6 sample callers with varied claim statuses.

### 5. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Expose with ngrok

```bash
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`).

### 7. Configure VAPI

1. Go to [VAPI Dashboard](https://dashboard.vapi.ai)
2. Create a new assistant using the config in `vapi/agent_config.json`
3. Set the **Server URL** to `https://YOUR_NGROK_URL/vapi/webhook`
4. Assign a phone number to the assistant
5. Call the number to test!

## Demo Scenarios

### Happy Path
Call with a known number (e.g., "555-123-4567" for Sarah Johnson):
- Agent greets → asks for phone → looks up record → confirms identity → delivers "Approved" status → logs interaction

### Error Path
Call with an unknown number (e.g., "555-999-0000"):
- Agent greets → asks for phone → lookup fails → offers alternative number → offers human callback → logs interaction

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Working Voice Agent | VAPI + this webhook server |
| Conversation Flow Chart | [docs/conversation_flow.md](docs/conversation_flow.md) |
| System Architecture Diagram | [docs/architecture.md](docs/architecture.md) |
| Technical Write-Up | [docs/technical_writeup.md](docs/technical_writeup.md) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice Platform | VAPI |
| STT | Deepgram Nova-3 |
| LLM | GPT-5-mini |
| TTS | ElevenLabs |
| Backend | Python + FastAPI |
| Data Store | Airtable |
