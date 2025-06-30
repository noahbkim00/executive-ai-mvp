# Executive AI MVP

A ChatGPT-like web application for candidate analysis, built with React frontend and FastAPI backend powered by LangChain + OpenAI.

## 🚀 Features

- **Interactive Chat Interface**: ChatGPT-style UI for natural conversations
- **AI-Powered Responses**: OpenAI GPT-4o-mini integration via LangChain
- **Candidate Analysis Focus**: Specialized prompts for evaluating job candidates
- **Real-time Communication**: REST API with error handling and loading states
- **Responsive Design**: Works on desktop and mobile devices
- **Docker-First Development**: One-command setup with hot reload

## 📋 Prerequisites

- **Docker Desktop** - [Download Docker](https://www.docker.com/products/docker-desktop/)
- **OpenAI API Key** - [Get API Key](https://platform.openai.com/api-keys)

Optional for local development:
- **Node.js 20+** - [Download Node.js](https://nodejs.org/)
- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)

## 🏃‍♂️ Quick Start

### 1. Clone and Setup Environment

```bash
git clone <your-repo-url>
cd executive-ai-mvp

# Create backend environment file
cp backend/.env.example backend/.env
# Edit backend/.env and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-key-here
```

### 2. Start the Application

```bash
# Start all services (Backend API + Database + Redis)
make up

# In a new terminal, start the frontend
cd ui
npm install
npm run dev
```

### 3. Access the Application

- **Frontend**: http://localhost:5173 (React chat interface)
- **Backend API**: http://localhost:8000 (FastAPI with auto-docs)
- **API Documentation**: http://localhost:8000/docs

### 4. Test the Chat

1. Open http://localhost:5173
2. Type a message like: "What qualities should I look for in a senior software engineer?"
3. Get AI-powered responses focused on candidate analysis!

## 🛠️ Development Commands

### Docker Commands (Recommended)

```bash
# Start all backend services
make up

# View logs from all services
make logs

# Stop all services
make down

# Rebuild containers (after dependency changes)
make rebuild

# Test the API directly
./test_chat_curl.sh
```

### Frontend Development

```bash
cd ui

# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Run linting
npm run lint

# Type check
npx tsc --noEmit

# Build for production
npm run build
```

### Backend Development (Local)

```bash
cd backend

# Install Poetry (if needed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run the server locally
poetry run uvicorn src.main:app --reload

# Run tests
poetry run pytest
```

## 🏗️ Architecture

### Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- CSS Modules for styling
- Fetch API for backend communication

**Backend:**
- FastAPI (Python web framework)
- LangChain (AI framework)
- OpenAI GPT-4o-mini (language model)
- Pydantic (data validation)
- Uvicorn (ASGI server)

**Infrastructure:**
- Docker Compose (development)
- PostgreSQL 15 (database)
- Redis 7 (caching/queuing)

### Project Structure

```
executive-ai-mvp/
├── backend/                 # FastAPI backend
│   ├── src/
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── config.py       # Settings & environment variables
│   │   ├── models/         # Pydantic models
│   │   ├── routers/        # API endpoints
│   │   │   ├── health.py   # Health check endpoint
│   │   │   └── chat.py     # Chat API endpoint
│   │   └── services/       # Business logic
│   │       └── chat.py     # LangChain + OpenAI integration
│   ├── pyproject.toml      # Python dependencies
│   ├── .env.example        # Environment variables template
│   └── Dockerfile
├── ui/                      # React frontend  
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ChatContainer.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── Message.tsx
│   │   │   └── MessageInput.tsx
│   │   ├── services/       # API communication
│   │   │   └── api.ts
│   │   └── types/          # TypeScript types
│   │       └── chat.ts
│   ├── package.json
│   └── .env                # Frontend environment variables
├── docker-compose.yml       # Multi-container setup
├── Makefile                # Common commands
└── test_chat_curl.sh       # API testing script
```

## 🔧 Configuration

### Environment Variables

**Backend (`backend/.env`):**
```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your-langsmith-api-key-here
```

**Frontend (`ui/.env`):**
```env
VITE_API_URL=http://localhost:8000
```

### API Endpoints

- `GET /` - Redirects to API documentation
- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness check  
- `POST /api/chat/` - Send message, get AI response

### Chat API Usage

```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "What makes a good product manager?"}'
```

## 🐛 Troubleshooting

### Common Issues

**"OPENAI_API_KEY not set" error:**
- Ensure you've created `backend/.env` with your API key
- Restart containers after adding the key: `make down && make up`

**API not connecting:**
- Check if backend is running: `make logs`
- Verify CORS settings in `backend/src/main.py`
- Ensure frontend is using correct API URL

**Frontend not loading:**
- Check if port 5173 is available
- Run `npm install` in the `ui` directory
- Clear browser cache and try again

**Docker issues:**
- Ensure Docker Desktop is running
- Check for port conflicts (8000, 5432, 6379)
- Try rebuilding: `make down && make rebuild && make up`

### Development Tips

**Hot Reload:**
- Backend: Code changes auto-reload in Docker
- Frontend: Changes auto-reload with `npm run dev`

**Debugging:**
- Backend logs: `make logs`
- Frontend: Use browser developer tools
- API testing: Use `/docs` endpoint or `test_chat_curl.sh`

**Adding Dependencies:**
- Backend: Add to `backend/pyproject.toml`, then `make rebuild`
- Frontend: `npm install <package>` in `ui/` directory

## 🚀 Deployment

This is an MVP setup. For production:

1. **Security**: Remove debug mode, add authentication, secure API keys
2. **Scaling**: Use production ASGI server, container orchestration
3. **Monitoring**: Add logging, metrics, error tracking
4. **Database**: Configure production PostgreSQL with migrations

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test with `make up` and `npm run dev`
4. Run linting: `npm run lint` 
5. Submit a pull request

## 📝 License

[Add your license here]

---

**Happy coding!** 🎉 

For questions or issues, please check the troubleshooting section or create an issue.