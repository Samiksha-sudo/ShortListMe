import io
import zipfile

MAX_BYTES = 5 * 1024 * 1024
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class InvalidCV(ValueError):
    pass


def validate_docx(filename: str, data: bytes) -> None:
    if not filename.lower().endswith(".docx"):
        raise InvalidCV("Only .docx files are supported right now.")
    if len(data) > MAX_BYTES:
        raise InvalidCV("File is larger than 5 MB.")
    if not data.startswith(b"PK\x03\x04"):
        raise InvalidCV("File is not a valid DOCX.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise InvalidCV("File is not a valid DOCX.")
    except zipfile.BadZipFile:
        raise InvalidCV("File is not a valid DOCX.") from None
