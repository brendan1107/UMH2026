"""
Evidence Uploads Routes

Handles file uploads for business case evidence.
Files are stored in Firebase Storage (when available) with metadata in Firestore.

Firestore path: business_cases/{case_id}/evidence_uploads/{upload_id}
Storage path:   cases/{case_id}/evidence/{uuid}.{ext}
"""
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from google.cloud import firestore

from app.config import settings
from app.db.session import get_db, get_storage_bucket
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.evidence_upload import EvidenceUpload
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()
logger = logging.getLogger(__name__)

SENSITIVE_FILE_MESSAGE = (
    "Sensitive configuration or credential files cannot be uploaded as evidence."
)

BLOCKED_PATTERNS = [
    "firebase-service-account",
    "service-account",
    ".env",
    "env.backend",
    "credentials.json",
]

BLOCKED_EXTENSIONS = [".pem", ".key", ".p12", ".pfx"]

ALLOWED_EXTENSIONS = [
    ".png", ".jpg", ".jpeg", ".webp",
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".csv", ".xls", ".xlsx",
]


def _upload_response(doc_id: str, data: dict) -> dict:
    """Build a consistent camelCase response dict for an upload document."""
    response_data = dict(data)
    response_data["id"] = doc_id
    return snake_dict_to_camel(response_data)


def _original_filename(upload_file: UploadFile) -> str:
    """Return a safe basename from the browser-provided filename."""
    filename = upload_file.filename or ""
    return filename.replace("\\", "/").split("/")[-1]


def _validate_upload_filename(filename: str) -> str:
    """Validate upload filename and return its lowercase extension."""
    lowered = filename.lower()
    if not lowered:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    if any(pattern in lowered for pattern in BLOCKED_PATTERNS):
        raise HTTPException(status_code=400, detail=SENSITIVE_FILE_MESSAGE)

    if any(lowered.endswith(ext) for ext in BLOCKED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=SENSITIVE_FILE_MESSAGE)

    extension = f".{lowered.rsplit('.', 1)[1]}" if "." in lowered else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    return extension


def _get_case_ref(db, case_id: str, user_uid: str):
    """Verify case exists and belongs to user."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    if case_doc.to_dict().get("user_id") != user_uid:
        raise HTTPException(status_code=403, detail="Not authorized")
    return case_ref


def _created_at_order_field(upload_data: dict) -> str:
    return str(upload_data.get("createdAt") or upload_data.get("created_at") or "")


@router.post("/{case_id}/upload")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload evidence file for a case."""
    original_filename = _original_filename(file)
    logger.info(
        "Upload route reached: case_id=%s original_filename=%s",
        case_id,
        original_filename,
    )

    case_ref = _get_case_ref(db, case_id, user["uid"])
    extension = _validate_upload_filename(original_filename)

    contents = await file.read()
    file_size = len(contents)
    upload_id = uuid.uuid4().hex
    storage_path_candidate = f"cases/{case_id}/evidence/{upload_id}{extension}"
    is_image = (file.content_type or "").startswith("image")
    content_type = file.content_type or "application/octet-stream"
    logger.info("Upload file size: case_id=%s file_size=%s", case_id, file_size)

    bucket_name = settings.FIREBASE_STORAGE_BUCKET or ""
    bucket = get_storage_bucket()
    logger.info(
        "Firebase Storage bucket configured: %s bucket_name=%s fallback_mode=%s",
        bool(bucket_name),
        bucket_name or "(none)",
        "metadata_only" if bucket is None else "firebase_storage",
    )

    url = ""
    storage_path = ""
    storage_mode = "metadata_only"

    if bucket is not None:
        storage_mode = "firebase_storage"
        try:
            download_token = uuid.uuid4().hex
            blob = bucket.blob(storage_path_candidate)
            blob.metadata = {"firebaseStorageDownloadTokens": download_token}
            blob.upload_from_string(contents, content_type=content_type)
            storage_path = storage_path_candidate
            url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
                f"{quote(storage_path, safe='')}?alt=media&token={download_token}"
            )
            logger.info(
                "Uploaded file to Firebase Storage: bucket=%s storage_path=%s",
                bucket.name,
                storage_path,
            )
        except Exception as exc:
            logger.exception(
                "Firebase Storage upload failed: storage_path=%s",
                storage_path_candidate,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Firebase Storage upload failed: {exc}",
            ) from exc
    elif bucket_name:
        logger.error(
            "FIREBASE_STORAGE_BUCKET is configured but Storage bucket is unavailable: %s",
            bucket_name,
        )
        raise HTTPException(
            status_code=503,
            detail="Firebase Storage bucket is configured but unavailable.",
        )
    else:
        logger.warning(
            "Firebase Storage bucket is not configured; using metadata-only upload mode."
        )

    size_display = (
        f"{file_size / (1024 * 1024):.1f} MB"
        if file_size >= 1024 * 1024
        else f"{file_size / 1024:.1f} KB"
    )
    now = datetime.now(timezone.utc)

    upload_dict = {
        "id": upload_id,
        "caseId": case_id,
        "fileName": original_filename,
        "fileType": content_type,
        "fileSize": file_size,
        "storagePath": storage_path,
        "url": url,
        "createdAt": now,
        "storageMode": storage_mode,
        "name": original_filename,
        "size": size_display,
        "type": "image" if is_image else "document",
    }

    upload_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).document(upload_id)
    firestore_path = (
        f"{BusinessCase.COLLECTION}/{case_id}/"
        f"{EvidenceUpload.SUBCOLLECTION}/{upload_id}"
    )
    upload_ref.set(upload_dict)
    logger.info("Wrote upload metadata to Firestore: %s", firestore_path)

    return _upload_response(upload_ref.id, upload_dict)


@router.get("/{case_id}")
@router.get("/{case_id}/uploads")
async def list_uploads(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all uploaded evidence files for a case."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    uploads_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).stream()

    uploads = [_upload_response(doc.id, doc.to_dict()) for doc in uploads_ref]
    uploads.sort(key=_created_at_order_field)
    return uploads


@router.delete("/{case_id}/{upload_id}")
async def delete_upload(
    case_id: str,
    upload_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete an upload: removes Firestore metadata and Storage file if present."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    upload_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).document(upload_id)
    doc = upload_ref.get()

    if not doc.exists:
        logger.info(
            "Upload delete requested for already-deleted upload: case_id=%s upload_id=%s",
            case_id,
            upload_id,
        )
        return {"status": "success", "alreadyDeleted": True}

    data = doc.to_dict()
    storage_path = data.get("storagePath") or data.get("storage_path")
    bucket_name = settings.FIREBASE_STORAGE_BUCKET or ""

    if storage_path:
        bucket = get_storage_bucket()
        if bucket is not None:
            try:
                blob = bucket.blob(storage_path)
                if blob.exists():
                    blob.delete()
                    logger.info("Deleted file from Firebase Storage: %s", storage_path)
                else:
                    logger.warning("Storage file was already missing: %s", storage_path)
            except Exception as exc:
                logger.exception("Failed to delete from Firebase Storage: %s", storage_path)
                raise HTTPException(
                    status_code=502,
                    detail=f"Firebase Storage delete failed: {exc}",
                ) from exc
        elif bucket_name:
            raise HTTPException(
                status_code=503,
                detail="Firebase Storage bucket is configured but unavailable.",
            )

    upload_ref.delete()
    return {"status": "success"}
