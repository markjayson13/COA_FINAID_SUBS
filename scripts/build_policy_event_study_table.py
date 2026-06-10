from __future__ import annotations

# Extracts policy event-study coefficients into a reviewable table.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.event_study_tables import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
