#!/usr/bin/env python3
"""
Generates developer-event examples in examples/ using the Python reference SDK,
so the integrity hashes are real rather than hand-written.

    pip install context-passport
    python tools/generate-developer-examples.py

Identifiers and timestamps are pinned to fixed, readable values. That is safe:
under SPEC.md 3.4 the integrity block covers the payload and the parent hash
only. Pinning keeps the files stable in review and in git history.

Run `npm test` after regenerating to validate against schema/v2.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from context_passport import make_passport

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

DROP = ("lineage",)

TRACE = "trace_demo_research_brief"
PROVIDER = "example"
MODEL = "demo-agent-v1"


def build(
    payload,
    *,
    agent_id,
    agent_name,
    event_type,
    role=None,
    provider=PROVIDER,
    model=MODEL,
    trace_id=TRACE,
    parent=None,
    branch_key="main",
    to_agent_id=None,
):
    p = make_passport(
        agent_id=agent_id,
        agent_name=agent_name,
        payload=payload,
        parent=parent,
        to_agent_id=to_agent_id,
        role=role,
        provider=provider,
        model=model,
        event_type=event_type,
        trace_id=trace_id,
        branch_key=branch_key,
    )
    for key in DROP:
        p.pop(key, None)
    return p


def pin(passport, *, ctx_id, timestamp):
    """Fix the identifiers and timestamps. Hashes are unaffected."""
    passport["id"] = ctx_id
    passport["created_at"] = timestamp
    passport["event"]["timestamp"] = timestamp
    # The SDK still emits verification_status and verified_at. The schema no
    # longer defines either, so strip rather than pin: the examples should show
    # the shape the specification describes, not the shape one SDK produces.
    passport["integrity"].pop("verification_status", None)
    passport["integrity"].pop("verified_at", None)
    return passport


def relink(child, parent):
    """Point a pinned child at its pinned parent."""
    child["parent_id"] = parent["id"]
    return child


def write(name, data):
    path = EXAMPLES / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote examples/{name}")


# ------------------------------------------------------------------- error

error = pin(
    build(
        {
            "input": {
                "tool": "web_search",
                "arguments": {"query": "Project Atlas enterprise SLA"},
            },
            "output": None,
            "memory": {
                "error_code": "tool_timeout",
                "message": "Search provider did not respond within 30 seconds.",
                "retryable": True,
            },
        },
        agent_id="agent-researcher-01",
        agent_name="Research Agent",
        event_type="error",
        role="researcher",
    ),
    ctx_id="ctx_1774358320000_e1a2b3c4d5e6",
    timestamp="2026-03-29T10:05:00Z",
)
write("error.passport.json", error)


# ------------------------------------------------------------------- spawn

spawn = pin(
    build(
        {
            "input": {
                "summary": "Found release notes, pricing FAQ, and support article.",
                "confidence": 0.91,
                "sources": ["release-notes.md", "pricing-faq.md"],
            },
            "output": {
                "handoff": "Write a customer-facing launch summary from the research brief.",
            },
            "variables": {
                "tone": "customer_facing",
                "max_words": 600,
            },
        },
        agent_id="agent-planner-01",
        agent_name="Planner Agent",
        event_type="spawn",
        role="planner",
        to_agent_id="agent-writer-01",
    ),
    ctx_id="ctx_1774358330000_a1b2c3d4e5f7",
    timestamp="2026-03-29T10:06:00Z",
)
write("spawn.passport.json", spawn)


# ----------------------------------------------------------------- timeout

timeout = pin(
    build(
        {
            "input": {
                "tool": "web_search",
                "arguments": {"query": "Project Atlas enterprise SLA"},
            },
            "output": None,
            "memory": {
                "operation": "tool_call:web_search",
                "timeout_ms": 30000,
                "elapsed_ms": 30001,
            },
        },
        agent_id="agent-researcher-01",
        agent_name="Research Agent",
        event_type="timeout",
        role="researcher",
    ),
    ctx_id="ctx_1774358340000_f1e2d3c4b5a6",
    timestamp="2026-03-29T10:07:00Z",
)
write("timeout.passport.json", timeout)


# ------------------------------------------------------------------ branch

branch = pin(
    build(
        {
            "input": "Fork alternate pricing copy after reviewer checkpoint.",
            "output": {
                "action": "created",
                "from_branch": "main",
                "branch_key": "alt-pricing",
                "reason": "Explore alternate enterprise pricing wording.",
            },
        },
        agent_id="agent-planner-01",
        agent_name="Planner Agent",
        event_type="branch",
        role="planner",
        branch_key="alt-pricing",
    ),
    ctx_id="ctx_1774358470000_b1a2c3d4e5f8",
    timestamp="2026-03-29T10:32:00Z",
)
write("branch.passport.json", branch)


# ------------------------------------------------------------------- retry

retry = pin(
    build(
        {
            "input": {
                "tool": "web_search",
                "arguments": {"query": "Project Atlas enterprise SLA"},
            },
            "output": None,
            "memory": {
                "attempt": 2,
                "reason": "rate_limit",
                "backoff_ms": 2000,
                "previous_error_code": "tool_timeout",
            },
        },
        agent_id="agent-researcher-01",
        agent_name="Research Agent",
        event_type="retry",
        role="researcher",
    ),
    ctx_id="ctx_1774358355000_c1d2e3f4a5b6",
    timestamp="2026-03-29T10:08:00Z",
)
write("retry.passport.json", retry)


# ------------------------------------------------------------------- fork
# A fork only means something next to the checkpoint it branches from.

fork_checkpoint = pin(
    build(
        {
            "input": {
                "draft": "Customer-facing launch summary prepared.",
                "open_questions": ["Confirm enterprise support SLA wording."],
            },
            "output": {
                "decision": "approved_with_minor_edits",
                "notes": [
                    "Remove unverifiable adoption metric.",
                    "Keep pricing language source-backed.",
                ],
            },
        },
        agent_id="agent-reviewer-01",
        agent_name="Reviewer Agent",
        event_type="checkpoint",
        role="reviewer",
    ),
    ctx_id="ctx_1774358460000_c3d4e5f6a1b2",
    timestamp="2026-03-29T10:31:00Z",
)

fork_event = pin(
    build(
        {
            "input": "Explore alternate enterprise pricing copy on a side branch.",
            "output": {
                "fork_from": "ctx_1774358460000_c3d4e5f6a1b2",
                "branch_key": "alt-pricing",
                "reason": "Test softer enterprise pricing language before merge.",
            },
        },
        agent_id="agent-planner-01",
        agent_name="Planner Agent",
        event_type="fork",
        role="planner",
        branch_key="alt-pricing",
        parent=fork_checkpoint,
    ),
    ctx_id="ctx_1774358480000_d1e2f3a4b5c6",
    timestamp="2026-03-29T10:33:00Z",
)
relink(fork_event, fork_checkpoint)
write("fork.passports.json", [fork_checkpoint, fork_event])


# ----------------------------------------------------------------- revert

revert_commit = pin(
    build(
        {
            "input": "Draft customer-facing launch summary from research brief.",
            "output": {
                "draft": "Customer-facing launch summary prepared.",
                "open_questions": ["Confirm enterprise support SLA wording."],
            },
        },
        agent_id="agent-writer-01",
        agent_name="Writer Agent",
        event_type="commit",
        role="writer",
    ),
    ctx_id="ctx_1774358350000_b2c3d4e5f6a1",
    timestamp="2026-03-29T10:12:30Z",
)

revert_event = pin(
    build(
        {
            "input": "Reviewer flagged unverifiable adoption metric in the draft.",
            "output": {
                "reverted_record": "ctx_1774358350000_b2c3d4e5f6a1",
                "reason": "Draft included an adoption metric without a source citation.",
                "restored_to": "research_brief_only",
            },
        },
        agent_id="agent-reviewer-01",
        agent_name="Reviewer Agent",
        event_type="revert",
        role="reviewer",
        parent=revert_commit,
    ),
    ctx_id="ctx_1774358490000_e5f6a7b8c9da",
    timestamp="2026-03-29T10:34:00Z",
)
relink(revert_event, revert_commit)
write("revert.passports.json", [revert_commit, revert_event])


# ------------------------------------------------------------------ merge

merge_ancestor = pin(
    build(
        {
            "input": "Collect public launch notes for Project Atlas.",
            "output": {
                "summary": "Found release notes, pricing FAQ, and support article.",
                "confidence": 0.91,
                "sources": ["release-notes.md", "pricing-faq.md"],
            },
        },
        agent_id="agent-researcher-01",
        agent_name="Research Agent",
        event_type="commit",
        role="researcher",
    ),
    ctx_id="ctx_1774358291000_a1b2c3d4e5f6",
    timestamp="2026-03-29T10:00:00Z",
)

merge_branch_work = pin(
    build(
        {
            "input": "Draft alternate enterprise pricing wording on alt-pricing branch.",
            "output": {
                "draft": "Enterprise plans include priority support with a published SLA.",
                "branch_key": "alt-pricing",
            },
        },
        agent_id="agent-writer-01",
        agent_name="Writer Agent",
        event_type="commit",
        role="writer",
        branch_key="alt-pricing",
        parent=merge_ancestor,
    ),
    ctx_id="ctx_1774358500000_a1b2c3d4e5f6",
    timestamp="2026-03-29T10:35:00Z",
)
relink(merge_branch_work, merge_ancestor)

merge_event = pin(
    build(
        {
            "input": "Merge alt-pricing wording back onto main after reviewer approval.",
            "output": {
                "merged_from": "alt-pricing",
                "strategy": "take_alt_pricing_wording",
                "conflicts": 0,
                "result": "Enterprise SLA wording updated on main.",
            },
        },
        agent_id="agent-planner-01",
        agent_name="Planner Agent",
        event_type="merge",
        role="planner",
        parent=merge_branch_work,
    ),
    ctx_id="ctx_1774358510000_0a1b2c3d4e5f",
    timestamp="2026-03-29T10:36:00Z",
)
relink(merge_event, merge_branch_work)
write("merge.passports.json", [merge_ancestor, merge_branch_work, merge_event])

print("\nRun `npm test` to validate these against schema/v2.json.")
