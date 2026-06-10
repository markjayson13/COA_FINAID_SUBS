#!/usr/bin/env python3
from __future__ import annotations

# Verifies the public variable contract against the prepared IPEDS panel.
# The detailed logic lives in src/ so scripts and notebooks use the same code.
from coa_finaid_subs.audit_variable_config import main


if __name__ == "__main__":
    # Run the command-line workflow.
    main()
