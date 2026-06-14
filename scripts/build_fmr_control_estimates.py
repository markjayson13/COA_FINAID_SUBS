from __future__ import annotations

# Runs the companion estimate set that adds HUD Fair Market Rent as a local rent control.
# The baseline model configuration stays unchanged; this script writes separate robustness outputs.
from coa_finaid_subs.fmr_control_estimates import main


if __name__ == "__main__":
    main()
