#!/usr/bin/env python3
"""
Phase 2.2: State Machine for Workflow Lifecycle Management
Tracks case lifecycle states and state transitions
"""

import logging
from enum import Enum
from typing import Dict, Callable, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CaseState(Enum):
    """Case lifecycle states matching workflow phases"""
    PENDING = "PENDING"  # Initial state, waiting to be investigated
    INVESTIGATING = "INVESTIGATING"  # Gathering evidence and context
    VALIDATING = "VALIDATING"  # Checking against policies and rules
    REMEDIATING = "REMEDIATING"  # Taking corrective action
    RESOLVED = "RESOLVED"  # Successfully handled
    FAILED = "FAILED"  # Failed to resolve
    CANCELLED = "CANCELLED"  # Manually cancelled


@dataclass
class StateTransition:
    """Metadata for a state transition"""
    from_state: CaseState
    to_state: CaseState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateMachine:
    """Manages case state transitions with validation"""
    
    # Define valid state transitions
    VALID_TRANSITIONS = {
        CaseState.PENDING: [CaseState.INVESTIGATING, CaseState.CANCELLED],
        CaseState.INVESTIGATING: [CaseState.VALIDATING, CaseState.FAILED, CaseState.CANCELLED],
        CaseState.VALIDATING: [CaseState.REMEDIATING, CaseState.FAILED, CaseState.CANCELLED],
        CaseState.REMEDIATING: [CaseState.RESOLVED, CaseState.FAILED, CaseState.CANCELLED],
        CaseState.RESOLVED: [],  # Terminal state
        CaseState.FAILED: [],  # Terminal state
        CaseState.CANCELLED: [],  # Terminal state
    }
    
    def __init__(self, case_id: str, initial_state: CaseState = CaseState.PENDING):
        self.case_id = case_id
        self.current_state = initial_state
        self.transitions: list[StateTransition] = []
        self.state_handlers: Dict[CaseState, list[Callable]] = {
            state: [] for state in CaseState
        }
        self.created_at = datetime.utcnow()
        
    def register_handler(self, state: CaseState, handler: Callable):
        """Register a callback handler for state entry"""
        self.state_handlers[state].append(handler)
        logger.info(f"Registered handler {handler.__name__} for state {state.value}")
    
    async def transition(self, new_state: CaseState, reason: str = "", metadata: Dict[str, Any] = None) -> bool:
        """Attempt to transition to a new state"""
        if metadata is None:
            metadata = {}
        
        # Validate transition
        if not self._is_valid_transition(self.current_state, new_state):
            logger.warning(
                f"Invalid transition: {self.current_state.value} -> {new_state.value} "
                f"for case {self.case_id}"
            )
            return False
        
        old_state = self.current_state
        
        # Record transition
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            reason=reason,
            metadata=metadata
        )
        self.transitions.append(transition)
        
        # Update state
        self.current_state = new_state
        logger.info(
            f"Case {self.case_id} transitioned: {old_state.value} -> {new_state.value} "
            f"(Reason: {reason})"
        )
        
        # Call registered handlers
        for handler in self.state_handlers[new_state]:
            try:
                if hasattr(handler, '__call__'):
                    if hasattr(handler, '__await__'):
                        await handler(self)
                    else:
                        handler(self)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}")
        
        return True
    
    def _is_valid_transition(self, from_state: CaseState, to_state: CaseState) -> bool:
        """Check if a transition is valid"""
        return to_state in self.VALID_TRANSITIONS.get(from_state, [])
    
    def get_state(self) -> CaseState:
        """Get current state"""
        return self.current_state
    
    def get_transitions(self) -> list[StateTransition]:
        """Get all state transitions for this case"""
        return self.transitions.copy()
    
    def get_duration_in_state(self) -> float:
        """Get seconds since entering current state"""
        if not self.transitions:
            return (datetime.utcnow() - self.created_at).total_seconds()
        
        last_transition = self.transitions[-1]
        return (datetime.utcnow() - last_transition.timestamp).total_seconds()
    
    def get_total_duration(self) -> float:
        """Get total case duration"""
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def is_terminal(self) -> bool:
        """Check if case is in a terminal state"""
        return self.current_state in [
            CaseState.RESOLVED,
            CaseState.FAILED,
            CaseState.CANCELLED
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state machine to dict for serialization"""
        return {
            "case_id": self.case_id,
            "current_state": self.current_state.value,
            "is_terminal": self.is_terminal(),
            "created_at": self.created_at.isoformat(),
            "total_duration_seconds": self.get_total_duration(),
            "duration_in_current_state_seconds": self.get_duration_in_state(),
            "transitions": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason
                }
                for t in self.transitions
            ]
        }


class StateMachineManager:
    """Manages multiple state machines for different cases"""
    
    def __init__(self):
        self.machines: Dict[str, StateMachine] = {}
    
    def create_machine(self, case_id: str, initial_state: CaseState = CaseState.PENDING) -> StateMachine:
        """Create a new state machine"""
        if case_id in self.machines:
            logger.warning(f"State machine for case {case_id} already exists")
            return self.machines[case_id]
        
        machine = StateMachine(case_id, initial_state)
        self.machines[case_id] = machine
        logger.info(f"Created state machine for case {case_id}")
        return machine
    
    def get_machine(self, case_id: str) -> Optional[StateMachine]:
        """Get existing state machine"""
        return self.machines.get(case_id)
    
    async def transition(self, case_id: str, new_state: CaseState, reason: str = "") -> bool:
        """Transition a case to a new state"""
        machine = self.get_machine(case_id)
        if not machine:
            logger.error(f"State machine for case {case_id} not found")
            return False
        
        return await machine.transition(new_state, reason)
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current state of all cases"""
        return {
            case_id: machine.to_dict()
            for case_id, machine in self.machines.items()
        }


# Example usage
async def main():
    manager = StateMachineManager()
    
    # Create state machine for a case
    machine = manager.create_machine("case-123")
    
    # Register handlers
    def on_investigating(m):
        print(f"Starting investigation for {m.case_id}")
    
    def on_resolved(m):
        print(f"Case {m.case_id} resolved successfully")
    
    machine.register_handler(CaseState.INVESTIGATING, on_investigating)
    machine.register_handler(CaseState.RESOLVED, on_resolved)
    
    # Perform transitions
    await machine.transition(CaseState.INVESTIGATING, "User reported spam")
    await machine.transition(CaseState.VALIDATING, "Evidence gathered")
    await machine.transition(CaseState.REMEDIATING, "Policy violation confirmed")
    await machine.transition(CaseState.RESOLVED, "Account suspended")
    
    # Print final state
    print("\nFinal State:")
    import json
    print(json.dumps(machine.to_dict(), indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
