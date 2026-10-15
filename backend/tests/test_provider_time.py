from datetime import datetime, timedelta, timezone

import pytest

from apps.common.provider import provider_time
from apps.inbox.services import trusted_inbound_time


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "bad",
        "2026-02-30T10:00:00Z",
        "2026-10-14T10:00:00",
        True,
        [],
        {},
        float("nan"),
        float("inf"),
        -float("inf"),
        10**400,
    ],
)
def test_unparseable_time_is_explicitly_absent(value):
    assert provider_time(value) is None


def test_provider_time_units_and_timezone(frozen_now):
    assert provider_time(frozen_now.timestamp()) == frozen_now
    assert provider_time(frozen_now.timestamp() * 1000, milliseconds=True) == frozen_now
    assert provider_time("2026-10-14T18:00:00+0800") == frozen_now
    assert provider_time(frozen_now.isoformat()) == frozen_now
    assert provider_time(str(frozen_now.timestamp() * 1000), milliseconds=True) is None
    assert provider_time(True, milliseconds=True) is None
    assert provider_time(10**400, milliseconds=True) is None


@pytest.mark.parametrize("seconds,valid", [(0, True), (5, True), (5.001, False), (604800, False)])
def test_inbound_future_tolerance_is_five_seconds(frozen_now, seconds, valid):
    value = frozen_now + timedelta(seconds=seconds)
    # Parsing and authorization are deliberately separate decisions.
    assert provider_time(value.isoformat()) == value
    assert trusted_inbound_time(value, now=frozen_now) == (value if valid else None)


@pytest.mark.parametrize("value", [0, -1, datetime(1960, 1, 1, tzinfo=timezone.utc)])
def test_non_positive_epoch_cannot_authorize(value, frozen_now):
    assert trusted_inbound_time(value, now=frozen_now) is None
