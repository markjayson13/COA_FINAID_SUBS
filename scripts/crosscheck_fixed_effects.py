from __future__ import annotations

# Compares the local fixed-effects estimator against an external package.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.fixed_effects_crosscheck import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
