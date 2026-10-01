# Clean Code Review — 2026-10-02

## Assessment and scope

FlightOps already separated SQL transforms, sklearn pipelines, serving, and deployment. The main maintenance problems were broken entry points, implicit contracts, mixed responsibilities, and stale documentation. The review covered Python runtime modules, CLI scripts, DAGs, unit tests, SQL contracts/migrations, PowerShell scripts, and deployment configuration. Refactoring focused on concrete defects and the Python training/scoring paths.

The reference is Robert C. Martin's [Clean Code](https://www.lkhibra.ma/books/clean-code.pdf), especially chapters 2–3 (names and function responsibilities), 4–5 (comments and organization), 7 (error context), 9 (repeatable tests), and 10 (focused classes). The local Clean Code and Karpathy skills apply these principles in context. Function length and class count are not compliance scores; use the simplest structure that makes behavior clear.

## Findings addressed

| Impact | Finding before review | Change |
| --- | --- | --- |
| High | Baseline and validation entry points imported deleted symbols/modules. | Use `TrainingExperiment` and `TrainingData`; importing scripts no longer starts validation. |
| High | Champion was resolved for metadata, then loaded again through a mutable alias. | `scoring/model.py` resolves once and loads the exact version for both API and batch. |
| High | Training could accept invalid labels/timestamps or split too few unique timestamps. | Validate the dataset and split boundaries; fail with contextual errors before model fitting. |
| Medium | Chronological splits ignored YAML ratios. | Use the configured fractions, keeping equal timestamps within one window. |
| Medium | Airflow training discarded results; DAG start dates were naive. | Track/register results and use UTC-aware start dates. |
| Medium | Training/tracking functions mixed tuning, fitting, metrics, registry, and SQL writes. | Extract focused stages and pass an explicit `ExperimentResult`. Promotion occurs after lineage is committed. |
| Medium | Recorded splits were empty; comparator field names incorrectly claimed route-rate metrics. | Persist actual boundaries/counts and migrate to generic baseline fields with an explicit comparator name. |
| Medium | Serving imported batch policy and loaded YAML just to retrieve a fixed feature list. | Share the input contract, model loader, and risk policy directly; keep training package imports free of jobs. |
| Medium | YAML listed transformer switches that the loader never read. | Remove unused switches; the current sklearn pipeline explicitly defines its calendar/history transforms. |
| Medium | PostgreSQL credentials were interpolated into connection text. | Use psycopg's connection formatter to quote spaces, apostrophes, and backslashes correctly. |
| Medium | API caught every exception, swallowed registry errors during metrics collection, and used arbitrary URL labels. | Handle expected registry/artifact failures explicitly, retain error context, log missing champions, use bounded route labels, and count unhandled HTTP 500s. |
| Medium | Missing prediction history appeared as fresh zero-valued monitoring data. | Emit `NaN` for unavailable freshness and matured-rate observations. |
| Medium | Typing checks had missing annotations, missing YAML stubs, and untyped sklearn inheritance. | Add method/result annotations and YAML stubs; limit sklearn's untyped-base exception to the transformer module. |
| Medium | Documentation described removed modules, multi-family selection, and artifacts not produced by current code. | Document the actual configured-family workflow, plain comparator, promotion, and diagnostic thresholds. |

The existing estimator families, feature values, sigmoid calibration, comparison metrics, risk bands, and successful promotion behavior are preserved. SQL history aggregates remain explicit: their repeated query shapes have different grouping/cutoff conditions, and a generic abstraction would make leakage checks harder to audit.

## Setup and verification

Use Python 3.12.10 and run commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest
```

If the pyenv shim says no version is selected, check `pyenv versions` and use the installed Python 3.12.10 executable to create the environment. During this review, the installed executable was `C:\Users\Maull\.pyenv\pyenv-win\versions\3.12.10\python.exe`; no global pyenv configuration was changed.

Regression tests cover configured split ratios, timestamp ties/timezones, invalid datasets, prediction/evaluation equivalence with the previous logistic procedure, tuning windows, exact champion-version loading, API eligibility/error responses, batch version/risk recording, lineage/promotion order, monitoring semantics, and importable entry points. PostgreSQL and MLflow calls are mocked in unit tests; these tests do not prove live service availability or database idempotency.

Verified locally on Python 3.12.10: Ruff lint and formatting passed, strict mypy passed across 17 source modules, and all 58 tests passed. The suite includes a serialized sklearn pipeline round trip. Python compilation and both configurable CLI help commands also passed. Three dependency deprecation warnings remain visible.

## Apply the lineage migration before training

```powershell
.\scripts\apply-migrations.ps1
```

Migration `013_clarify_training_baseline_lineage.sql` affects only `ml.training_runs`. It renames two comparator columns and adds `baseline_name`, preserving existing metrics. Historical comparator identities remain `NULL` rather than being guessed. Apply it before running the updated training script or Airflow training task. Migration validation against a live PostgreSQL instance remains a separate integration check.

For live verification, follow the [local platform runbook](runbooks/local-platform.md) and `scripts/smoke-test.ps1`. An `UndefinedColumn` error mentioning `candidate_beats_baseline` or `baseline_name` means migration 013 has not been applied. A `503` prediction means the champion alias or its artifact is unavailable; inspect MLflow and the original error in service logs. Empty prediction history produces `NaN` monitoring values until batch scoring writes predictions.

## Remaining design and runtime limits

The follow-up review reproduced two failure paths and fixed them with regression tests. `_log_run` records `git_revision=unavailable` when the Git executable or repository metadata is absent; this keeps pipeline images trainable without Git. `load_approved_model` translates EOF and pickle deserialization failures into `ApprovedModelUnavailable`, so API clients receive the documented HTTP 503 instead of a server error. These checks are included in the current unit suite.

- Validation currently serves tuning, calibration, and threshold selection. Cross-family selection requires an explicit evaluation policy and a fresh holdout; this cleanup does not claim to solve statistical selection bias.
- The SQL target is strictly `actual_departure > scheduled_departure + 15 minutes`, while some PRD prose says “at least 15 minutes.” The existing SQL contract is preserved here. Changing the boundary requires an agreed target definition and rebuilt labels/features/models.
- Registry alias readiness does not check artifact loadability or PostgreSQL. Model artifacts are still loaded per request; caching requires a defined refresh policy.
- `git_revision=unavailable` means the runtime did not provide repository provenance. Build systems needing complete lineage must inject the revision as deployment metadata.
- The sklearn 1.6 calibration API emits a `cv="prefit"` deprecation warning; the installed Starlette/AnyIO combination also emits a deprecation warning. Tests do not suppress them.
- Live PostgreSQL/MLflow/Airflow/Docker and Kubernetes checks were not completed in this review. Docker daemon access was denied in the current sandbox. Prior deployment evidence in other documents is historical.

## Maintenance conventions

Add a new estimator factory only for an actual model family. Keep domain thresholds in `scoring/policy.py`, raw input columns in `training/config.py`, and feature availability rules in SQL and the [feature contract](feature-contract.md). Update migration history and documentation when persisted contracts change. Before editing serving or preprocessing, run the regression tests and verify a serialized model round trip when artifact compatibility is affected.

Downloaded developer tools under `.tools/`, local data, artifacts, caches, and `.env` are ignored by Git. Review the dry-run staging list before each first push, especially when adding a new configuration or generated output.
