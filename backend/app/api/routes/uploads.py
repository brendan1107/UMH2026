from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from google.cloud import firestore
from firebase_admin import storage
from datetime import datetime
import time
import uuid

from app.db.session import get_db, get_storage_bucket
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.evidence_upload import EvidenceUpload

router = APIRouter()

@router.post("/{case_id}/upload")
async def upload_evidence(
    case_id: str, 
    file: UploadFile = File(...),
    db: firestore.Client = Depends(get_db),
    bucket: storage.bucket = Depends(get_storage_bucket),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    if not case_ref.get().exists:
        raise HTTPException(status_code=404, detail="Case not found")

    # Upload to Storage
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    blob_name = f"cases/{case_id}/evidence/{uuid.uuid4()}.{ext}"
    blob = bucket.blob(blob_name)
    
    contents = await file.read()
    blob.upload_from_string(contents, content_type=file.content_type)
    blob.make_public()
    
    public_url = blob.public_url

    # Store metadata in Firestore
    size_mb = f"{len(contents) / (1024 * 1024):.1f} MB"
    is_image = file.content_type.startswith("image")
    
    upload = EvidenceUpload(
        case_id=case_id,
        name=file.filename,
        size=size_mb,
        type="image" if is_image else "document",
        url=public_url,
        storage_path=blob_name
    )
    
    upload_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).document()
    upload_dict = upload.to_dict()
    upload_ref.set(upload_dict)
    
    upload_dict["id"] = upload_ref.id
    return upload_dict

@router.get("/{case_id}/uploads")
async def list_uploads(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    uploads_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).stream()
    
    uploads = []
    for doc in uploads_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        uploads.append(data)
        
    return uploads

@router.delete("/{case_id}/uploads/{upload_id}")
async def delete_upload(
    case_id: str,
    upload_id: str,
    db: firestore.Client = Depends(get_db),
    bucket: storage.bucket = Depends(get_storage_bucket),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    upload_ref = case_ref.collection(EvidenceUpload.SUBCOLLECTION).document(upload_id)
    doc = upload_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Upload not found")
        
    data = doc.to_dict()
    
    # Delete from storage
    if data.get("storage_path"):
        blob = bucket.blob(data["storage_path"])
        if blob.exists():
            blob.delete()
            
    # Delete from Firestore
    upload_ref.delete()
    return {"status": "success"}
