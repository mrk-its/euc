import asyncio
import logging

logger = logging.getLogger(__name__)

_tasks = []


def _cleanup_task_cb(task):
    logger.debug("cleanup task %r", task)
    _tasks.remove(task)


def create_task(coro, loop=None):
    loop = loop or asyncio.get_event_loop()
    task = loop.create_task(coro)
    _tasks.append(task)
    task.add_done_callback(_cleanup_task_cb)
    logger.debug("created task %r", task)
