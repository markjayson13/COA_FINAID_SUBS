# Estimator validation

The main estimator is local and transparent: it residualizes the configured variables by institution and year, solves the residualized least-squares problem, and computes clustered standard errors by `UNITID`.

That transparency is useful, but it is not enough for paper tables. The headline estimates should also be checked against a maintained panel-estimation package before they are cited in the manuscript.

## Standard-package check

Install the optional validation dependency:

```bash
python -m pip install '.[validation]'
```

Then run:

```bash
PYTHONPATH=src python scripts/crosscheck_fixed_effects.py \
  --sample-dir outputs/model_samples/samples \
  --fixed-effects-dir outputs/fixed_effects \
  --output-dir outputs/fixed_effects_crosscheck \
  --config config/model_specifications.csv \
  --model-id fe_inst_grant_per_student \
  --model-id public_inst_grant \
  --model-id private_np_inst_grant
```

By default, the script checks the focal coefficient from each selected model. Add `--all-terms` to compare controls too. The control-term check is useful for numerical audits, but the manuscript gate is the focal coefficient used as a finding.

The script fits the same materialized model samples with `linearmodels.PanelOLS`, using entity and time effects when the model specifies `UNITID;year`. It uses the same clustered-SE small-sample convention as the local estimator. It writes:

- `outputs/fixed_effects_crosscheck/fixed_effects_linearmodels_comparison.csv`
- `outputs/fixed_effects_crosscheck/fixed_effects_linearmodels_summary.json`

## Rule for manuscript use

The cross-check should pass for any coefficient used as a headline finding. A failed check means the estimate is not ready for the paper until the mismatch is explained.

The check does not change the research design. It is a numerical validation step for the estimator.

## Current result

The current local cross-check passes for:

- `fe_inst_grant_per_student`
- `public_inst_grant`
- `private_np_inst_grant`

The three focal coefficients match within the configured tolerances. The maximum absolute coefficient difference is `1.39e-16`; the maximum absolute standard-error difference is `1.49e-05`.
