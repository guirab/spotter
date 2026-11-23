from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import tomtom
from .serializers import GeocodeQuerySerializer, PlanRequestSerializer

UPSTREAM_FAILED = {"detail": "The routing service is unavailable. Please try again."}
GEOCODE_TTL_S = 24 * 60 * 60


@api_view(["GET"])
def health(request):
    return Response({"ok": True})


@api_view(["GET"])
def geocode(request):
    serializer = GeocodeQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    query = serializer.validated_data["q"].lower()
    try:
        places = cache.get_or_set(f"geocode:{query}", lambda: tomtom.geocode(query), GEOCODE_TTL_S)
    except tomtom.UpstreamError:
        return Response(UPSTREAM_FAILED, status=502)
    return Response(places)


@api_view(["POST"])
def plan(request):
    serializer = PlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        route = tomtom.calculate_route(**serializer.validated_data)
    except tomtom.NoRouteError:
        return Response({"detail": "No truck route found between these places."}, status=422)
    except tomtom.UpstreamError:
        return Response(UPSTREAM_FAILED, status=502)
    return Response({"routes": [{"id": "A", **route}]})
