from dataclasses import dataclass


@dataclass(slots=True)
class WorkflowResult:

    success: bool

    message: str