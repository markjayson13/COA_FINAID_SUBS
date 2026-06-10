#!/usr/bin/env python3
from __future__ import annotations

# Profiles variable distributions and flags extreme values for review.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.audit_extremes import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
