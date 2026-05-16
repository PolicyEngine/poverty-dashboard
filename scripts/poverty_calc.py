"""Compatibility wrapper for ``poverty_dashboard.poverty_calc``."""

from poverty_dashboard.poverty_calc import *  # noqa: F403
from poverty_dashboard.poverty_calc import main

if __name__ == "__main__":
    main()
