# ========================================
# Stage 1: Builder
# ========================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies to /opt/venv
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# ========================================
# Stage 2: Runtime
# ========================================
FROM python:3.12-slim

WORKDIR /app

# Create user FIRST (before copying files)
RUN useradd -m -u 1000 appuser

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv with correct ownership (NO separate chown layer)
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code with correct ownership
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Set PATH
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
