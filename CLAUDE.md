# Claude Development Instructions

## Backend Testing with Make Commands

Use these make shortcuts for all backend development and testing:

### Starting the Backend
```bash
make up
```
- Starts all services (backend API, PostgreSQL, Redis) in Docker containers
- Backend runs on http://localhost:8000
- Automatically loads environment variables from `backend/.env`

### Viewing Logs
```bash
make logs
```
- Shows real-time logs from all containers
- Research agent findings and thought process appear here
- Use Ctrl+C to exit log viewing

### Stopping the Backend
```bash
make down
```
- Stops and removes all containers
- Preserves data volumes

### Building/Rebuilding
```bash
make build      # Build with cache
make rebuild    # Build without cache (clean build)
```

### Testing the API
After `make up`, test with:
```bash
# Health check
curl http://localhost:8000/health

# Test conversation flow
curl -X POST "http://localhost:8000/api/chat/conversation" \
  -H "Content-Type: application/json" \
  -d '{"message": "I am looking for a Head of Sales at Stripe"}'
```

### Viewing Research Agent Logs
1. Run `make logs` to see real-time logs
2. Look for lines containing:
   - "Starting research for company:"
   - "Company research completed"
   - "Research agent initialized"
   - "Generated X research-driven questions"

### Environment Configuration
- API keys are in `backend/.env`
- Add your Serper API key to enable real web search
- Docker automatically loads the .env file

### Database Access
PostgreSQL runs on localhost:5432 with:
- Username: postgres
- Password: postgres  
- Database: executive_ai

### Common Commands
```bash
# Start and view logs immediately
make up && make logs

# Rebuild and restart
make down && make rebuild && make up

# Quick restart
make down && make up
```

## Important Notes
- Always use `make` commands instead of direct Docker commands
- The backend auto-reloads on code changes when running via `make up`
- Check `make logs` for research agent findings and debugging info
- Environment variables are automatically loaded from `backend/.env`