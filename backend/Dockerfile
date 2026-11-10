FROM python:3.12-slim

WORKDIR /app

# System deps for asyncpg, healthchecks, and building C extensions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification first for layer caching
COPY pyproject.toml .
# Create stub package so setuptools can discover 'app' and install all dependencies
RUN mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir -e ".[dev]"

# Copy all application files
COPY . .

# Re-link the package in editable mode to include all real modules
RUN pip install --no-cache-dir --no-deps -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
