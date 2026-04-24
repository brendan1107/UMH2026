"""Small persistence layer for the cases/tasks/uploads MVP.

Firestore is used when it is reachable. If initialization or an operation fails,
the store switches to in-memory data for the current process so local demos keep
working without Firebase services.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePath
import re
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.db.database import bucket as firebase_bucket
from app.db.database import db as firestore_db


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return uuid4().hex


def public_case(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data["id"],
        "title": data["title"],
        "description": data.get("description"),
        "businessStage": data.get("businessStage"),
        "status": data["status"],
        "createdAt": data["createdAt"],
        "updatedAt": data["updatedAt"],
    }


def public_task(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data["id"],
        "caseId": data["caseId"],
        "title": data["title"],
        "description": data.get("description"),
        "type": data["type"],
        "status": data["status"],
        "actionLabel": data.get("actionLabel"),
        "createdAt": data["createdAt"],
        "updatedAt": data["updatedAt"],
    }


def public_upload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data["id"],
        "caseId": data["caseId"],
        "fileName": data["fileName"],
        "fileType": data.get("fileType"),
        "fileSize": data.get("fileSize"),
        "url": data.get("url"),
        "createdAt": data["createdAt"],
    }


class MvpStore:
    def __init__(self):
        self.db = firestore_db
        self.bucket = firebase_bucket
        self.firestore_disabled = firestore_db is None
        self.lock = Lock()
        self.memory: dict[str, dict[str, Any]] = {}

    def _disable_firestore(self):
        self.firestore_disabled = True

    def _use_firestore(self) -> bool:
        return self.db is not None and not self.firestore_disabled

    def _user_memory(self, uid: str) -> dict[str, Any]:
        return self.memory.setdefault(
            uid,
            {
                "cases": {},
                "tasks": {},
                "uploads": {},
            },
        )

    def _cases_ref(self, uid: str):
        return self.db.collection("users").document(uid).collection("cases")

    def _tasks_ref(self, uid: str, case_id: str):
        return self._cases_ref(uid).document(case_id).collection("tasks")

    def _uploads_ref(self, uid: str, case_id: str):
        return self._cases_ref(uid).document(case_id).collection("uploads")

    def _doc_data(self, doc) -> dict[str, Any] | None:
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    def _memory_case(self, uid: str, case_id: str) -> dict[str, Any] | None:
        return self._user_memory(uid)["cases"].get(case_id)

    def _require_case(self, uid: str, case_id: str) -> dict[str, Any]:
        case = self.get_case(uid, case_id)
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found",
            )
        with self.lock:
            self._user_memory(uid)["cases"].setdefault(case_id, deepcopy(case))
        return case

    def list_cases(self, uid: str) -> list[dict[str, Any]]:
        if self._use_firestore():
            try:
                items = [
                    public_case(data)
                    for doc in self._cases_ref(uid).stream()
                    if (data := self._doc_data(doc)) is not None
                ]
                return sorted(items, key=lambda item: item["updatedAt"], reverse=True)
            except Exception:
                self._disable_firestore()

        with self.lock:
            cases = [public_case(deepcopy(item)) for item in self._user_memory(uid)["cases"].values()]
        return sorted(cases, key=lambda item: item["updatedAt"], reverse=True)

    def create_case(self, uid: str, data: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        case = {
            "id": new_id(),
            "title": data["title"],
            "description": data.get("description"),
            "businessStage": data.get("businessStage"),
            "status": data.get("status", "active"),
            "createdAt": now,
            "updatedAt": now,
        }

        if self._use_firestore():
            try:
                self._cases_ref(uid).document(case["id"]).set(case)
                return public_case(case)
            except Exception:
                self._disable_firestore()

        with self.lock:
            self._user_memory(uid)["cases"][case["id"]] = deepcopy(case)
        return public_case(case)

    def get_case(self, uid: str, case_id: str) -> dict[str, Any] | None:
        if self._use_firestore():
            try:
                data = self._doc_data(self._cases_ref(uid).document(case_id).get())
                return public_case(data) if data is not None else None
            except Exception:
                self._disable_firestore()

        with self.lock:
            data = self._memory_case(uid, case_id)
            return public_case(deepcopy(data)) if data is not None else None

    def update_case(self, uid: str, case_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        self._require_case(uid, case_id)
        updates = {**updates, "updatedAt": utc_now()}

        if self._use_firestore():
            try:
                ref = self._cases_ref(uid).document(case_id)
                ref.update(updates)
                data = self._doc_data(ref.get())
                return public_case(data)
            except Exception:
                self._disable_firestore()

        with self.lock:
            case = self._memory_case(uid, case_id)
            if case is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Case not found",
                )
            case.update(updates)
            return public_case(deepcopy(case))

    def delete_case(self, uid: str, case_id: str) -> None:
        self._require_case(uid, case_id)

        if self._use_firestore():
            try:
                for upload in self._uploads_ref(uid, case_id).stream():
                    upload_data = self._doc_data(upload)
                    self.delete_storage_file(upload_data.get("storagePath") if upload_data else None)
                    upload.reference.delete()
                for task in self._tasks_ref(uid, case_id).stream():
                    task.reference.delete()
                self._cases_ref(uid).document(case_id).delete()
                return
            except Exception:
                self._disable_firestore()

        with self.lock:
            user_data = self._user_memory(uid)
            for upload in user_data["uploads"].get(case_id, {}).values():
                self.delete_storage_file(upload.get("storagePath"))
            user_data["uploads"].pop(case_id, None)
            user_data["tasks"].pop(case_id, None)
            user_data["cases"].pop(case_id, None)

    def list_tasks(self, uid: str, case_id: str) -> list[dict[str, Any]]:
        self._require_case(uid, case_id)

        if self._use_firestore():
            try:
                items = [
                    public_task(data)
                    for doc in self._tasks_ref(uid, case_id).stream()
                    if (data := self._doc_data(doc)) is not None
                ]
                return sorted(items, key=lambda item: item["createdAt"])
            except Exception:
                self._disable_firestore()

        with self.lock:
            tasks = [
                public_task(deepcopy(item))
                for item in self._user_memory(uid)["tasks"].get(case_id, {}).values()
            ]
        return sorted(tasks, key=lambda item: item["createdAt"])

    def create_task(self, uid: str, case_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._require_case(uid, case_id)
        now = utc_now()
        task = {
            "id": new_id(),
            "caseId": case_id,
            "title": data["title"],
            "description": data.get("description"),
            "type": data.get("type", "provide_text_input"),
            "status": data.get("status", "pending"),
            "actionLabel": data.get("actionLabel"),
            "createdAt": now,
            "updatedAt": now,
        }

        if self._use_firestore():
            try:
                self._tasks_ref(uid, case_id).document(task["id"]).set(task)
                return public_task(task)
            except Exception:
                self._disable_firestore()

        with self.lock:
            self._user_memory(uid)["tasks"].setdefault(case_id, {})[task["id"]] = deepcopy(task)
        return public_task(task)

    def update_task(
        self,
        uid: str,
        case_id: str,
        task_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_case(uid, case_id)
        updates = {**updates, "updatedAt": utc_now()}

        if self._use_firestore():
            try:
                ref = self._tasks_ref(uid, case_id).document(task_id)
                if not ref.get().exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Task not found",
                    )
                ref.update(updates)
                data = self._doc_data(ref.get())
                return public_task(data)
            except HTTPException:
                raise
            except Exception:
                self._disable_firestore()

        with self.lock:
            task = self._user_memory(uid)["tasks"].get(case_id, {}).get(task_id)
            if task is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found",
                )
            task.update(updates)
            return public_task(deepcopy(task))

    def delete_task(self, uid: str, case_id: str, task_id: str) -> None:
        self._require_case(uid, case_id)

        if self._use_firestore():
            try:
                ref = self._tasks_ref(uid, case_id).document(task_id)
                if not ref.get().exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Task not found",
                    )
                ref.delete()
                return
            except HTTPException:
                raise
            except Exception:
                self._disable_firestore()

        with self.lock:
            tasks = self._user_memory(uid)["tasks"].get(case_id, {})
            if task_id not in tasks:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found",
                )
            tasks.pop(task_id)

    def list_uploads(self, uid: str, case_id: str) -> list[dict[str, Any]]:
        self._require_case(uid, case_id)

        if self._use_firestore():
            try:
                items = [
                    public_upload(data)
                    for doc in self._uploads_ref(uid, case_id).stream()
                    if (data := self._doc_data(doc)) is not None
                ]
                return sorted(items, key=lambda item: item["createdAt"], reverse=True)
            except Exception:
                self._disable_firestore()

        with self.lock:
            uploads = [
                public_upload(deepcopy(item))
                for item in self._user_memory(uid)["uploads"].get(case_id, {}).values()
            ]
        return sorted(uploads, key=lambda item: item["createdAt"], reverse=True)

    def create_upload(
        self,
        uid: str,
        case_id: str,
        file_name: str,
        file_type: str | None,
        file_size: int,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        self._require_case(uid, case_id)
        upload_id = new_id()
        url, storage_path = self.upload_storage_file(
            uid=uid,
            case_id=case_id,
            upload_id=upload_id,
            file_name=file_name,
            file_type=file_type,
            file_bytes=file_bytes,
        )
        upload = {
            "id": upload_id,
            "caseId": case_id,
            "fileName": file_name,
            "fileType": file_type,
            "fileSize": file_size,
            "url": url,
            "storagePath": storage_path,
            "createdAt": utc_now(),
        }

        if self._use_firestore():
            try:
                self._uploads_ref(uid, case_id).document(upload_id).set(upload)
                return public_upload(upload)
            except Exception:
                self._disable_firestore()

        with self.lock:
            self._user_memory(uid)["uploads"].setdefault(case_id, {})[upload_id] = deepcopy(upload)
        return public_upload(upload)

    def delete_upload(self, uid: str, case_id: str, upload_id: str) -> None:
        self._require_case(uid, case_id)

        if self._use_firestore():
            try:
                ref = self._uploads_ref(uid, case_id).document(upload_id)
                data = self._doc_data(ref.get())
                if data is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Upload not found",
                    )
                self.delete_storage_file(data.get("storagePath"))
                ref.delete()
                return
            except HTTPException:
                raise
            except Exception:
                self._disable_firestore()

        with self.lock:
            uploads = self._user_memory(uid)["uploads"].get(case_id, {})
            upload = uploads.get(upload_id)
            if upload is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Upload not found",
                )
            self.delete_storage_file(upload.get("storagePath"))
            uploads.pop(upload_id)

    def upload_storage_file(
        self,
        uid: str,
        case_id: str,
        upload_id: str,
        file_name: str,
        file_type: str | None,
        file_bytes: bytes,
    ) -> tuple[str | None, str | None]:
        if self.bucket is None:
            return None, None

        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", PurePath(file_name).name).strip("_")
        safe_name = safe_name or "upload"
        storage_path = f"users/{uid}/cases/{case_id}/uploads/{upload_id}/{safe_name}"

        try:
            blob = self.bucket.blob(storage_path)
            blob.upload_from_string(file_bytes, content_type=file_type)
            try:
                blob.make_public()
                return blob.public_url, storage_path
            except Exception:
                return None, storage_path
        except Exception:
            return None, None

    def delete_storage_file(self, storage_path: str | None) -> None:
        if self.bucket is None or not storage_path:
            return
        try:
            self.bucket.blob(storage_path).delete()
        except Exception:
            return


store = MvpStore()
