from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("data/test_actiongate.db")
os.environ["ACTIONGATE_DB"] = str(TEST_DB)
