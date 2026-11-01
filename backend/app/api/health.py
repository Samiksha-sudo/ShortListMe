from rest_framework.response import Response

from app.api.deps import endpoint


@endpoint(["GET"], auth=None)
def health(request):
    return Response({"status": "ok"})
