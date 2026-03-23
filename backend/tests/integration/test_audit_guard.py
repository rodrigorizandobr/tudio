import pytest
from backend.core.datastore_client import get_datastore_client
from google.cloud import datastore

def test_audit_guard_blocks_delete():
    """
    Verify that the GuardedDatastoreClient blocks physical delete calls.
    """
    client = get_datastore_client()
    key = client.key("TestKind", 12345)
    
    with pytest.raises(RuntimeError) as excinfo:
        client.delete(key)
    
    assert "Physical deletion (Hard Delete) is strictly forbidden" in str(excinfo.value)

def test_audit_guard_blocks_delete_multi():
    """
    Verify that the GuardedDatastoreClient blocks physical delete_multi calls.
    """
    client = get_datastore_client()
    keys = [client.key("TestKind", 12345), client.key("TestKind", 67890)]
    
    with pytest.raises(RuntimeError) as excinfo:
        client.delete_multi(keys)
    
    assert "Physical deletion (Hard Delete) is strictly forbidden" in str(excinfo.value)
