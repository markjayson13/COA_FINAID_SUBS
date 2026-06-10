#!/usr/bin/env python3
from __future__ import annotations

# Builds the public research analysis panel from the upstream clean IPEDS panel.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.prepare_analysis_panel import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
