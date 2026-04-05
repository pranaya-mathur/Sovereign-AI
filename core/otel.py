"""OpenTelemetry management for enterprise observability.

Provides standardized tracing and metrics initialization via OTLP.
"""

import os
import logging
from typing import Dict, Any, Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

logger = logging.getLogger(__name__)

class SovereignOTel:
    """Singleton-style manager for OpenTelemetry lifecycle."""
    
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SovereignOTel, cls).__new__(cls)
        return cls._instance

    def initialize(self, config: Dict[str, Any]):
        """Initialize OTel tracers and meters if enabled.
        
        Args:
            config: Observability configuration from policy.
        """
        if self._initialized or not config.get("enabled", False):
            return

        service_name = config.get("service_name", "sovereign-ai-guard")
        endpoint = config.get("otlp_endpoint", "http://localhost:4317")
        sampling_rate = config.get("sampling_rate", 1.0)
        
        resource = Resource.create({"service.name": service_name})
        
        # 1. Setup Tracing
        sampler = TraceIdRatioBased(sampling_rate)
        tracer_provider = TracerProvider(resource=resource, sampler=sampler)
        
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            logger.info(f"✅ OTel Tracing enabled (OTLP: {endpoint})")
        except Exception as e:
            logger.warning(f"⚠️ OTel Tracing export failed to init: {e}. Falling back to No-op.")
            
        trace.set_tracer_provider(tracer_provider)
        
        # 2. Setup Metrics
        try:
            metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
            reader = PeriodicExportingMetricReader(metric_exporter)
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(meter_provider)
            logger.info(f"✅ OTel Metrics enabled (OTLP: {endpoint})")
        except Exception as e:
            logger.warning(f"⚠️ OTel Metrics export failed to init: {e}. Falling back to No-op.")

        self._initialized = True

    def get_tracer(self, name: str = "sovereign-ai"):
        """Get a tracer instance."""
        return trace.get_tracer(name)

    def get_meter(self, name: str = "sovereign-ai"):
        """Get a meter instance."""
        return metrics.get_meter(name)

# Global singleton
otel_manager = SovereignOTel()
