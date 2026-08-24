"""foundry_service.py - wraps the EXISTING Foundry Agent thin client
(agent_api_demo/call_agent_api.py) for use from FastAPI. This does not
reimplement any agent/tool-calling logic - it just imports and reuses the
already-working, already-tested client, same as refresh_and_load.py reuses
the existing enrichment pipeline.

The client connects lazily on first use (not at import time) and is
cached afterward, so an app boot never fails or blocks just because
Foundry is briefly unreachable - see get_client()'s error handling and
the "AI Assistant unavailable, dashboard still works" principle from the
spec's error-handling section."""

import sys

sys.path.insert(0, r"C:\Users\nbaskaran\source\repos\FoundryAgentFunctionCalling\agent_api_demo")
import call_agent_api  # noqa: E402

_client = None
_client_error = None

# Tracks the Foundry agent's last response id for the chat assistant only,
# so a follow-up like "next" or "what about California" threads onto the
# prior turn via the Responses API's previous_response_id (see
# call_agent_api.ask_agent). This is a single shared conversation thread -
# fine for this single-user prototype, not for multi-user production.
_last_chat_response_id = None


def get_client():
    """Connects on first call, then reuses the same client. Returns
    (client, error) - error is None on success, or a human-readable
    message if the Foundry agent couldn't be reached."""
    global _client, _client_error
    if _client is not None:
        return _client, None
    if _client_error is not None:
        return None, _client_error
    try:
        _client = call_agent_api.get_agent_client()
        return _client, None
    except Exception as e:
        _client_error = f"Could not connect to the Foundry agent: {e}"
        return None, _client_error


def ask(question: str, maintain_history: bool = False):
    """Sends a question to the existing Foundry agent. Returns
    (answer, error) - exactly one of which is None. Never raises -
    callers (FastAPI routes) turn a non-None error into a 200 response
    with a friendly message, not a 500, so the rest of the dashboard
    keeps working if Foundry is temporarily unavailable.

    maintain_history=True threads this question onto the running chat
    conversation (see _last_chat_response_id) so follow-ups like "next"
    resolve correctly. Leave False for one-off asks like outreach
    generation, which should not be influenced by unrelated chat turns."""
    client, error = get_client()
    if error:
        return None, error
    try:
        global _last_chat_response_id
        previous_response_id = _last_chat_response_id if maintain_history else None
        response = call_agent_api.ask_agent(client, question, previous_response_id=previous_response_id)
        if maintain_history:
            _last_chat_response_id = response.id
        return response.output_text, None
    except Exception as e:
        return None, f"The Foundry agent didn't respond: {e}"


def reset_chat_history():
    """Starts a fresh conversation thread for the chat assistant - call
    this when the user explicitly wants to start over, so old context
    (e.g. "we were talking about Texas") doesn't leak into an unrelated
    new question."""
    global _last_chat_response_id
    _last_chat_response_id = None


# Phrases the agent uses when its search index doesn't contain this
# carrier - distinct from an actual outage (get_client()/ask() already
# handle that). This happens for any opportunity added after the index
# was last built, e.g. via the "Refresh Data" button, which updates
# SQLite but not the separate Foundry search index.
_NOT_FOUND_MARKERS = ("not found", "couldn't find", "could not find", "no record", "no matching")


def generate_outreach_for_carrier(carrier_legal_name: str, oos_date: str = None):
    """Asks the existing Foundry agent to generate the grounded outreach
    message for a specific carrier - the same agent, same instructions,
    same scope guardrail as the chat assistant. Does not build the
    message text itself; the agent's own retrieval + template logic does
    that, exactly as the spec requires ('do not recreate the outreach
    generation logic') - EXCEPT when the agent's index doesn't have this
    carrier yet (a real gap: the index is a separate, static snapshot,
    and SQLite can now gain carriers the index has never seen via the
    Refresh Data button). In that one case, fall back to the exact same
    fixed template the spec itself defines, built from real data we
    already trust (carrier name + oos_date from SQLite) - not an AI
    guess, not fabricated, just the deterministic form of the same
    message the agent would otherwise have produced."""
    question = f"Create an outreach message for {carrier_legal_name}"
    message, error = ask(question)

    if message and oos_date and any(marker in message.lower() for marker in _NOT_FOUND_MARKERS):
        fallback = (
            f"Hi {carrier_legal_name}, I see your operations were recently impacted by an "
            f"out-of-service notice dated {oos_date}. Can we set up a call to discuss new "
            f"sales opportunities?"
        )
        return fallback, None

    return message, error
