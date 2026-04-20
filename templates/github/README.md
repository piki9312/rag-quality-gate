# GitHub Actions templates for RQG

Copy one of these workflows into `.github/workflows/` in the target repository.

- `rqg-gate-mock.yml`: local/mock smoke gate for first-day onboarding
- `rqg-gate-external.yml`: external HTTP RAG validation + gate run
- `rqg-gate-external-notify.yml`: external gate with Slack notification hook

These templates are intentionally small so operators can adapt them to their own CI/CD rules.
