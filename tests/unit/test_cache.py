from rag_assistant.common.cache import EmbeddingCache


def test_put_get_roundtrip(tmp_path):
    c = EmbeddingCache(str(tmp_path / "cache"), model="m1")
    assert c.get("texto") is None
    c.put("texto", [0.1, 0.2, 0.3])
    assert c.get("texto") == [0.1, 0.2, 0.3]
    c.close()


def test_key_includes_model(tmp_path):
    path = str(tmp_path / "cache")
    c1 = EmbeddingCache(path, model="m1")
    c1.put("t", [1.0])
    c1.close()
    # mesmo texto, modelo diferente => miss (vetores não são intercambiáveis)
    c2 = EmbeddingCache(path, model="m2")
    assert c2.get("t") is None
    c2.close()
