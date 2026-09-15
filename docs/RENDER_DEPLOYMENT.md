# Render deployment

Pharos is prepared as a single Docker web service using the root `render.yaml` Blueprint. The initial Blueprint selects Render's free plan so creating the preview cannot silently commit to paid compute. Free instances sleep and have limited memory; upgrade the service before presenting it as a reliable public application if measured report workloads require it.

## Initial preview

1. Create a Render account and connect the canonical GitHub repository.
2. Choose **New → Blueprint** and select this repository.
3. Confirm that Render detected `render.yaml` and the `pharos-openalex` service.
4. Deploy without adding an `OPENALEX_API_KEY`. Visitors begin with anonymous OpenAlex access and may optionally enter a key for their HTTPS session.
5. Verify `/healthz`, load a saved or newly generated report, exercise an export, and confirm that a foreign Host or Origin receives HTTP 403.

The default service authority is configured as `pharos-openalex.onrender.com`. If Render assigns another hostname, update both `PHAROS_ALLOWED_HOSTS` and `PHAROS_ALLOWED_ORIGINS` before testing the application.

## Custom domain

After the private preview is accepted, add `pharos.helenedraux.com` as the service's custom domain in Render. Render will show the exact DNS record to add. Only then change DNS. Both the Render hostname and custom hostname are already allowlisted in the Blueprint so the former remains useful for diagnosis.

## Data and credentials

- The public service is intentionally ephemeral. Active jobs are held in one process and must not be scaled beyond one instance without externalising job and session state.
- Hosted browser sessions are designed to expire after one hour. A restart can delete them earlier. Users must download reports and review records they want to retain.
- Anonymous and operator-key OpenAlex responses may use the shared dated cache. Session-key responses remain inside the session directory and are not shared.
- Do not commit `OPENALEX_API_KEY`, model endpoints, tokens, or Render credentials. If an operator key is added later, set it as a Render secret in the dashboard.
- The public deployment does not configure `PHAROS_SLM_ENDPOINT` or `PHAROS_SLM_MODEL`. Model assistance remains an optional local/self-hosted experiment.

## Release checks

Run locally before deploying:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
node --check src/pharos/web/app.js
node --check src/pharos/xlsx_export.mjs
docker build --tag pharos:render-preview .
```

Render is configured to deploy only after GitHub checks pass. Keep the service on one instance and observe report duration, memory use, OpenAlex request volume, cache growth, queue saturation, and error rates before changing resource limits.

Security or privacy questions about the public service may be sent to `helene.draux@gmail.com`.

