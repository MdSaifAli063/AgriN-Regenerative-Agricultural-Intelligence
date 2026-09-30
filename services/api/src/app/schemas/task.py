from typing import Any, Optional
from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    ready: bool
    result: Optional[Any] = None
