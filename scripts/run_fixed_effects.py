from __future__ import annotations

# Estimates the configured fixed-effects models from materialized samples.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.fixed_effects import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
