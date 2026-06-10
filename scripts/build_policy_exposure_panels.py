from __future__ import annotations

# Builds institution-level exposure panels for Pell policy diagnostics.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.policy_exposures import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
