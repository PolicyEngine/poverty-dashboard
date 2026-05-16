"""Compatibility wrapper for ``poverty_dashboard.compute_local``."""

from poverty_dashboard.compute_local import *  # noqa: F403
from poverty_dashboard.compute_local import main

if __name__ == "__main__":
    main()
