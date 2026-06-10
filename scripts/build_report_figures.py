#!/usr/bin/env python3
from __future__ import annotations

# Builds paper-ready SVG figures and the CSV data behind each figure.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.report_figures import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
