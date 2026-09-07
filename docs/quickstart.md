# Quickstart

Zero to a verified chain in about five minutes, in Python. Every block below is
part of one script and runs as written. A TypeScript version of this walkthrough
lives at [`quickstart-typescript.md`](quickstart-typescript.md).

## Install

```bash
pip install context-passport
```

## 1. Record something

A passport is a record of one agent event. The payload is yours; the format
only cares that it is JSON.

```python
from context_passport import make_passport, verify_chain

first = make_passport(
    agent_id="agent-underwriter-01",
    agent_name="Underwriting Agent",
    payload={
        "input": "Assess application APP-4471 against the lending policy.",
        "output": {"decision": "decline", "confidence": 0.88},
    },
    role="executor",
    provider="anthropic",
    model="claude-sonnet-5",
    trace_id="trace_app_4471",
)

print(first["id"])
print(first["integrity"]["payload_hash"])
```

`payload_hash` is the SHA-256 of the payload after RFC 8785 canonicalization.
Two implementations in two languages produce the same bytes, so they produce
the same hash.

## 2. Chain a second record onto it

Pass the previous passport as `parent`. That is the whole chaining API.

```python
second = make_passport(
    agent_id="human:reviewer_2c9d",
    agent_name="Senior Credit Officer",
    payload={
        "input": "Review declined application APP-4471.",
        "output": {"decision": "approve", "reason": "Verified rental history."},
    },
    parent=first,
    role="compliance",
    event_type="override",
    trace_id="trace_app_4471",
)

chain = [first, second]
print(second["integrity"]["parent_hash"] == first["integrity"]["integrity_hash"])
```

That prints `True`. The child commits to the parent's `integrity_hash`, which
is what makes the sequence tamper-evident rather than merely ordered.

## 3. Verify

```python
print(verify_chain(chain))
```

`True`. Verification needs nothing but the records themselves: no server, no
network, no trust in whoever wrote them.

## 4. Break it on purpose

This is the part worth seeing for yourself. Edit the first record's output, as
someone rewriting history after the fact would.

```python
chain[0]["payload"]["output"]["decision"] = "approve"

print(verify_chain(chain))
```

`False`. Changing the payload changes its `payload_hash`, which no longer
matches the `parent_hash` the second record committed to. The edit is not
prevented, it is **detected**, and detected by anyone holding the records.

Put it back and it verifies again:

```python
chain[0]["payload"]["output"]["decision"] = "decline"

print(verify_chain(chain))
```

## 5. What the chain does not protect

The chain covers the payload and the link to the parent. It does not cover
who wrote the record, when, or what kind of event it was. Rewrite the author:

```python
chain[0]["created_by"]["agent_id"] = "someone-else"

print(verify_chain(chain))
```

`True`. The attribution changed and nothing noticed. The same is true of
`event.type`, `event.timestamp` and `event.to_agent_id`: under the 2.0 hash
rules those fields are metadata the chain carries but does not bind.

If who and when matter to you, and for any compliance use they do, sign the
records. A signature covers the whole envelope, so a forged author fails
`verify_signature` even though it passes `verify_chain`. Signing is covered in
[`docs/key-management.md`](key-management.md). Binding the envelope into the
chain itself is proposed for 3.0.

## Where to go next

- [`examples/`](../examples) has worked records for each event type, including
  the compliance ones: `consent`, `override`, `escalate`, `redact`, `audit`.
- [`SPEC.md`](../SPEC.md) section 3.4 defines the hashing rules precisely.
- [`examples/integrations/anthropic_sdk.py`](../examples/integrations/anthropic_sdk.py)
  wires this into real model calls.
- Signing records with Ed25519, so a verifier also learns *who* wrote them, is
  covered in [`docs/key-management.md`](key-management.md).
