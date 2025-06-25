# Executive AI MVP

Welcome to the Executive AI MVP project! This guide will help you get up and running quickly.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 20+** - [Download Node.js](https://nodejs.org/)
- **Docker Desktop** - [Download Docker](https://www.docker.com/products/docker-desktop/)
- **Poetry** - Python dependency manager (installation instructions below)

## Quick Start with Docker

The fastest way to get the entire stack running:

```bash
# Start all services (API, PostgreSQL, Redis)
make up

# View logs
make logs

# Stop all services
make down
```

This will start:
- API server on http://localhost:8000
- PostgreSQL database on localhost:5432
- Redis cache on localhost:6379

## Local Development Setup

### Backend Setup

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   poetry install
   ```

3. **Activate the virtual environment**:
   ```bash
   poetry shell
   ```

4. **Run the backend** (placeholder for now):
   ```bash
   python -m src
   ```

### Frontend Setup

1. **Install Node dependencies**:
   ```bash
   cd ui
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```
   
   The frontend will be available at http://localhost:5173

3. **Run linting**:
   ```bash
   npm run lint
   ```

4. **Build for production**:
   ```bash
   npm run build
   ```

## Running Tests

### Backend Tests
```bash
cd backend
poetry run pytest
```

### Frontend Tests
```bash
cd ui
npm run lint
```

## Project Structure

```
executive-ai-mvp/
├── backend/
│   ├── src/              # Python source code
│   │   ├── __init__.py
│   │   └── __main__.py   # Entry point
│   ├── pyproject.toml    # Python dependencies
│   ├── poetry.lock       # Locked dependencies
│   └── Dockerfile        # Backend container definition
├── ui/
│   ├── src/              # React source code
│   ├── package.json      # Node dependencies
│   └── vite.config.ts    # Vite configuration
├── docker-compose.yml    # Multi-container setup
├── Makefile              # Common commands
└── .github/
    └── workflows/
        └── ci.yml        # CI/CD pipeline
```

## Docker Architecture

Our Docker setup includes three services:

1. **API** - Python backend application
   - Built from `backend/Dockerfile`
   - Runs on port 8000
   - Auto-reloads on code changes

2. **PostgreSQL** - Primary database
   - Version: 15
   - Port: 5432
   - Credentials: postgres/postgres
   - Database name: executive_ai

3. **Redis** - Caching and queuing
   - Version: 7-alpine
   - Port: 6379

## Environment Variables

The Docker setup automatically configures:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Continuous Integration

Our CI pipeline runs on every push and pull request:
- Python dependency installation
- Node.js dependency installation
- Python tests (when available)
- Frontend linting

## Common Issues

### Docker not starting?
- Ensure Docker Desktop is running
- Check if ports 8000, 5432, or 6379 are already in use

### Poetry not found?
- Add Poetry to your PATH: `export PATH="$HOME/.local/bin:$PATH"`
- Restart your terminal after installation

### Module 'src' errors?
- Make sure you're in the correct directory
- For backend: `cd backend` before running commands

## Next Steps

The backend currently has a placeholder implementation. To build your application:

1. Choose a web framework (FastAPI, Flask, Django)
2. Update `backend/src/__main__.py` with your application code
3. Add your dependencies to `backend/pyproject.toml`
4. Create your API endpoints and database models

Happy coding! 🚀