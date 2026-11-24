"""Request limits for the endpoints that spend TomTom quota; the rates are in settings."""

from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle


class PlanThrottle(AnonRateThrottle):
    cache = caches["throttle"]
    scope = "plan"


class GeocodeThrottle(AnonRateThrottle):
    cache = caches["throttle"]
    scope = "geocode"
