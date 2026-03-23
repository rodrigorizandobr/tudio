import pytest
from backend.services.cache_service import search_cache
from backend.repositories.search_cache_repository import search_cache_repository

@pytest.mark.asyncio
async def test_search_cache_persistence():
    provider = "test_provider"
    query = "test_query_permanent"
    data = [{"id": 1, "url": "http://test.com/img.jpg"}]
    
    # 1. Clear existing if any (manual mock or real client)
    # Actually we don't 'delete' in our project easily without guard, but we can just use unique query
    
    # 2. Set Cache
    search_cache.set(provider, query, data)
    
    # 3. Get Cache
    retrieved = search_cache.get(provider, query)
    
    assert retrieved is not None
    assert len(retrieved) == 1
    assert retrieved[0]["url"] == "http://test.com/img.jpg"
    
    # 4. Verify in Repository directly
    key = search_cache._get_key(provider, query)
    db_entry = search_cache_repository.get(key)
    assert db_entry is not None
    assert db_entry.provider == provider
    assert db_entry.data == data
    
    print("Search Cache Persistence Verified successfully!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search_cache_persistence())
