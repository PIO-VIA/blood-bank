from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
import time
import structlog

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections'
)

DHIS2_SYNC_COUNT = Counter(
    'dhis2_sync_total',
    'Total DHIS2 sync operations',
    ['sync_type', 'status']
)

DHIS2_SYNC_DURATION = Histogram(
    'dhis2_sync_duration_seconds',
    'DHIS2 sync operation duration in seconds',
    ['sync_type']
)

BLOOD_PRODUCTS_GAUGE = Gauge(
    'blood_products_total',
    'Total blood products by type and status',
    ['blood_type', 'status']
)

DONATIONS_GAUGE = Gauge(
    'donations_total',
    'Total blood donations'
)

API_ERRORS = Counter(
    'api_errors_total',
    'Total API errors',
    ['endpoint', 'error_type']
)


def setup_prometheus_metrics():
    """Setup Prometheus metrics collection."""
    logger.info("Prometheus metrics enabled")


def track_request_metrics(request: Request, response: Response, process_time: float):
    """Track request metrics for Prometheus."""
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)


def track_sync_metrics(sync_type: str, status: str, duration: float):
    """Track DHIS2 sync metrics."""
    DHIS2_SYNC_COUNT.labels(
        sync_type=sync_type,
        status=status
    ).inc()
    
    DHIS2_SYNC_DURATION.labels(
        sync_type=sync_type
    ).observe(duration)


def update_blood_inventory_metrics(inventory_data: dict):
    """Update blood inventory metrics."""
    for (blood_type, status), count in inventory_data.items():
        BLOOD_PRODUCTS_GAUGE.labels(
            blood_type=blood_type,
            status=status
        ).set(count)


def track_api_error(endpoint: str, error_type: str):
    """Track API errors."""
    API_ERRORS.labels(
        endpoint=endpoint,
        error_type=error_type
    ).inc()


def get_prometheus_metrics():
    """Get Prometheus metrics in text format."""
    return generate_latest()