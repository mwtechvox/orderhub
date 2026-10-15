from unittest.mock import Mock

from kombu.exceptions import OperationalError

from apps.common.queue import enqueue


def test_queue_failure_does_not_undo_durable_row():
    task = Mock(name="task")
    task.apply_async.side_effect = OperationalError("unavailable")
    enqueue(task, "company", "message")
    task.apply_async.assert_called_once_with(args=("company", "message"), retry=False)
