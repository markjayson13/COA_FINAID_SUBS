from __future__ import annotations

# Checks the Pell policy-shock registry before any exposure design uses it.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.policy_shocks import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
