"""Taskade API client for HTTP operations."""

from typing import Optional, Any
import asyncio
import httpx
import structlog

from config import get_settings

logger = structlog.get_logger()


class TaskadeClient:
    """Async client for Taskade API integration."""

    def __init__(self):
        settings = get_settings()
        self.workspace_id = settings.taskade_workspace_id
        self.project_entities = settings.taskade_project_entities
        self.base_url = settings.taskade_base_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with authentication."""
        if self._client is None or self._client.is_closed:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {settings.taskade_api_token.get_secret_value()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ==================== Task Operations ====================

    async def get_tasks(self, project_id: str) -> list[dict[str, Any]]:
        """Get all tasks in a project, including nested children."""
        client = await self._get_client()
        response = await client.get(f"/projects/{project_id}/tasks")
        response.raise_for_status()
        
        all_tasks = response.json().get("items", [])
        
        # Flatten nested tasks - extract children recursively
        def extract_all_tasks(tasks: list[dict]) -> list[dict]:
            result = []
            for task in tasks:
                result.append(task)
                # If task has children, recursively extract them
                if "tasks" in task and task["tasks"]:
                    result.extend(extract_all_tasks(task["tasks"]))
            return result
        
        return extract_all_tasks(all_tasks)

    async def get_task(self, project_id: str, task_id: str) -> dict[str, Any]:
        """Get a specific task."""
        client = await self._get_client()
        response = await client.get(f"/projects/{project_id}/tasks/{task_id}")
        response.raise_for_status()
        return response.json().get("item", {})

    async def create_task(self, project_id: str, content: str) -> dict[str, Any]:
        """Create a new task in a project."""
        client = await self._get_client()
        response = await client.post(
            f"/projects/{project_id}/tasks",
            json={"content": content, "contentType": "text/markdown"}
        )
        response.raise_for_status()
        logger.info("task_created", project_id=project_id)
        return response.json().get("item", {})

    async def update_task(self, project_id: str, task_id: str, content: str) -> dict[str, Any]:
        """Update a task."""
        client = await self._get_client()
        response = await client.put(
            f"/projects/{project_id}/tasks/{task_id}",
            json={"content": content, "contentType": "text/markdown"}
        )
        response.raise_for_status()
        return response.json().get("item", {})

    async def delete_task(self, project_id: str, task_id: str) -> None:
        """Delete a task."""
        client = await self._get_client()
        response = await client.delete(f"/projects/{project_id}/tasks/{task_id}")
        response.raise_for_status()

    async def get_fields(self, project_id: str) -> list[dict[str, Any]]:
        """Get custom field schema for a project."""
        client = await self._get_client()
        response = await client.get(f"/projects/{project_id}/fields")
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_task_field(self, project_id: str, task_id: str, field_id: str) -> dict[str, Any]:
        """Get a single field value for a task."""
        client = await self._get_client()
        response = await client.get(
            f"/projects/{project_id}/tasks/{task_id}/fields/{field_id}"
        )
        response.raise_for_status()
        return response.json()

    async def get_task_all_fields(
        self,
        project_id: str,
        task_id: str,
        field_ids: list[str],
        semaphore: asyncio.Semaphore
    ) -> dict[str, Any]:
        """Fetch all field values for a task with concurrency limiting and rate limit handling."""

        async def fetch_field(field_id: str) -> tuple[str, Any, str | None]:
            async with semaphore:
                try:
                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.05)  # 50ms delay between requests
                    result = await self.get_task_field(project_id, task_id, field_id)
                    return (field_id, result.get("item", {}).get("value"), None)
                except Exception as e:
                    # Check if it's a rate limit error
                    if "429" in str(e):
                        logger.warning(f"Rate limited on field {field_id}, will retry after delay")
                        await asyncio.sleep(2)  # Wait 2 seconds on rate limit
                        try:
                            result = await self.get_task_field(project_id, task_id, field_id)
                            return (field_id, result.get("item", {}).get("value"), None)
                        except Exception as retry_e:
                            logger.warning(f"Retry failed for field {field_id} for task {task_id}: {retry_e}")
                            return (field_id, None, str(retry_e))
                    logger.warning(f"Failed to fetch field {field_id} for task {task_id}: {e}")
                    return (field_id, None, str(e))

        # Fetch all fields concurrently
        results = await asyncio.gather(
            *[fetch_field(fid) for fid in field_ids],
            return_exceptions=True
        )

        # Build result dict
        data = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            field_id, value, error = result
            if value is not None:
                data[field_id] = value

        return data

    async def fetch_all_entities_with_fields(
        self,
        project_id: str,
        field_ids: list[str],
        max_concurrent: int = 10  # Reduced from 20 to 10 for rate limiting
    ) -> list[dict[str, Any]]:
        """Fetch all tasks with their field values using fan-out pattern with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)

        # Step 1: Get all tasks
        try:
            tasks = await self.get_tasks(project_id)
        except Exception as e:
            if "429" in str(e):
                logger.warning("Rate limited when fetching tasks, retrying after delay")
                await asyncio.sleep(5)
                tasks = await self.get_tasks(project_id)
            else:
                raise

        logger.info(f"Fetching fields for {len(tasks)} tasks with max {max_concurrent} concurrent requests")

        # Step 2: For each task, fetch all fields
        async def fetch_task_with_fields(task: dict) -> dict[str, Any]:
            task_id = task.get("id", "")
            fields = await self.get_task_all_fields(project_id, task_id, field_ids, semaphore)
            return {
                "task_id": task_id,
                "task_name": task.get("text", ""),
                "fields": fields
            }

        results = await asyncio.gather(
            *[fetch_task_with_fields(t) for t in tasks],
            return_exceptions=True
        )

        # Filter out exceptions
        return [r for r in results if not isinstance(r, Exception)]


# Dependency injection helper
async def get_taskade_client() -> TaskadeClient:
    """FastAPI dependency for TaskadeClient."""
    client = TaskadeClient()
    try:
        yield client
    finally:
        await client.close()

