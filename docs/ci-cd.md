# CI/CD

## Pull Requests

The `CI` workflow runs formatting, Ruff, mypy, pytest, Compose validation, Helm lint, Helm rendering, and a filesystem vulnerability scan. The scan uses `aquasecurity/trivy-action@v0.36.0`, the current versioned tag documented by the action project. Configure these jobs as required checks on `main`.

## Images

Merges to `main` publish API, pipeline, and Airflow images to GHCR. Each image is scanned with the same Trivy action and tagged only with the immutable commit SHA:

```text
ghcr.io/<owner>/flightops-api:<commit-sha>
```

## Deployment

`Deploy` starts staging only after `Publish Images` succeeds. It deploys the workflow commit SHA through Helm and checks deployment rollout, API readiness, and service reachability.

The production job uses the GitHub `production` environment. Configure required reviewers on that environment to create the manual approval gate. Kubernetes credentials must be supplied through protected environment secrets; they are intentionally not stored in the repository.

## Repository Settings

Protect `main` in GitHub with pull-request review requirements and these required checks:

- `quality`
- `compose`
- `helm`

Grant the workflow `packages: write` permission and enable GitHub Packages for the repository.
