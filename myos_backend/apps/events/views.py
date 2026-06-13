from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import AutomationRule, Event
from .permissions import EventPermission
from .serializers import AutomationRuleSerializer, EventSerializer


class EventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, EventPermission]

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)


class AutomationRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated, EventPermission]

    def get_queryset(self):
        return AutomationRule.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
