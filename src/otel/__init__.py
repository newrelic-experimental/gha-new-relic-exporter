import logging

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import \
    OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import \
    OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_providers = []

def create_resource_attributes(atts, GLAB_SERVICE_NAME):
    attributes={SERVICE_NAME: GLAB_SERVICE_NAME}
    for att in atts:
            attributes[att]=atts[att]
    return attributes

def get_logger(endpoint, headers, resource, name):
    exporter = OTLPLogExporter(endpoint=endpoint,headers=headers)
    logger = logging.getLogger(str(name))
    logger.handlers.clear()
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logger.addHandler(handler)
    _providers.append(logger_provider)
    return logger


def get_tracer(endpoint, headers, resource, tracer):
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint,headers=headers))
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    _providers.append(provider)
    return trace.get_tracer(tracer, tracer_provider=provider)


def shutdown_providers():
    # BatchSpanProcessor/BatchLogRecordProcessor export on a timer; without an
    # explicit flush the last-ended root span can still be queued when the
    # process exits, so New Relic never sees it and shows the trace group as
    # "unknown".
    for provider in _providers:
        provider.force_flush()
        provider.shutdown()

# todo
# def get_meter(endpoint, headers, resource, meter):
#     reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint,headers=headers))
#     provider = MeterProvider(resource=resource, metric_readers=[reader])
#     meter = metrics.get_meter(__name__,meter_provider=provider)
#     return meter