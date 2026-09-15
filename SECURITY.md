# Security

## Reporting a vulnerability

Do not open a public issue containing credentials, personal data, or an exploitable proof of concept. Contact the repository maintainers privately through the security-reporting channel configured on the canonical repository. Include the affected revision, deployment mode, reproduction conditions, and likely impact. Remove all real OpenAlex keys from examples.

## Supported boundary

Pharos is local-only by default. Hosted mode is opt-in and requires exact public Host and Origin allowlists. The current container foundation provides ephemeral session isolation, bounded work, and optional session-only OpenAlex authentication, but still requires platform-level TLS, traffic controls, monitoring, and incident handling.

Anonymous and operator-key OpenAlex responses may use the shared dated public cache. Requests made with a browser-supplied session key use a cache inside that session's ephemeral directory and are never reused across sessions. Forgetting a session key changes credential lookup for the next OpenAlex request, including the next request made by a report already running.

Never place `OPENALEX_API_KEY` or another credential in source code, Docker build arguments, repository variables, issue reports, URLs, report inputs, or screenshots. Use a local secret manager, a container runtime secret, or a private Hugging Face Space secret. A key entered into the public hosted interface necessarily passes through that server over HTTPS and is therefore less private than local execution.

## Deployment expectations

- Terminate TLS only at a trusted platform endpoint and configure its exact external authority in Pharos.
- Do not derive trust from client-supplied forwarding headers.
- Keep the container unprivileged and the application data directory ephemeral.
- Apply edge-level request and abuse controls in addition to in-process session budgets.
- Do not promise persistence for hosted reports or session credentials.
- Review dependency, base-image, and platform security updates before deployment.
