import threading
import time
from collections import defaultdict


class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._latencies = defaultdict(float)

    def increment(self, key, amount=1):
        with self._lock:
            self._counters[key] += amount

    def observe(self, key, value):
        with self._lock:
            self._latencies[key] += value

    def render_prometheus(self):
        lines = []
        with self._lock:
            for key, value in sorted(self._counters.items()):
                lines.append(f"{key} {value}")
            for key, value in sorted(self._latencies.items()):
                lines.append(f"{key} {value:.6f}")
        return "\n".join(lines) + "\n"


REGISTRY = MetricsRegistry()


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed = time.perf_counter() - start
        normalized = request.path.strip("/").replace("/", "_") or "root"
        REGISTRY.increment("myos_requests_total")
        REGISTRY.increment(f"myos_path_{normalized}_total")
        REGISTRY.observe("myos_request_duration_seconds", elapsed)
        return response
