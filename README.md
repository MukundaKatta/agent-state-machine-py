# agent-state-machine-py

Simple finite state machine for agent step orchestration.

```bash
pip install agent-state-machine-py
```

## Quick start

```python
from agent_state_machine import StateMachine

sm = StateMachine("idle")
sm.add_transition("idle", "gathering", "start")
sm.add_transition("gathering", "responding", "done")
sm.add_transition("responding", "idle", "reset")

sm.trigger("start")
assert sm.state == "gathering"

sm.trigger("done")
assert sm.state == "responding"
```

## Guards and actions

```python
sm.add_transition(
    "idle", "running", "start",
    guard=lambda ctx: ctx.get("ready", False),
    action=lambda ctx: print(f"Starting with {ctx}"),
)

sm.trigger("start", context={"ready": True})  # fires
sm.trigger("start", context={"ready": False}) # guard blocks, returns False
```

## API

```python
StateMachine(initial_state: str)

sm.add_transition(from_state, to_state, trigger, guard=None, action=None)
sm.trigger(event, context={}) -> bool       # True if transitioned, False if guard blocked
sm.can_trigger(event, context={}) -> bool
sm.available_triggers() -> list[str]
sm.state -> str
sm.history -> list[HistoryEntry]            # .from_state, .to_state, .trigger, .context
sm.reset(state=None)                        # clear history, optionally jump to a state
```

## Zero dependencies
