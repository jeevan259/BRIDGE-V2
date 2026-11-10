FROM python:3.12-slim

WORKDIR /app

# System deps for asyncpg, healthchecks, and building C extensions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy project specification first for layer caching
COPY pyproject.toml .
# Create stub package so setuptools can discover 'app' and install all dependencies
RUN mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir -e ".[dev]"

# Copy all application files
COPY . .

# Re-link the package in editable mode to include all real modules
RUN pip install --no-cache-dir --no-deps -e .

# Permissions and start script
RUN chown -R appuser:appuser /app && chmod +x /app/start.sh

USER appuser

ENV PORT=8000
EXPOSE 8000

CMD ["/app/start.sh"]
