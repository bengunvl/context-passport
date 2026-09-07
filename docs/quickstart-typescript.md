# Quickstart (TypeScript)

Zero to a verified chain in about five minutes, in TypeScript. Every block
below is part of one script and runs as written. The Python SDK walkthrough
is at [`quickstart.md`](quickstart.md).

## Install

```bash
npm install @contextpassport/core@^2.0.0
```

## 1. Record something

A passport is a record of one agent event. The payload is yours; the format
only cares that it is JSON.

```typescript
import { makePassport, verifyChain } from "@contextpassport/core";

const first = makePassport({
  agentId: "agent-underwriter-01",
  agentName: "Underwriting Agent",
  payload: {
    input: "Assess application APP-4471 against the lending policy.",
    output: { decision: "decline", confidence: 0.88 },
  },
  role: "executor",
  provider: "anthropic",
  model: "claude-sonnet-5",
  traceId: "trace_app_4471",
});

console.log(first.id);
console.log(first.integrity.payload_hash);
```

`payload_hash` is the SHA-256 of the payload after RFC 8785 canonicalization.
Two implementations in two languages produce the same bytes, so they produce
the same hash.

## 2. Chain a second record onto it

Pass the previous passport as `parent`. That is the whole chaining API.

```typescript
const second = makePassport({
  agentId: "human:reviewer_2c9d",
  agentName: "Senior Credit Officer",
  payload: {
    input: "Review declined application APP-4471.",
    output: { decision: "approve", reason: "Verified rental history." },
  },
  parent: first,
  role: "compliance",
  eventType: "override",
  traceId: "trace_app_4471",
});

const chain = [first, second];
console.log(second.integrity.parent_hash === first.integrity.integrity_hash);
```

That prints `true`. The child commits to the parent's `integrity_hash`, which
is what makes the sequence tamper-evident rather than merely ordered.

## 3. Verify

```typescript
console.log(verifyChain(chain));
```

`true`. Verification needs nothing but the records themselves: no server, no
network, no trust in whoever wrote them.

## 4. Break it on purpose

This is the part worth seeing for yourself. Edit the first record's output, as
someone rewriting history after the fact would.

```typescript
(chain[0].payload.output as { decision: string }).decision = "approve";

console.log(verifyChain(chain));
```

`false`. Changing the payload changes its `payload_hash`, which no longer
matches the `parent_hash` the second record committed to. The edit is not
prevented, it is **detected**, and detected by anyone holding the records.

Put it back and it verifies again:

```typescript
(chain[0].payload.output as { decision: string }).decision = "decline";

console.log(verifyChain(chain));
```

## 5. What the chain does not protect

The chain covers the payload and the link to the parent. It does not cover
who wrote the record, when, or what kind of event it was. Rewrite the author:

```typescript
chain[0].created_by.agent_id = "someone-else";

console.log(verifyChain(chain));
```

`true`. The attribution changed and nothing noticed. The same is true of
`event.type`, `event.timestamp` and `event.to_agent_id`: under the 2.0 hash
rules those fields are metadata the chain carries but does not bind.

If who and when matter to you, and for any compliance use they do, sign the
records. A signature covers the whole envelope, so a forged author fails
`verifySignature` even though it passes `verifyChain`. Signing is covered in
[`docs/key-management.md`](key-management.md). Binding the envelope into the
chain itself is proposed for 3.0.

## Where to go next

- [`examples/`](../examples) has worked records for each event type, including
  the compliance ones: `consent`, `override`, `escalate`, `redact`, `audit`.
- [`SPEC.md`](../SPEC.md) section 3.4 defines the hashing rules precisely.
- Signing records with Ed25519 via the SDK's `generateKeypair`/`signPassport`,
  so a verifier also learns *who* wrote them, is covered in
  [`docs/key-management.md`](key-management.md).
- [contextpassport/typescript](https://github.com/contextpassport/typescript)
  is the full TypeScript reference implementation.
