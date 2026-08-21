from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "realtor_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_default_queue = "realtor-agent"


@celery_app.task(name="realtor_agent.ingest_listings")
def ingest_listings_task() -> dict:
    from app.workers.ingest_listings import run

    return run()


@celery_app.task(name="realtor_agent.match_listings")
def match_listings_task() -> dict:
    from app.workers.match_listings import run

    return run()


@celery_app.task(name="realtor_agent.send_notifications")
def send_notifications_task() -> dict:
    from app.workers.send_notifications import run

    return run()


@celery_app.task(name="realtor_agent.generate_documents")
def generate_documents_task() -> dict:
    from app.workers.generate_documents import run

    return run()
