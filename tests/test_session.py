import os
import json

from headout_login import ensure_session


def test_storage_state_created():
    path = ensure_session()
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "cookies" in data

