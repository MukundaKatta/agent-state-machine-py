import pytest
from agent_state_machine import (
    StateMachine,
    InvalidTransitionError,
    Transition,
)


# ---------------------------------------------------------------------------
# Basic transitions
# ---------------------------------------------------------------------------


def test_initial_state():
    sm = StateMachine("idle")
    assert sm.state == "idle"


def test_simple_transition():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start")
    sm.trigger("start")
    assert sm.state == "running"


def test_chain_transitions():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.add_transition("b", "c", "go")
    sm.trigger("go")
    sm.trigger("go")
    assert sm.state == "c"


def test_invalid_trigger_raises():
    sm = StateMachine("idle")
    with pytest.raises(InvalidTransitionError):
        sm.trigger("nonexistent")


def test_trigger_wrong_state_raises():
    sm = StateMachine("idle")
    sm.add_transition("running", "done", "finish")
    with pytest.raises(InvalidTransitionError):
        sm.trigger("finish")


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------


def test_trigger_returns_true_on_success():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start")
    assert sm.trigger("start") is True


def test_trigger_returns_false_when_guard_blocks():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start", guard=lambda ctx: False)
    result = sm.trigger("start")
    assert result is False
    assert sm.state == "idle"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_guard_allows_transition():
    sm = StateMachine("idle")
    sm.add_transition(
        "idle", "running", "start", guard=lambda ctx: ctx.get("ready", False)
    )
    sm.trigger("start", context={"ready": True})
    assert sm.state == "running"


def test_guard_blocks_transition():
    sm = StateMachine("idle")
    sm.add_transition(
        "idle", "running", "start", guard=lambda ctx: ctx.get("ready", False)
    )
    sm.trigger("start", context={"ready": False})
    assert sm.state == "idle"


def test_guard_receives_context():
    received = {}

    def guard(ctx):
        received.update(ctx)
        return True

    sm = StateMachine("a")
    sm.add_transition("a", "b", "go", guard=guard)
    sm.trigger("go", context={"key": "value"})
    assert received["key"] == "value"


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_action_fires_on_transition():
    fired = []
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start", action=lambda ctx: fired.append(True))
    sm.trigger("start")
    assert fired == [True]


def test_action_not_fired_when_guard_blocks():
    fired = []
    sm = StateMachine("idle")
    sm.add_transition(
        "idle",
        "running",
        "start",
        guard=lambda ctx: False,
        action=lambda ctx: fired.append(True),
    )
    sm.trigger("start")
    assert fired == []


def test_action_receives_context():
    received = {}
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go", action=lambda ctx: received.update(ctx))
    sm.trigger("go", context={"msg": "hello"})
    assert received["msg"] == "hello"


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_history_records_transition():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start")
    sm.trigger("start")
    assert len(sm.history) == 1
    entry = sm.history[0]
    assert entry.from_state == "idle"
    assert entry.to_state == "running"
    assert entry.trigger == "start"


def test_history_records_context():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.trigger("go", context={"x": 1})
    assert sm.history[0].context == {"x": 1}


def test_history_grows_with_transitions():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "next")
    sm.add_transition("b", "c", "next")
    sm.trigger("next")
    sm.trigger("next")
    assert len(sm.history) == 2


def test_history_is_snapshot():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.trigger("go")
    snap = sm.history
    assert len(snap) == 1  # not affected by future triggers


# ---------------------------------------------------------------------------
# can_trigger
# ---------------------------------------------------------------------------


def test_can_trigger_true():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start")
    assert sm.can_trigger("start") is True


def test_can_trigger_false_wrong_event():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start")
    assert sm.can_trigger("stop") is False


def test_can_trigger_false_wrong_state():
    sm = StateMachine("idle")
    sm.add_transition("running", "done", "finish")
    assert sm.can_trigger("finish") is False


def test_can_trigger_respects_guard():
    sm = StateMachine("idle")
    sm.add_transition("idle", "running", "start", guard=lambda ctx: False)
    assert sm.can_trigger("start") is False


# ---------------------------------------------------------------------------
# available_triggers
# ---------------------------------------------------------------------------


def test_available_triggers():
    sm = StateMachine("idle")
    sm.add_transition("idle", "a", "go")
    sm.add_transition("idle", "b", "jump")
    sm.add_transition("running", "done", "stop")
    triggers = sm.available_triggers()
    assert set(triggers) == {"go", "jump"}


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_clears_history():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.trigger("go")
    sm.reset(state="a")
    assert sm.history == []


def test_reset_changes_state():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.trigger("go")
    sm.reset(state="a")
    assert sm.state == "a"


def test_reset_no_state_keeps_state():
    sm = StateMachine("a")
    sm.add_transition("a", "b", "go")
    sm.trigger("go")
    sm.reset()
    assert sm.state == "b"
    assert sm.history == []


# ---------------------------------------------------------------------------
# Multiple candidate transitions (guard fallthrough)
# ---------------------------------------------------------------------------


def test_first_matching_guard_wins():
    sm = StateMachine("idle")
    sm.add_transition("idle", "first", "go", guard=lambda ctx: True)
    sm.add_transition("idle", "second", "go", guard=lambda ctx: True)
    assert sm.trigger("go") is True
    assert sm.state == "first"


def test_falls_through_to_second_candidate_when_first_blocks():
    sm = StateMachine("idle")
    sm.add_transition("idle", "first", "go", guard=lambda ctx: False)
    sm.add_transition("idle", "second", "go", guard=lambda ctx: True)
    assert sm.trigger("go") is True
    assert sm.state == "second"


def test_all_candidates_blocked_returns_false_and_no_history():
    sm = StateMachine("idle")
    sm.add_transition("idle", "first", "go", guard=lambda ctx: False)
    sm.add_transition("idle", "second", "go", guard=lambda ctx: False)
    assert sm.trigger("go") is False
    assert sm.state == "idle"
    assert sm.history == []


# ---------------------------------------------------------------------------
# can_trigger with context
# ---------------------------------------------------------------------------


def test_can_trigger_respects_guard_with_context():
    sm = StateMachine("idle")
    sm.add_transition(
        "idle", "running", "start", guard=lambda ctx: ctx.get("ok", False)
    )
    assert sm.can_trigger("start", context={"ok": True}) is True
    assert sm.can_trigger("start", context={"ok": False}) is False


# ---------------------------------------------------------------------------
# Transition dataclass
# ---------------------------------------------------------------------------


def test_transition_dataclass_defaults():
    t = Transition("a", "b", "go")
    assert t.from_state == "a"
    assert t.to_state == "b"
    assert t.trigger == "go"
    assert t.guard is None
    assert t.action is None
