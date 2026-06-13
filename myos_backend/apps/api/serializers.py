from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200)


class DashboardSerializer(serializers.Serializer):
    finance = serializers.DictField()
    projects = serializers.DictField()
    education = serializers.DictField()
    media = serializers.DictField()
    bucket = serializers.DictField()
    diary = serializers.DictField()
    events = serializers.DictField()
    unread_notifications = serializers.IntegerField()
