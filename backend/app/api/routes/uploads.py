"""Evidence upload routes."""

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies import get_current_user
from app.schemas.upload import UploadEnvelope, UploadListEnvelope
from app.services.upload_service import UploadService

router = APIRouter()
service = UploadService()


def _uid(current_user: dict) -> str:
    return current_user["uid"]


@router.get("/{case_id}", response_model=UploadListEnvelope)
async def list_uploads(case_id: str, current_user: dict = Depends(get_current_user)):
    return {"data": await service.list_uploads(_uid(current_user), case_id)}


@router.post("/{case_id}", response_model=UploadEnvelope, status_code=status.HTTP_201_CREATED)
async def upload_file(
    case_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    upload = await service.upload_file(_uid(current_user), case_id, file)
    return {"data": upload}


@router.delete("/{case_id}/{upload_id}")
async def delete_upload(
    case_id: str,
    upload_id: str,
    current_user: dict = Depends(get_current_user),
):
    await service.delete_upload(_uid(current_user), case_id, upload_id)
    return {"data": {"id": upload_id, "caseId": case_id, "deleted": True}}
