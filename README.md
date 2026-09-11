# Overview

**DocPilot** is an AI‑powered tool that generates a polished `README.md` for any GitHub repository. It analyses the codebase, selects the most relevant files, and uses a large language model to draft a README that you can review and edit before it is committed. The service includes a React frontend, a FastAPI backend, and uses Redis for session state.

---

# Quick Start

## Using Docker Compose (recommended)
```bash
# Build and start all services
docker compose up --build
```
- Frontend UI: <http://localhost:3000>
- Backend API: <http://localhost:8081> (interactive docs at `/docs`)

To stop the stack:
```bash
docker compose down
```

## Running Locally (without Docker)
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
uvicorn app.main:app --reload --port 8081
```
### Frontend
```bash
cd frontend
npm ci
npm run dev   # Vite dev server (http://localhost:5173 by default)
```
Make sure the frontend points to the backend API (see **Configuration**).

---

# Tech Stack
| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, Radix UI, Firebase (auth) |
| **Backend** | FastAPI, Uvicorn, Python 3.11, LangChain, LangGraph, PyGithub, Redis |
| **Data Store** | Redis (in‑memory, persisted via Docker volume) |
| **Containerisation** | Docker & Docker Compose |
| **CI/CD** | (not included – can be added by the user) |

---

# Project Structure
```
.
├─ backend/                     # FastAPI service
│   ├─ app/                     # Application code
│   │   ├─ Agent/
│   │   │   ├─ readme_workflow.py
│   │   │   └─ repository_analyzer.py
│   │   ├─ gitfetch/            # GitHub fetch & PR helpers
│   │   ├─ core/                # Shared services (e.g., Redis client)
│   │   └─ main.py              # FastAPI entry point
│   ├─ Dockerfile
│   └─ requirement.txt
├─ frontend/                    # React UI
│   ├─ src/                     # Source code (components, routes, etc.)
│   ├─ .env.example
│   ├─ Dockerfile
│   └─ package.json
├─ docker-compose.yml          # Orchestrates backend, frontend, Redis
└─ serviceAccountKey.json      # Firebase service‑account (mounted at runtime)
```

---

# Configuration

## Backend (`backend/app/.env`)
```env
GROQ_API=your_groq_api_key   # Required for LangChain‑Groq calls
```
Place the file at `backend/app/.env`. The backend also reads the Firebase service‑account JSON that should be located at the repository root as `serviceAccountKey.json`. Docker Compose mounts this file into the container at `/app/app/serviceAccountKey.json` (read‑only).

## Frontend (`frontend/.env`)
Create a copy of `frontend/.env.example` and adjust the values as needed:
```env
VITE_API_URL=http://localhost:8081   # URL of the backend API
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
```
When building with Docker, the environment file is baked into the image; for local development, the `.env` file is read by Vite.

## Docker Compose defaults
- Backend port: **8081** (exposed as `localhost:8081`)
- Frontend port: **3000** (exposed as `localhost:3000`)
- Redis runs on the default port inside the network (`redis://redis:6379/0`).

---

# Running the Project

## Docker Compose (full stack)
```bash
# Start services (backend, frontend, redis)
docker compose up --build
```
- Access the UI at `http://localhost:3000`.
- API docs are available at `http://localhost:8081/docs`.

## Local Development
1. **Backend** – follow the steps in *Quick Start*.
2. **Frontend** – follow the steps in *Quick Start*.
3. Ensure the frontend `VITE_API_URL` points to the backend address.
4. Redis is optional for local testing; the backend will start without it but session persistence will be lost on restart.

---

# Key Dependencies

## Backend (`backend/requirement.txt`)
- **fastapi** – API framework
- **uvicorn** – ASGI server
- **requests** – HTTP client
- **python-dotenv** – `.env` file loading
- **PyGithub** – GitHub API interactions
- **langgraph** – Graph‑based LLM workflow orchestration
- **langchain** – LLM utilities
- **langchain-groq** – Groq provider for LangChain
- **pydantic** – Data validation
- **redis** – Redis client
- **firebase-admin** – Firebase authentication & admin SDK

## Frontend (`frontend/package.json`)
- **react**, **react-dom** – UI library
- **vite** – Build tool & dev server
- **typescript** – Type safety
- **tailwindcss** – Utility‑first CSS framework
- **@radix-ui/react-dropdown-menu**, **@radix-ui/react-slot** – Accessible UI primitives
- **firebase** – Front‑end Firebase SDK (auth)
- **lucide-react**, **react-markdown**, **remark-gfm** – Icons & markdown rendering
- **eslint**, **eslint-plugin-react-hooks**, **eslint-plugin-react-refresh** – Linting
- Additional dev tools for testing and building.

---

# Contributing

Contributions are welcome! Typical areas where help is valuable:
- Extending file‑selection logic (`repository_analyzer.py`) to support more build systems.
- Refining LLM prompts while keeping generated statements grounded in the repository.
- Adding unit/integration tests for the backend workflow and API validation.
- Improving error handling and UI feedback on the frontend.
- Enhancing the GitHub PR creation flow to avoid leaking credentials.

## How to submit a PR
1. Fork the repository and create a feature branch.
2. Keep changes focused and atomic.
3. Do **not** commit any secrets (API keys, Firebase credentials, etc.).
4. Update documentation if you modify the public interface.
5. Run the test suite (if present) and ensure the Docker build still succeeds.
6. Open a pull request with a clear description of the problem, your approach, and verification steps.

---

# API Reference

All endpoints require a Firebase bearer token. Repository‑related calls also need an `X-GitHub-Token` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/fetchrepo` | Provide a GitHub repo URL; returns the first README draft and a `session_id`. |
| `POST` | `/review` | Approve the draft or send feedback for revision (requires `session_id`). |
| `POST` | `/pullrequest` | Create a branch and PR with the final README. |

**Example request body for `/fetchrepo`**
```json
{
  "repo_url": "https://github.com/owner/repository"
}
```
The response includes `status`, `session_id`, `readme`, and `revision`. Keep the `session_id` for subsequent `/review` calls.

---

# Additional Notes
- Redis data is persisted in the Docker volume `redis_data`; removing the volume will clear session history.
- The frontend uses a SPA fallback configuration in Nginx so that direct navigation works.
- Ensure your Firebase project has Authentication enabled and that the service‑account JSON has the necessary permissions.
