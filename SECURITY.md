# Security

## Reporting a vulnerability

Do not open a public issue containing credentials, personal data, or an exploitable proof of concept. Contact the repository maintainers privately through the security-reporting channel configured on the canonical repository. Include the affected revision, deployment mode, reproduction conditions, and likely impact. Remove all real OpenAlex keys from examples.

## Supported boundary

Pharos is local-only by default. Hosted mode is opt-in and requires exact public Host and Origin allowlists. The current container foundation provides ephemeral session isolation, bounded work, and optional session-only OpenAlex authentication, but still requires platform-level TLS, traffic controls, monitoring, and incident handling. The application verifies that its configured public origins use HTTPS; because TLS normally terminates at the platform edge and untrusted forwarding headers are ignored, the application cannot independently prove the transport scheme of an individual proxy-to-application request.

Anonymous and operator-key OpenAlex responses may use the shared dated public cache. Requests made with a browser-supplied session key use a cache inside that session's ephemeral directory and are never reused across sessions. Forgetting a session key changes credential lookup for the next OpenAlex request, including the next request made by a report already running.

Never place `OPENALEX_API_KEY` or another credential in source code, Docker build arguments, repository variables, issue reports, URLs, report inputs, or screenshots. Use a local secret manager, a container runtime secret, or a private Hugging Face Space secret. A key entered into the public hosted interface necessarily passes through that server over HTTPS and is therefore less private than local execution.

Browser-key mode is a single-process feature. Session identifiers, jobs and plaintext keys live only in that process, so multiple replicas require sticky routing and a process restart ends every session. Do not move session credentials into Redis, a database or another shared store as a routine scaling change: redesign and review encryption, access control, expiry, deletion, logging and incident handling first.

All active browser keys share one server process. Arbitrary code execution, a process-memory dump, an attached debugger, or an unsafe profiling or diagnostics endpoint could therefore expose every active key. Production deployments should disable public debugging and profiling facilities, avoid retaining core dumps, restrict process inspection, and treat this shared-memory exposure as an accepted residual risk of browser-key mode.

## Deployment expectations

- Terminate TLS only at a trusted platform endpoint, configure its exact external authority in Pharos, and prevent clients from reaching the application port except through that trusted endpoint.
- Do not derive trust from client-supplied forwarding headers.
- Keep the container unprivileged and the application data directory ephemeral.
- Apply edge-level request and abuse controls in addition to in-process session budgets.
- Do not promise persistence for hosted reports or session credentials.
- Review dependency, base-image, and platform security updates before deployment.
