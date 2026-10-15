import logging

from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)


def enqueue(task, *args):
    """Rows persist before publish. Beat recovers pending rows if Redis is unavailable."""
    try:
        task.apply_async(args=args, retry=False)
    except OperationalError:
        logger.warning("queue_publish_unavailable task=%s", task.name)
