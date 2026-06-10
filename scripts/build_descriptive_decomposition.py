#!/usr/bin/env python3
from __future__ import annotations

# Builds component-change tables that separate COA pieces over time.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.descriptive_decomposition import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
