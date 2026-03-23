from datetime import datetime
from google.cloud import datastore
from backend.core.datastore_client import get_datastore_client
from typing import Optional, Any

class AuditService:
    def __init__(self):
        self.kind = "AuditLog"

    @property
    def client(self) -> datastore.Client:
        return get_datastore_client()

    async def log_event(self, user_email: str, action: str, target: str, details: Optional[str] = None):
        """
        Async wrapper for log_event_sync.
        """
        await asyncio.to_thread(self._log_event_sync, user_email, action, target, details)

    def _log_event_sync(self, user_email: str, action: str, target: str, details: Optional[str] = None):
        """
        Logs a transactional event to Datastore.
        """
        try:
            client = self.client
            key = client.key(self.kind) # Auto ID
            entity = datastore.Entity(key=key)
            entity.update({
                "user_email": user_email,
                "action": action,
                "target": target,
                "details": details,
                "timestamp": datetime.now()
            })
            client.put(entity)
        except Exception as e:
            # Audit logging should not break the application flow, but should be logged to system logs
            print(f"Failed to write audit log: {e}")

audit_service = AuditService()
