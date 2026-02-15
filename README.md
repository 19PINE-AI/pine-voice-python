# Pine Voice SDK for Python

Official SDK for [Pine AI](https://pine.ai) voice calls. Make phone calls via Pine's AI voice agent from any Python application — no MCP client or OpenClaw required.

Supports both **synchronous** and **asynchronous** usage.

## Install

```bash
pip install pine-voice
```

## Quick start

```python
from pine_voice import PineVoice

client = PineVoice(access_token="your-access-token", user_id="your-user-id")

result = client.calls.create_and_wait(
    to="+14155551234",
    name="Dr. Smith Office",
    context=(
        "Local dentist office. I'm an existing patient (Jane Doe, DOB 03/15/1990). "
        "Open Mon-Fri 9am-5pm. Dr. Smith is my preferred dentist but Dr. Lee is also fine."
    ),
    objective="Schedule a dental cleaning for next Tuesday afternoon, ideally 2-4pm",
    instructions=(
        "If Tuesday afternoon is unavailable, try Wednesday or Thursday afternoon. "
        "If no afternoons are open this week, take the earliest available afternoon next week. "
        "Confirm the appointment date, time, and dentist name before hanging up."
    ),
)

print(result.transcript)
print(result.triage_category)
```

## Authentication

### Option A: Pass credentials directly

```python
client = PineVoice(access_token="your-access-token", user_id="your-user-id")
```

### Option B: Use environment variables

```bash
export PINE_ACCESS_TOKEN="your-access-token"
export PINE_USER_ID="your-user-id"
```

```python
client = PineVoice()  # reads from env
```

### Getting credentials

If you don't have credentials yet, use the auth helpers:

```python
from pine_voice import PineVoice

# Step 1: Request a verification code (sent to your Pine AI account email)
request_token = PineVoice.auth.request_code("you@example.com")

# Step 2: Enter the code from your email
credentials = PineVoice.auth.verify_code("you@example.com", request_token, "1234")

# Step 3: Use the credentials
client = PineVoice(
    access_token=credentials.access_token,
    user_id=credentials.user_id,
)
```

## Making calls

### Fire and poll

```python
# Initiate (returns immediately)
call = client.calls.create(
    to="+14155552345",
    name="Bay Area Auto Care",
    context=(
        "Local auto repair shop. My car is a 2019 Honda Civic, ~45,000 miles. "
        "Due for a routine oil change and tire rotation. No warning lights or known issues."
    ),
    objective=(
        "Schedule an oil change and tire rotation for this Friday morning, ideally before noon"
    ),
    instructions=(
        "If Friday morning is full, try Friday afternoon. "
        "If Friday is completely booked, try next Monday or Tuesday morning. "
        "Ask for a price estimate for both services combined. "
        "Ask how long the service will take so I know when to pick up the car. "
        "Confirm the appointment date, time, services, and estimated cost before hanging up."
    ),
    caller="communicator",
    voice="female",
    max_duration_minutes=10,
)

# Poll until complete
status = client.calls.get(call.call_id)
```

### Call and wait (SSE streaming with polling fallback)

```python
result = client.calls.create_and_wait(
    to="+14155559876",
    name="Bella Italia Restaurant",
    context=(
        "Italian restaurant in downtown SF. Reservation for Mike Chen. "
        "Party of 4 adults, no children. One guest is vegetarian, one has a nut allergy."
    ),
    objective="Make a dinner reservation for tonight at 7pm for 4 people",
    instructions=(
        "If 7pm is not available, try 7:30pm or 8pm. "
        "If tonight is fully booked, try tomorrow (Saturday) at the same times. "
        "Request a booth or quiet table if possible, but not required. "
        "Mention the nut allergy and ask if they can accommodate it. "
        "Confirm the reservation date, time, party size, and name on the reservation."
    ),
    # SSE streaming is used by default for real-time delivery.
    # Falls back to polling if SSE is unavailable.
    poll_interval=10,  # polling fallback interval (default 10s)
)

print(result.status)          # "completed" | "failed" | "cancelled"
print(result.transcript)      # full conversation
print(result.summary)         # LLM summary (empty unless enable_summary=True)
print(result.triage_category) # "successful" | "partially_successful" | ...
print(result.credits_charged) # credits used
```

## Async usage

```python
from pine_voice import AsyncPineVoice

client = AsyncPineVoice(access_token="...", user_id="...")

# Auth (async)
request_token = await AsyncPineVoice.auth.request_code("you@example.com")
credentials = await AsyncPineVoice.auth.verify_code("you@example.com", request_token, "1234")

# Calls (async)
call = await client.calls.create(to="+14155551234", name="...", context="...", objective="...")
status = await client.calls.get(call.call_id)
result = await client.calls.create_and_wait(to="+14155551234", name="...", context="...", objective="...")
```

Both clients support context managers:

```python
# Sync
with PineVoice(access_token="...", user_id="...") as client:
    result = client.calls.create_and_wait(...)

# Async
async with AsyncPineVoice(access_token="...", user_id="...") as client:
    result = await client.calls.create_and_wait(...)
```

## Error handling

```python
from pine_voice import PineVoice, AuthError, RateLimitError, CallError

try:
    result = client.calls.create_and_wait(...)
except AuthError as e:
    # Token expired or invalid — re-authenticate
    print(f"Auth failed: {e.code} {e.message}")
except RateLimitError as e:
    # Too many calls — wait and retry
    print(f"Rate limited: {e.message}")
except CallError as e:
    # Call-specific issue (invalid phone, DND, policy, etc.)
    print(f"Call error: {e.code} {e.message}")
```

## API reference

### `PineVoice(access_token?, user_id?, gateway_url?)`

Synchronous client. Falls back to `PINE_ACCESS_TOKEN` and `PINE_USER_ID` env vars.

### `AsyncPineVoice(access_token?, user_id?, gateway_url?)`

Asynchronous client. Same parameters as `PineVoice`.

### `PineVoice.auth.request_code(email) -> str`

Request a verification code. Returns the `request_token`.

### `PineVoice.auth.verify_code(email, request_token, code) -> Credentials`

Verify the code. Returns `Credentials(access_token, user_id)`.

### `client.calls.create(...) -> CallInitiated`

Initiate a call. Returns `CallInitiated(call_id, status)`.

| Param | Type | Required | Description |
|---|---|---|---|
| `to` | `str` | Yes | Phone number in E.164 format. Supported countries: US/CA (+1), UK (+44), AU (+61), NZ (+64), IE (+353) |
| `name` | `str` | Yes | Name of the person or business being called |
| `context` | `str` | Yes | Background context about the callee and info needed during the call |
| `objective` | `str` | Yes | Specific goal the call should accomplish |
| `instructions` | `str` | No | Detailed strategy and instructions for the voice agent |
| `caller` | `str` | No | `"negotiator"` for complex negotiations (requires thorough strategy in context/instructions). `"communicator"` for general tasks. Default: `"negotiator"` |
| `voice` | `str` | No | `"male"` or `"female"`. Default: `"female"` |
| `max_duration_minutes` | `int` | No | Max call duration in minutes (1-120). Default: 120 |
| `enable_summary` | `bool` | No | Request an LLM-generated summary after the call. Default: `False`. Most AI agents can process the full transcript directly, so the summary is opt-in to save latency and cost. |

### `client.calls.get(call_id) -> CallStatus | CallResult`

Get call status. Returns `CallResult` if terminal.

### `client.calls.create_and_wait(...) -> CallResult`

Initiate and wait until complete. Returns `CallResult`.

Uses SSE streaming for real-time result delivery. If the SSE connection fails or the server doesn't support it, automatically falls back to polling. Reconnects once on SSE connection drop before falling back.

| Extra Param | Type | Default | Description |
|---|---|---|---|
| `poll_interval` | `int` | `10` | Seconds between polling requests (fallback only) |
| `use_sse` | `bool` | `True` | Try SSE streaming first. Set `False` to force polling. |
| `on_progress` | `Callable[[CallProgress], None]` | `None` | Callback invoked with a `CallProgress` object whenever the call phase changes or a new transcript turn arrives. Only works when SSE streaming is available; during polling fallback, called after each poll cycle. |

## Supported countries

The voice agent can only speak English. Calls can be placed to the following countries:

- US and Canada (+1)
- United Kingdom (+44)
- Australia (+61)
- New Zealand (+64)
- Ireland (+353)

Calls to numbers outside these country codes will be rejected with a `POLICY_VIOLATION` error.

## Requirements

- Python 3.9+
- Pine AI Pro subscription ([pine.ai](https://pine.ai))

## License

MIT
