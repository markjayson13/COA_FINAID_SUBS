from __future__ import annotations

# Builds manuscript-ready fixed-effects estimate tables from generated outputs.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.estimate_tables import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
