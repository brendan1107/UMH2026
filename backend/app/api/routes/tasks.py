"""Task CRUD routes scoped to a case."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user
from app.schemas.task import TaskCreate, TaskEnvelope, TaskListEnvelope, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter()
service = TaskService()


def _uid(current_user: dict) -> str:
    return current_user["uid"]


@router.get("/{case_id}", response_model=TaskListEnvelope)
async def list_tasks(case_id: str, current_user: dict = Depends(get_current_user)):
    return {"data": service.list_tasks(_uid(current_user), case_id)}


@router.post("/{case_id}", response_model=TaskEnvelope, status_code=status.HTTP_201_CREATED)
async def create_task(
    case_id: str,
    payload: TaskCreate,
    current_user: dict = Depends(get_current_user),
):
    return {"data": service.create_task(_uid(current_user), case_id, payload.model_dump())}


@router.put("/{case_id}/{task_id}", response_model=TaskEnvelope)
async def update_task(
    case_id: str,
    task_id: str,
    payload: TaskUpdate,
    current_user: dict = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    return {"data": service.update_task(_uid(current_user), case_id, task_id, updates)}


@router.delete("/{case_id}/{task_id}")
async def delete_task(
    case_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    service.delete_task(_uid(current_user), case_id, task_id)
    return {"data": {"id": task_id, "caseId": case_id, "deleted": True}}
