# Security policy

TAP is currently a single-user research prototype. It can submit and cancel remote jobs, read training logs, and access experiment metadata. Treat the backend as a privileged administrative service.

## Safe deployment

- Run TAP only on a trusted private network or behind an authenticated reverse proxy.
- Do not expose the FastAPI service directly to the public internet.
- Use a dedicated SSH identity with the minimum remote permissions required.
- Protect the SSH private key on the host and mount it read-only when using Docker.
- Store credentials in an untracked `.env` file or a secret manager.
- Restrict GitHub self-hosted runners to trusted workflows and repositories.
- Rotate W&B keys, webhooks, and SSH credentials immediately if they are committed or logged.
- Back up the SQLite database and treat it as sensitive research metadata.

TAP does not currently provide application-level authentication, authorization, tenant isolation, or distributed worker locking.

## Reporting a vulnerability

Do not disclose credentials or sensitive infrastructure details in a public issue. Contact the repository owner privately through their GitHub profile with a minimal description and coordinate secure delivery of any sensitive evidence.
