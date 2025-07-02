FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install project dependencies (production only)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root --only=main

# Copy backend code
COPY src/ ./src/

# Install the project itself
RUN poetry install --no-interaction --no-ansi

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]