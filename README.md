# Bourne SDKs

This repository holds official client libraries for [Permiso](https://permiso.io). The packages here target the **Custom Hooks API**: your application can send hook events so agent activity shows up in Permiso with consistent **run** correlation (automatic `runId` / `run_id` handling, optional session and user metadata, and `endRun` / `end_run` to close a run).

## Packages

| Package | Language | Published name | Documentation |
|--------|----------|----------------|-----------------|
| [custom-hooks-sdk](custom-hooks-sdk/) | TypeScript (Node.js ≥ 18) | [`@permiso-io/custom-hooks-sdk`](https://www.npmjs.com/package/@permiso-io/custom-hooks-sdk) | [README](custom-hooks-sdk/README.md) |
| [custom-hooks-sdk-py](custom-hooks-sdk-py/) | Python (≥ 3.9) | [`permiso-custom-hooks-sdk`](https://pypi.org/project/permiso-custom-hooks-sdk/) | [README](custom-hooks-sdk-py/README.md) |

Each package README covers installation, quick start, request shape, configuration, run lifecycle, and API surface.

## Repository layout

```
bourne-sdks/
├── custom-hooks-sdk/      # npm package (TypeScript, builds to lib/)
└── custom-hooks-sdk-py/   # PyPI package (src/permiso_custom_hooks/)
```

Packages are developed and versioned independently; there is no root workspace orchestrator.

## Developing locally

**TypeScript SDK** (`custom-hooks-sdk/`):

```bash
cd custom-hooks-sdk
yarn install
yarn test
yarn build
```

**Python SDK** (`custom-hooks-sdk-py/`):

```bash
cd custom-hooks-sdk-py
pip install -e ".[dev]"
pytest
```

Examples that call the live API expect `PERMISO_API_KEY` (see each package README for `.env` placement).

## License

Packages in this repository are released under the **MIT** license unless otherwise noted in a given package.
