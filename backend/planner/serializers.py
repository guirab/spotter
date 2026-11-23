from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

# A little slack in the past so a form left open for a few minutes still submits (PLAN.md §5.3).
DEPARTURE_GRACE = timedelta(minutes=15)
DEPARTURE_WINDOW = timedelta(days=5)  # D12


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=100)  # CharField trims whitespace first


class PlaceSerializer(serializers.Serializer):
    # Loose US box (contiguous US plus Alaska and Hawaii); geocoding is already US-only (D19).
    label = serializers.CharField(max_length=200)
    lat = serializers.FloatField(min_value=18, max_value=72)
    lon = serializers.FloatField(min_value=-180, max_value=-66)


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_at = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=80_000)  # A2
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50])  # D3

    def validate_departure_at(self, value):
        now = timezone.now()
        if not now - DEPARTURE_GRACE <= value <= now + DEPARTURE_WINDOW:
            raise serializers.ValidationError("Departure must be between now and 5 days from now.")
        return value

    def validate(self, data):
        origin, destination = data["origin"], data["destination"]
        if (origin["lat"], origin["lon"]) == (destination["lat"], destination["lon"]):
            raise serializers.ValidationError({"destination": ["Destination must differ from the origin."]})
        return data
