#!/usr/bin/env python3
from __future__ import annotations

# Checks that configured model variables exist before model samples are built.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.model_plan import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
