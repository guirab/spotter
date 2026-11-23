from rest_framework import serializers


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

    def validate(self, data):
        origin, destination = data["origin"], data["destination"]
        if (origin["lat"], origin["lon"]) == (destination["lat"], destination["lon"]):
            raise serializers.ValidationError({"destination": ["Destination must differ from the origin."]})
        return data
