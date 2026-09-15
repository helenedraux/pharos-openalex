# Pharos hosting review supplement

This supplement records the container ignore rules, continuous-integration workflow, and current verification status supplied for independent review.

## `.dockerignore`

```dockerignore
.git
.pharos
output
outputs
tmp
tests
docs
*.pyc
__pycache__
.DS_Store
.env
.env.*
*.pem
*.key
*.p12
*.pfx
```

## `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: Python tests
        run: PYTHONPATH=src python -m unittest discover -s tests -v
      - name: JavaScript checks
        run: |
          node --check src/pharos/web/app.js
          node --check src/pharos/xlsx_export.mjs

  container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build --tag pharos:test .
      - name: Smoke-test non-root container and health endpoint
        run: |
          container_id=$(docker run --detach --rm --publish 7860:7860 \
            --env PHAROS_ALLOWED_HOSTS=localhost:7860 \
            --env PHAROS_ALLOWED_ORIGINS=http://localhost:7860 \
            pharos:test)
          trap 'docker stop "$container_id"' EXIT
          for attempt in $(seq 1 20); do
            if curl --fail --silent http://127.0.0.1:7860/healthz; then break; fi
            if [ "$attempt" = 20 ]; then docker logs "$container_id"; exit 1; fi
            sleep 1
          done
          test "$(docker inspect --format '{{.Config.User}}' "$container_id")" = pharos
          curl --fail --silent --header 'Host: localhost:7860' --header 'Sec-Fetch-Site: none' http://127.0.0.1:7860/api/config >/dev/null
          test "$(curl --silent --output /dev/null --write-out '%{http_code}' --header 'Host: hostile.example' http://127.0.0.1:7860/api/config)" = 403
          test "$(curl --silent --output /dev/null --write-out '%{http_code}' --header 'Host: localhost:7860' http://127.0.0.1:7860/api/config)" = 403
          test "$(curl --silent --output /dev/null --write-out '%{http_code}' --header 'Host: localhost:7860' --header 'Sec-Fetch-Site: cross-site' http://127.0.0.1:7860/api/config)" = 403
          test "$(curl --silent --output /dev/null --write-out '%{http_code}' --request POST --header 'Host: localhost:7860' --header 'Origin: http://hostile.example' --header 'Sec-Fetch-Site: same-origin' --header 'Content-Type: application/json' --data '{}' http://127.0.0.1:7860/api/overview)" = 403
```

## Current test summary

- 54 Python tests passed.
- Both JavaScript syntax checks passed:
  - `node --check src/pharos/web/app.js`
  - `node --check src/pharos/xlsx_export.mjs`

## Container-verification caveat

Docker has not been run locally because it is not installed on the development host. The Docker image build, non-root runtime assertion, health check, and Host-header smoke tests therefore await execution and verification by the CI workflow or another Docker-equipped environment.
