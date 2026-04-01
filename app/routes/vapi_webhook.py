import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from app.services.airtable import lookup_caller, log_interaction
from app.models.schemas import Sentiment

logger = logging.getLogger(__name__)
router = APIRouter()

# Track call state for end-of-call fallback logging
_call_state: dict[str, dict] = {}


@router.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Handle VAPI server-url webhook events.

    VAPI sends different message types:
    - tool-calls: Assistant wants to invoke one or more tools
    - function-call: Legacy format for tool invocation
    - end-of-call-report: Call has ended, includes transcript + summary
    - status-update: Call status changes
    """
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")

    logger.info(f"VAPI webhook received: type={msg_type}")

    if msg_type == "tool-calls":
        return await handle_tool_calls(message)
    elif msg_type == "function-call":
        return await handle_function_call(message)
    elif msg_type == "end-of-call-report":
        return await handle_end_of_call(message)
    elif msg_type == "status-update":
        return handle_status_update(message)

    return {"ok": True}


async def handle_tool_calls(message: dict) -> dict:
    """Handle VAPI tool-calls format (current API version)."""
    tool_calls = message.get("toolCallList", [])
    call_id = message.get("call", {}).get("id", "unknown")

    results = []
    for tool_call in tool_calls:
        tc_id = tool_call.get("id", "")
        fn = tool_call.get("function", {})
        fn_name = fn.get("name", "")
        fn_args = fn.get("arguments", {})

        logger.info(f"Tool call: {fn_name} with args: {fn_args} (call={call_id})")

        if fn_name == "lookup_caller":
            result = handle_lookup_caller(fn_args, call_id)
        elif fn_name == "log_interaction":
            result = handle_log_interaction(fn_args, call_id)
        else:
            logger.warning(f"Unknown function: {fn_name}")
            result = f"Unknown function: {fn_name}"

        # Extract the result string if it came from our handlers
        if isinstance(result, dict) and "results" in result:
            result_str = result["results"][0]["result"]
        else:
            result_str = str(result)

        results.append({
            "toolCallId": tc_id,
            "result": result_str,
        })

    return {"results": results}


async def handle_function_call(message: dict) -> dict:
    """Handle legacy function-call format."""
    fn_name = message.get("functionCall", {}).get("name", "")
    fn_args = message.get("functionCall", {}).get("parameters", {})
    call_id = message.get("call", {}).get("id", "unknown")

    logger.info(f"Function call: {fn_name} with args: {fn_args} (call={call_id})")

    if fn_name == "lookup_caller":
        return handle_lookup_caller(fn_args, call_id)
    elif fn_name == "log_interaction":
        return handle_log_interaction(fn_args, call_id)
    else:
        logger.warning(f"Unknown function: {fn_name}")
        return {"results": [{"result": f"Unknown function: {fn_name}"}]}


def handle_lookup_caller(args: dict, call_id: str) -> dict:
    """Look up caller by phone number and return their record."""
    phone = args.get("phone_number", "")

    if not phone:
        return {"results": [{"result": "No phone number provided. Please ask the caller for their phone number."}]}

    logger.info(f"Looking up phone: '{phone}' (normalized: '{''.join(c for c in phone if c.isdigit())}')")

    caller = lookup_caller(phone)

    if caller is None:
        _call_state[call_id] = {"authenticated": False, "phone": phone}
        return {
            "results": [
                {
                    "result": (
                        "No account found for that phone number. "
                        "Please ask the caller if they have another number on file, "
                        "or offer to have a human representative follow up."
                    )
                }
            ]
        }

    _call_state[call_id] = {
        "authenticated": False,
        "phone": phone,
        "caller_name": f"{caller.first_name} {caller.last_name}",
    }

    return {
        "results": [
            {
                "result": (
                    f"Found account. The caller's name is {caller.first_name} {caller.last_name}. "
                    f"Please confirm their identity by asking 'Am I speaking with {caller.first_name} {caller.last_name}?' "
                    f"If confirmed, their claim status is: {caller.claim_status}. "
                    f"Claim ID: {caller.claim_id}. Policy Number: {caller.policy_number}."
                )
            }
        ]
    }


def handle_log_interaction(args: dict, call_id: str) -> dict:
    """Log a post-call interaction record to Airtable."""
    caller_name = args.get("caller_name", "Unknown")
    summary = args.get("summary", "No summary provided")
    sentiment_str = args.get("sentiment", "neutral").lower()

    try:
        sentiment = Sentiment(sentiment_str)
    except ValueError:
        sentiment = Sentiment.neutral

    state = _call_state.pop(call_id, {})
    phone = state.get("phone", "")
    authenticated = state.get("authenticated", False)

    record_id = log_interaction(
        caller_name=caller_name,
        phone=phone,
        summary=summary,
        sentiment=sentiment,
        authenticated=authenticated,
    )

    return {"results": [{"result": f"Interaction logged successfully (record: {record_id})."}]}


async def handle_end_of_call(message: dict) -> dict:
    """
    Fallback: if the assistant didn't call log_interaction during the call,
    use the end-of-call-report to log an interaction record.
    """
    call_id = message.get("call", {}).get("id", "unknown")

    state = _call_state.pop(call_id, None)
    if state is not None:
        caller_name = state.get("caller_name", "Unknown Caller")
        phone = state.get("phone", "")

        summary = message.get("summary", "Call ended without summary.")
        ended_reason = message.get("endedReason", "unknown")

        log_interaction(
            caller_name=caller_name,
            phone=phone,
            summary=f"{summary} (ended: {ended_reason})",
            sentiment=Sentiment.neutral,
            authenticated=state.get("authenticated", False),
        )
        logger.info(f"Fallback interaction logged for call {call_id}")

    return {"ok": True}


def handle_status_update(message: dict) -> dict:
    """Log call status updates for monitoring."""
    status = message.get("status", "unknown")
    call_id = message.get("call", {}).get("id", "unknown")
    logger.info(f"Call {call_id} status: {status}")
    return {"ok": True}
