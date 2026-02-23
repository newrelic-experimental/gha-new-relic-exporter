import logging

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import \
    OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import \
    OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_providers = []

def shutdown_all():
    """Flush and shutdown all tracer/logger providers to ensure data is exported."""
    for provider in _providers:
        try:
            provider.force_flush()
            provider.shutdown()
        except Exception as e:
            print(f"Error shutting down provider: {e}")

def create_resource_attributes(atts, GLAB_SERVICE_NAME):
    attributes={SERVICE_NAME: GLAB_SERVICE_NAME}
    for att in atts:
            attributes[att]=atts[att]
    return attributes

def get_logger(endpoint, headers, resource, name):
    exporter = OTLPLogExporter(endpoint=endpoint + "/v1/logs",headers=headers)
    logger = logging.getLogger(str(name))
    logger.handlers.clear()
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    _providers.append(logger_provider)
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logger.addHandler(handler)
    return logger


def get_tracer(endpoint, headers, resource, tracer):
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces",headers=headers))
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    _providers.append(provider)
    tracer = trace.get_tracer(__name__, tracer_provider=provider)

    return tracer

# todo
# def get_meter(endpoint, headers, resource, meter):
#     reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint,headers=headers))
#     provider = MeterProvider(resource=resource, metric_readers=[reader])
#     meter = metrics.get_meter(__name__,meter_provider=provider)
#     return meter