"""Business case service for the backend MVP."""

from fastapi import HTTPException, status

from app.services.mvp_store import store


class CaseService:
    def list_cases(self, user_id: str) -> list[dict]:
        return store.list_cases(user_id)

    def create_case(self, user_id: str, data: dict) -> dict:
        return store.create_case(user_id, data)

    def get_case(self, user_id: str, case_id: str) -> dict:
        case = store.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found",
            )
        return case

    def update_case(self, user_id: str, case_id: str, data: dict) -> dict:
        return store.update_case(user_id, case_id, data)

    def delete_case(self, user_id: str, case_id: str) -> None:
        store.delete_case(user_id, case_id)
