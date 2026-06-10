#!/usr/bin/env python3
from __future__ import annotations

# Materializes complete-case samples before any fixed-effects model is estimated.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.model_samples import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
