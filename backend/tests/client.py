"""A small httpx-style wrapper over Django's test client, so the tests read as plain HTTP calls."""
import json as jsonlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client


class Response:
    def __init__(self, res):
        self._res = res
        self.status_code = res.status_code
        self.headers = res
        self.content = res.content

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self):
        return jsonlib.loads(self.content)


class TestClient:
    __test__ = False  # not a test class

    def __init__(self, app=None):
        self._c = Client()
        self.headers: dict[str, str] = {}

    def request(self, method, url, json=None, headers=None, content=None, files=None, data=None):
        merged = {**self.headers, **(headers or {})}
        extra = {"HTTP_" + k.upper().replace("-", "_"): v for k, v in merged.items() if k.lower() != "content-type"}
        kwargs = {}
        if files is not None:
            body = dict(data or {})
            for field, (name, blob, *mime) in files.items():
                body[field] = SimpleUploadedFile(name, blob, content_type=mime[0] if mime else "application/octet-stream")
            kwargs = {"data": body}  # the test client encodes this as multipart
        else:
            payload = content if content is not None else (jsonlib.dumps(json) if json is not None else "")
            ctype = merged.get("content-type") or merged.get("Content-Type") or "application/json"
            kwargs = {"data": payload, "content_type": ctype}
        send = self._c.generic if files is None else getattr(self._c, method.lower())
        args = (method.upper(), url) if files is None else (url,)
        return Response(send(*args, **kwargs, **extra))

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def delete(self, url, **kw):
        return self.request("DELETE", url, **kw)
