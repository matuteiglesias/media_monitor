from backend.ids import stable_index_id, digest_id_hour
from backend.slugs import slugify

def test_index_id_len():
    assert len(stable_index_id("a","b","https://x")) == 10

def test_digest_id_format():
    did,_ = digest_id_hour()
    assert len(did) == 11 and did[8] == "T"

def test_slugify_accents():
    assert slugify("¿Niño? Café!") == "nino-cafe"
