"""Case CRUD routes."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user
from app.schemas.business_case import CaseCreate, CaseEnvelope, CaseListEnvelope, CaseUpdate
from app.services.case_service import CaseService

router = APIRouter()
service = CaseService()


def _uid(current_user: dict) -> str:
    return current_user["uid"]


@router.get("", response_model=CaseListEnvelope)
async def list_cases(current_user: dict = Depends(get_current_user)):
    return {"data": service.list_cases(_uid(current_user))}


@router.post("", response_model=CaseEnvelope, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    current_user: dict = Depends(get_current_user),
):
    return {"data": service.create_case(_uid(current_user), payload.model_dump())}


@router.get("/{case_id}", response_model=CaseEnvelope)
async def get_case(case_id: str, current_user: dict = Depends(get_current_user)):
    return {"data": service.get_case(_uid(current_user), case_id)}


@router.put("/{case_id}", response_model=CaseEnvelope)
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    current_user: dict = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    return {"data": service.update_case(_uid(current_user), case_id, updates)}


@router.delete("/{case_id}")
async def delete_case(case_id: str, current_user: dict = Depends(get_current_user)):
    service.delete_case(_uid(current_user), case_id)
    return {"data": {"id": case_id, "deleted": True}}
