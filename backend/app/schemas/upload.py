"""Evidence upload response schemas."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: str
    caseId: str
    fileName: str
    fileType: str | None
    fileSize: int | None
    url: str | None
    createdAt: str


class UploadListEnvelope(BaseModel):
    data: list[UploadResponse]


class UploadEnvelope(BaseModel):
    data: UploadResponse
