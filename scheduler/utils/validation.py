"""
Input validation helpers.

Centralized here so every entry point (random generation, custom process
input, CLI args) validates the same way instead of each call site
re-inventing (and potentially disagreeing on) what counts as valid input.
"""

from typing import List, Dict, Any
from scheduler.config import CONFIG


class ValidationError(ValueError):
    """Raised when input to the simulator is invalid. Caught at the CLI/API
    boundary and reported to the user with a clear message — never silently
    swallowed."""
    pass


def validate_process_count(n: int) -> None:
    if not isinstance(n, int):
        raise ValidationError(f"Process count must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValidationError(f"Process count cannot be negative (got {n})")
    if n > CONFIG.max_processes_hard_limit:
        raise ValidationError(
            f"Process count {n} exceeds hard limit of {CONFIG.max_processes_hard_limit}"
        )


def validate_quantum(quantum: int) -> None:
    if not isinstance(quantum, int) or quantum < 1:
        raise ValidationError(f"Quantum must be a positive integer, got {quantum!r}")


def validate_process_dict(p: Dict[str, Any], index: int) -> None:
    """Validate a single custom process record before it becomes a Process object."""
    required = ("arrival_time", "burst_time")
    for field in required:
        if field not in p:
            raise ValidationError(f"Process at index {index} is missing required field '{field}'")

    arrival = p["arrival_time"]
    burst = p["burst_time"]
    priority = p.get("priority", 0)

    if not isinstance(arrival, (int, float)) or arrival < 0:
        raise ValidationError(f"Process at index {index}: arrival_time must be >= 0, got {arrival!r}")
    if arrival > CONFIG.max_arrival_time:
        raise ValidationError(f"Process at index {index}: arrival_time {arrival} exceeds max allowed")

    if not isinstance(burst, (int, float)) or burst <= 0:
        raise ValidationError(f"Process at index {index}: burst_time must be > 0, got {burst!r}")
    if burst > CONFIG.max_burst_time:
        raise ValidationError(f"Process at index {index}: burst_time {burst} exceeds max allowed")

    if not isinstance(priority, (int, float)):
        raise ValidationError(f"Process at index {index}: priority must be numeric, got {priority!r}")


def validate_custom_processes(records: List[Dict[str, Any]]) -> None:
    if not isinstance(records, list):
        raise ValidationError("Custom process input must be a list of records")
    validate_process_count(len(records))
    for i, record in enumerate(records):
        validate_process_dict(record, i)
