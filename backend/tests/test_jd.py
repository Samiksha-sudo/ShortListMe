import hashlib

JD = ("We are hiring a Senior Backend Engineer to build APIs in Python and PostgreSQL. "
      "You will own services end to end, mentor colleagues and work with product.")


def create(client, text=JD):
    return client.post("/v1/jds", json={"text": text})


def test_create_stores_text_and_sha256(client):
    res = create(client)
    assert res.status_code == 201
    body = res.json()
    assert body["text"] == JD
    assert body["text_hash"] == hashlib.sha256(JD.encode()).hexdigest()


def test_get_returns_saved_jd(client):
    jd_id = create(client).json()["jd_id"]
    res = client.get(f"/v1/jds/{jd_id}")
    assert res.status_code == 200 and res.json()["text"] == JD


def test_same_text_same_hash_despite_whitespace_and_line_endings(client):
    a = create(client, JD).json()["text_hash"]
    b = create(client, f"\n  {JD.replace('. ', '.')[:0]}{JD}  \r\n").json()["text_hash"]
    assert a == b
    crlf = create(client, JD.replace(". ", ".\r\n")).json()["text_hash"]
    lf = create(client, JD.replace(". ", ".\n")).json()["text_hash"]
    assert crlf == lf


def test_different_text_different_hash(client):
    assert create(client).json()["text_hash"] != create(client, JD + " Remote friendly.").json()["text_hash"]


def test_too_short_rejected(client):
    res = create(client, "Backend engineer wanted.")
    assert res.status_code == 422 and "at least 100" in res.text


def test_whitespace_padding_does_not_pass_min_length(client):
    assert create(client, "short" + " " * 500).status_code == 422


def test_too_long_rejected(client):
    res = create(client, "x" * 20_001)
    assert res.status_code == 422 and "too long" in res.text


def test_unknown_jd_is_404(client):
    assert client.get("/v1/jds/does-not-exist").status_code == 404
