from __future__ import annotations

# Checks fixed-effects outputs before they are used in the paper.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.estimation_validation import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
