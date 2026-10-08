import io
import zipfile
from pathlib import Path

from app.core.config import settings


def make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


def post(client, name, data):
    return client.post("/v1/cvs", files={"file": (name, data, "application/octet-stream")})


def test_valid_docx_is_stored(client):
    from tests import samples

    r = post(client, "cv.docx", samples.single_column())
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "cv.docx"
    assert (Path(settings.storage_dir) / "cvs" / f"{body['cv_id']}.docx").exists()


def test_wrong_extension_rejected(client):
    r = post(client, "cv.pdf", b"%PDF-1.4")
    assert r.status_code == 422
    assert "docx" in r.json()["detail"].lower()


def test_fake_docx_rejected(client):
    r = post(client, "cv.docx", b"not a zip at all")
    assert r.status_code == 422


def test_zip_without_document_xml_rejected(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "x")
    assert post(client, "cv.docx", buf.getvalue()).status_code == 422


def test_oversized_file_rejected(client):
    r = post(client, "cv.docx", make_docx() + b"0" * (5 * 1024 * 1024))
    assert r.status_code == 422
    assert "5 MB" in r.json()["detail"]


def test_upload_parses_and_get_returns_blocks(client):
    from tests import samples

    r = post(client, "cv.docx", samples.single_column())
    assert r.status_code == 201
    body = r.json()
    assert body["blocks"] > 10 and 0 < body["editable"] < body["blocks"]

    got = client.get(f"/v1/cvs/{body['cv_id']}")
    assert got.status_code == 200
    cv = got.json()
    assert cv["filename"] == "cv.docx"
    assert any(b["type"] == "headline" and b["editable"] for b in cv["blocks"])
    assert "numbers" in cv["facts"]


def test_get_unknown_cv_is_404(client):
    assert client.get("/v1/cvs/does-not-exist").status_code == 404


def test_unreadable_docx_rejected_and_not_stored(client):
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<broken")
    r = post(client, "cv.docx", buf.getvalue())
    assert r.status_code == 422
    assert not (Path(settings.storage_dir) / "cvs").exists()
