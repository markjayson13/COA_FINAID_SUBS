#!/usr/bin/env python3
from __future__ import annotations

# Builds paper and appendix descriptive-statistics exports.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.descstat_tables import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
