## Docker deploy

This folder contains the production Docker setup for the two-container option:

- `backend` runs FastAPI on port `8000`
- `frontend` serves the React build through Nginx and proxies `/api` and `/ws` to `backend`

Run it from this folder:

```bash
docker compose up --build -d
```

On Windows PowerShell, you can also use:

```powershell
.uild.ps1
```

Build only:

```powershell
.uild.ps1 -BuildOnly
```

Environment:

- Backend reads `../backend/.env` from the host via `env_file`
- Frontend does not need a runtime env file because it uses same-origin proxying

If you change backend config, edit `backend/.env` on the host and restart the backend container.
