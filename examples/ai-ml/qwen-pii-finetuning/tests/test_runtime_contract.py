from datetime import date

import pytest

from src.runtime_contract import require_supported_baseline


def test_historical_runtime_passes_before_its_patch_end():
    require_supported_baseline(date(2026, 8, 5))


def test_review_date_blocks_the_expired_runtime():
    with pytest.raises(RuntimeError, match="2026-08-06"):
        require_supported_baseline(date(2026, 9, 12))
