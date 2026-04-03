# Technical Write-Up

## Part A: Tools, Frameworks, and APIs

### Architecture Overview

This solution uses a managed voice AI platform (VAPI) with a custom webhook backend, optimizing for **reliability**, **low latency**, and **rapid iteration**.

### Component Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Voice Platform** | VAPI | Manages the entire voice pipeline (telephony, STT, LLM, TTS) as a single platform. Eliminates the need to build and maintain SIP handling, audio streaming, or turn-taking logic. Provides built-in phone number provisioning and sub-200ms voice latency. |
| **STT** | Deepgram Nova-2 | Industry-leading accuracy for real-time transcription. Outperforms Whisper on phone audio quality (8kHz, background noise). Streaming mode enables the LLM to start processing before the caller finishes speaking. |
| **LLM** | GPT-4o-mini | Optimized for low-latency voice interactions at $0.15/MTok input. Reliable function calling for our two tools (lookup + logging). Handles our multi-step system prompt (auth flow, branching, FAQ, safety) well. The mini form factor delivers the fast time-to-first-token critical for natural phone conversations. |
| **TTS** | ElevenLabs | Most natural-sounding voice synthesis available. The "warmth" and "stability" controls let us dial in a calm, professional insurance support tone. Streaming output means the caller hears the first word within ~300ms of LLM completion. |
| **Backend** | Python + FastAPI | Async-native, minimal boilerplate. Perfect for a webhook server that receives VAPI events and returns structured tool results. Pydantic models provide request/response validation. Easy to deploy on any platform. |
| **Data Store** | Airtable | Provides both a structured API and a visual UI  - reviewers can see the data without needing database tools. The pyairtable SDK handles auth and pagination. For production, this would migrate to PostgreSQL. |

### Why This Architecture (vs. Alternatives)

**Why VAPI over building a custom pipeline (Twilio + Deepgram + OpenAI + ElevenLabs)?**
A custom pipeline gives maximum control but requires managing: audio streaming, WebSocket connections, turn-taking/interruption detection, silence detection, and audio synchronization. VAPI handles all of this, letting us focus on the conversational logic and integrations  - which is what the assessment evaluates.

**Why a webhook server over VAPI's built-in integrations?**
VAPI offers native Airtable/Google Sheets connectors, but a custom webhook gives us: phone number normalization, fallback logging on call end, call state tracking, and structured error handling. This also demonstrates engineering capability  - we're not just wiring no-code tools together.

**Why GPT-4o-mini over GPT-4o or Claude?**
For voice, latency is king. GPT-4o-mini delivers fast time-to-first-token while maintaining strong instruction following. The system prompt is complex (multi-step auth, branching, FAQ, safety) but doesn't require frontier-level reasoning  - it's structured instruction following, which mini models handle well. At $0.15/MTok input, it's significantly cheaper than GPT-4o ($2.50/MTok), which matters at scale when handling thousands of calls daily.

### Production Scaling Considerations

| Concern | Current (Demo) | Production |
|---------|----------------|------------|
| **Data Store** | Airtable (5 req/sec limit) | PostgreSQL with read replicas |
| **Deployment** | Single instance on Railway | Kubernetes with auto-scaling webhook pods |
| **Monitoring** | FastAPI logs + Airtable records | Datadog/Grafana dashboards, PagerDuty alerts |
| **Phone Numbers** | 1 VAPI number | Multiple numbers with geographic routing |
| **LLM** | GPT-4o-mini | GPT-4o-mini with GPT-4o fallback for complex calls |
| **Caching** | None | Redis cache for frequent caller lookups |
| **Security** | Basic | VAPI webhook signature verification, rate limiting, PII encryption at rest |

---

## Part B: Problem Solving & Debugging

### Challenge: VAPI Webhook Message Format Mismatch

**Problem**: During initial testing, every call failed  - the agent would say "I wasn't able to find an account with that number" even though the phone number existed in Airtable. Direct testing of the Airtable lookup function with the same phone number returned results correctly. The webhook was receiving requests (200 status codes), but the tool results were never reaching the LLM.

**Debugging Process**: I added request logging and inspected the raw webhook payloads via ngrok's inspection API. This revealed two issues:

1. **Wrong message type**: The VAPI documentation examples referenced a `function-call` message type, but the actual API was sending `tool-calls`. Our webhook handler had no case for `tool-calls`, so it fell through to the default `{"ok": true}` response  - which VAPI interpreted as a failed tool call with no result. The LLM then assumed the lookup found nothing.

2. **Different payload structure**: The `tool-calls` format wraps function calls in a `toolCallList` array with `toolCallId` identifiers, and expects results keyed by those IDs. The legacy `function-call` format used `functionCall.name` and `functionCall.parameters` directly.

**How I Solved It**: Added a `handle_tool_calls` handler that parses the `toolCallList` array, routes each call to the correct function, and returns results in the `[{toolCallId, result}]` format VAPI expects. I kept the legacy `function-call` handler as a fallback for backward compatibility.

```python
async def handle_tool_calls(message: dict) -> dict:
    tool_calls = message.get("toolCallList", [])
    results = []
    for tool_call in tool_calls:
        fn_name = tool_call.get("function", {}).get("name", "")
        fn_args = tool_call.get("function", {}).get("arguments", {})
        # Route to handler, collect result
        results.append({"toolCallId": tool_call["id"], "result": result_str})
    return {"results": results}
```

**Why this matters**: In voice AI integrations, silent failures are the worst kind  - the system appears to work (200 OK, no errors) but the user experience is broken. This reinforced the importance of end-to-end testing with real calls rather than relying on documentation alone, and logging the full request/response cycle at every integration boundary.

### Secondary Challenge: Phone Number Normalization

Callers speak phone numbers in varied formats that STT transcribes unpredictably. I implemented `normalize_phone()` to strip non-digit characters on both the application side and via Airtable's `SUBSTITUTE()` formula, so both sides compare pure digit strings regardless of format.

### If I Had One More Week

1. **Prompt caching**: VAPI supports prompt caching for the system prompt. With our ~800-token system prompt, this would reduce input costs by 90% on subsequent calls (cache hits at $0.025/MTok vs $0.25/MTok).

2. **Intent classification pre-filter**: Add a lightweight classifier before the main LLM to detect emergency keywords instantly (< 50ms), rather than waiting for the full LLM response cycle. Safety-critical paths should be as fast as possible.

3. **Regression test suite**: Build a set of 20+ synthetic conversations covering every branch (happy path, wrong number, identity denied, emergency, off-topic, FAQ variations) that run against the webhook server with mocked Airtable responses. This catches prompt regressions before they hit production.

4. **Multi-language support**: Add Spanish language support with a language detection step in the greeting. Deepgram Nova-2 supports multilingual transcription, and the system prompt can be conditioned on detected language.

5. **Warm transfer**: Instead of just promising a callback, integrate with a telephony API to perform a warm transfer to a live agent queue, passing the call context so the agent doesn't have to re-verify.

---

## Part C: Data & Metrics Evaluation

### Key Metrics to Track

| Metric | Definition | Target | Why It Matters |
|--------|-----------|--------|----------------|
| **Containment Rate** | % of calls fully resolved by the AI without human escalation | > 85% | Primary measure of agent effectiveness |
| **Average Handle Time (AHT)** | Mean call duration from greeting to hangup | < 2 min | Efficiency indicator; shorter = better for simple status checks |
| **Authentication Success Rate** | % of calls where caller is successfully identified | > 90% | Measures the phone lookup + identity confirmation flow |
| **Task Completion Rate** | % of calls where the caller's stated intent was fulfilled | > 90% | Did the caller actually get what they called for? |
| **Sentiment Distribution** | % positive / neutral / negative from logged interactions | > 60% positive | Caller satisfaction proxy |
| **Function Call Error Rate** | % of tool invocations that return errors | < 1% | System reliability |
| **First Response Latency** | Time from caller's utterance to first word of agent response | < 1.5s | Natural conversation feel |
| **Escalation Rate** | % of calls transferred or promised a callback | < 15% | Inverse of containment  - should decrease over time |

### How to Use This Data

**Weekly Review Cycle:**
1. Pull call transcripts and metrics from VAPI dashboard + Airtable interaction logs
2. Segment by: claim status type, authentication outcome, sentiment
3. Identify the top 5 failure patterns (calls where task completion failed)
4. Adjust system prompt or add FAQ entries to address recurring issues
5. A/B test prompt changes on 10% of traffic before full rollout

**Prompt Tuning Loop:**
- **Low containment on "Requires Documentation" calls** → Callers keep asking follow-up questions about what documents are needed. **Fix**: Add specific document lists per claim type to the knowledge base, so the agent can say "For your auto claim, we need the police report and repair estimate" instead of generic instructions.
- **High negative sentiment on error paths** → Callers are frustrated when their number isn't found. **Fix**: Adjust the error path tone to be more empathetic and proactive ("I'm sorry about that  - let me make sure a specialist calls you back today").

### Example: Diagnosing a Drop in Containment Rate

**Scenario**: Containment rate drops from 87% to 72% over one week.

**Step 1  - Segment the drop:**
Query interaction logs filtered by `Authenticated = false`. If unauthenticated calls spiked, the problem is in the lookup/verification flow, not claim delivery.

**Step 2  - Analyze transcripts:**
Pull the 50 most recent escalated calls. Cluster by failure reason:
- 40%  - Phone number not found (new customers from recent marketing campaign not yet in system)
- 30%  - Caller asked about a different policy type (life insurance, not claims)
- 30%  - Caller wanted to update their address (not a supported action)

**Step 3  - Root cause:**
The marketing campaign brought in new customers whose records haven't been backfilled into the Callers table. The other failures are scope mismatches.

**Step 4  - Fix:**
1. **Immediate**: Set up a nightly sync from the CRM to Airtable/database so new customer records appear within 24 hours of policy creation.
2. **Prompt update**: Add a branch for "account not found  - might be a new customer" that collects their policy number and manually looks it up, or fast-tracks the human callback.
3. **Scope expansion**: Add address update and policy type routing to the agent's capabilities (or redirect those callers to the right department upfront).

**Step 5  - Measure:**
Track containment rate daily for the next week. Expect recovery to 85%+ within 3-4 days as the data sync catches up, with further improvement as the prompt changes take effect.

### ROI Framework

| Factor | Calculation |
|--------|------------|
| **Cost per AI call** | ~$0.05 (LLM tokens + VAPI telephony + Airtable API) |
| **Cost per human call** | ~$8-12 (agent salary + overhead + AHT) |
| **Savings per contained call** | $8-12 minus $0.05 = ~$8-12 |
| **Monthly call volume** | 10,000 calls |
| **Containment rate** | 85% |
| **Monthly savings** | 8,500 contained calls x $10 avg = **$85,000/month** |

Every 1% improvement in containment = ~$1,000/month in additional savings at this volume. This makes even small prompt optimizations highly valuable.
