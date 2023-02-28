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
    return logger

def get_meter(endpoint, headers, resource, meter):
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint,headers=headers))
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    meter = metrics.get_meter(__name__,meter_provider=provider)
    return meter

def get_tracer(endpoint, headers, resource, tracer):
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint,headers=headers))
    tracer = TracerProvider(resource=resource)
    tracer.add_span_processor(processor)
    tracer = trace.get_tracer(__name__, tracer_provider=tracer)

    return tracer
