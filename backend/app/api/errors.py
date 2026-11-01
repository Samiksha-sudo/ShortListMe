from pydantic import BaseModel, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApiError(Exception):
    """An error answered as {"detail": ...} with the given status (the shape the frontend already reads)."""

    def __init__(self, status: int, detail, headers: dict | None = None):
        self.status, self.detail, self.headers = status, detail, headers or {}


def handler(exc, context):
    if isinstance(exc, ApiError):
        return Response({"detail": exc.detail}, status=exc.status, headers=exc.headers)
    if isinstance(exc, ValidationError):
        return Response({"detail": exc.errors(include_url=False, include_context=False, include_input=False)}, status=422)
    return exception_handler(exc, context)


def parse(model: type[BaseModel], data):
    """Validate a request body with its pydantic model; failures become a 422 via `handler`."""
    return model.model_validate(data if data is not None else {})
