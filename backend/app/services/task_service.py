"""Investigation task service for the backend MVP."""

from app.services.mvp_store import store


class TaskService:
    def list_tasks(self, user_id: str, case_id: str) -> list[dict]:
        return store.list_tasks(user_id, case_id)

    def create_task(self, user_id: str, case_id: str, data: dict) -> dict:
        return store.create_task(user_id, case_id, data)

    def update_task(
        self,
        user_id: str,
        case_id: str,
        task_id: str,
        data: dict,
    ) -> dict:
        return store.update_task(user_id, case_id, task_id, data)

    def delete_task(self, user_id: str, case_id: str, task_id: str) -> None:
        store.delete_task(user_id, case_id, task_id)
