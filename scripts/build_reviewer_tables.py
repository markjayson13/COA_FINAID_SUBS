from __future__ import annotations

# Builds model cards, sample-attrition rows, and metadata glossary tables.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.reviewer_tables import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
