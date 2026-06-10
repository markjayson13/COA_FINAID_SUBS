#!/usr/bin/env python3
from __future__ import annotations

# Audits the headroom measures used in the paper tables and models.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.headroom_measures import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
