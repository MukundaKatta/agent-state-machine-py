"""agent-state-machine-py — simple FSM for agent step orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Transition:
    from_state: str
    to_state: str
    trigger: str
    guard: Callable[[dict], bool] | None = None
    action: Callable[[dict], None] | None = None


@dataclass
class HistoryEntry:
    from_state: str
    to_state: str
    trigger: str
    context: dict


class InvalidTransitionError(Exception):
    """Raised when no valid transition exists for the given event."""


class StateMachine:
    """
    Finite state machine for orchestrating multi-step agent workflows.

    Example::

        sm = StateMachine("idle")
        sm.add_transition("idle", "gathering", "start")
        sm.add_transition("gathering", "responding", "done")
        sm.trigger("start")
        assert sm.state == "gathering"
    """

    def __init__(self, initial_state: str) -> None:
        self._state = initial_state
        self._transitions: list[Transition] = []
        self._history: list[HistoryEntry] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def history(self) -> list[HistoryEntry]:
        return list(self._history)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        trigger: str,
        guard: Callable[[dict], bool] | None = None,
        action: Callable[[dict], None] | None = None,
    ) -> None:
        """Register a transition."""
        self._transitions.append(
            Transition(from_state, to_state, trigger, guard, action)
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def trigger(self, event: str, context: dict | None = None) -> bool:
        """
        Fire an event. Returns True if a transition happened, False otherwise.
        Raises InvalidTransitionError if the event is unknown from the current state.
        """
        ctx = context or {}
        candidates = [
            t for t in self._transitions
            if t.from_state == self._state and t.trigger == event
        ]
        if not candidates:
            raise InvalidTransitionError(
                f"No transition from '{self._state}' on event '{event}'"
            )
        for t in candidates:
            if t.guard is None or t.guard(ctx):
                prev = self._state
                self._state = t.to_state
                self._history.append(
                    HistoryEntry(prev, t.to_state, event, dict(ctx))
                )
                if t.action:
                    t.action(ctx)
                return True
        return False  # Guard blocked all candidates

    def can_trigger(self, event: str, context: dict | None = None) -> bool:
        """Return True if the event would result in a transition."""
        ctx = context or {}
        return any(
            t.from_state == self._state
            and t.trigger == event
            and (t.guard is None or t.guard(ctx))
            for t in self._transitions
        )

    def available_triggers(self) -> list[str]:
        """List all events that can fire from the current state."""
        return [t.trigger for t in self._transitions if t.from_state == self._state]

    def reset(self, state: str | None = None) -> None:
        """Reset to a given state (defaults to keeping current, clears history)."""
        if state is not None:
            self._state = state
        self._history.clear()


__all__ = ["StateMachine", "Transition", "HistoryEntry", "InvalidTransitionError"]
