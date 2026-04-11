"""Allow running vibescore as ``python -m vibescore``."""
from __future__ import annotations

import sys

from .cli import main

sys.exit(main())
