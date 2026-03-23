from google.cloud import datastore
from backend.core.configs import settings
from typing import Optional, Any
from loguru import logger
import os

# --- gRPC Networking Tuning ---
# Force gRPC to prefer IPv4 if possible, or at least use native DNS resolver
# which tends to be more robust against IPv6 flakes on some hosts.
os.environ["GRPC_DNS_RESOLVER"] = "native"

# Optional: Disable IPv6 for gRPC if needed, but let's start with native resolver
# os.environ["GRPC_ENABLE_IPV6"] = "0" 

from google.api_core import retry

# Define a standard retry policy for Datastore transient errors
# InternalError, ServiceUnavailable, and DeadlineExceeded are common targets
datastore_retry = retry.Retry(
    predicate=retry.if_exception_type(
        Exception # We catch the base exception and filter inside if needed, or specific ones:
    ),
    initial=1.0,  # 1 second
    maximum=10.0, # 10 seconds
    multiplier=2.0,
    deadline=60.0  # 1 minute total
)

def is_transient_error(e: Exception) -> bool:
    """Detects if an exception is a transient gRPC/Datastore error."""
    msg = str(e).lower()
    return any(term in msg for term in [
        "serviceunavailable", "503", "unavailable", "deadline", "timeout", "route to host"
    ])

class GuardedDatastoreClient:
    """
    Wraps google.cloud.datastore.Client to enforce Zero Hard Delete policy
    and provide automatic retries for transient errors.
    """
    def __init__(self, client: datastore.Client):
        self._client = client

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        
        if callable(attr) and name in ["get", "put", "get_multi", "put_multi", "query"]:
            def with_retry(*args, **kwargs):
                try:
                    result = datastore_retry(attr)(*args, **kwargs)
                    
                    # If it's a query, we need to wrap its fetch() method too
                    if name == "query" and hasattr(result, "fetch"):
                        original_fetch = result.fetch
                        def fetch_with_retry(*inner_args, **inner_kwargs):
                            try:
                                return datastore_retry(original_fetch)(*inner_args, **inner_kwargs)
                            except Exception as e:
                                if is_transient_error(e):
                                    logger.warning(f"Datastore Query.fetch failed after retries: {e}")
                                raise e
                        result.fetch = fetch_with_retry
                    
                    return result
                except Exception as e:
                    if is_transient_error(e):
                        logger.warning(f"Datastore {name} failed after retries: {e}")
                    raise e
            return with_retry
            
        return attr

    def delete(self, key: datastore.Key) -> None:
        """
        Intercepts and blocks physical deletion attempts.
        """
        logger.critical(f"ZERO_HARD_DELETE_VIOLATION: Attempted to physically delete key {key}")
        raise RuntimeError("Physical deletion (Hard Delete) is strictly forbidden by project policy. Use Soft Delete instead.")

    def delete_multi(self, keys: list[datastore.Key]) -> None:
        """
        Intercepts and blocks multi-physical deletion attempts.
        """
        logger.critical(f"ZERO_HARD_DELETE_VIOLATION: Attempted to physically delete multiple keys: {keys}")
        raise RuntimeError("Physical deletion (Hard Delete) is strictly forbidden by project policy. Use Soft Delete instead.")

class DatastoreClient:
    _instance: Optional[GuardedDatastoreClient] = None

    @classmethod
    def get_client(cls) -> GuardedDatastoreClient:
        if cls._instance is None:
            # Initialize client with project from settings
            real_client = datastore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            cls._instance = GuardedDatastoreClient(real_client)
        return cls._instance

def get_datastore_client() -> GuardedDatastoreClient:
    return DatastoreClient.get_client()
