"""Evidence upload service for the backend MVP."""

from fastapi import HTTPException, UploadFile, status

from app.services.mvp_store import store


class UploadService:
    async def list_uploads(self, user_id: str, case_id: str) -> list[dict]:
        return store.list_uploads(user_id, case_id)

    async def upload_file(self, user_id: str, case_id: str, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must have a filename",
            )

        file_bytes = await file.read()
        return store.create_upload(
            uid=user_id,
            case_id=case_id,
            file_name=file.filename,
            file_type=file.content_type,
            file_size=len(file_bytes),
            file_bytes=file_bytes,
        )

    async def delete_upload(self, user_id: str, case_id: str, upload_id: str) -> None:
        store.delete_upload(user_id, case_id, upload_id)
