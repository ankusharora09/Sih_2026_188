from backend.vector import get_vector_store

def test_in_memory_vector_store_basic():
    store = get_vector_store()
    # Ensure fallback to in-memory
    assert store.__class__.__name__ == "InMemoryVectorStore"
    store.add("a", [1.0, 0.0, 0.0])
    store.add("b", [0.0, 1.0, 0.0])
    store.add("c", [0.5, 0.5, 0.0])
    # Query near [1,0,0]
    results = store.query([1.0, 0.0, 0.0], top_k=2)
    # Expect "a" first
    assert results[0][0] == "a"
    # second may be "c" (cosine 0.707) > "b" (0)
    assert results[1][0] == "c"
