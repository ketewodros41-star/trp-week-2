# Automaton Auditor — Containerized Runtime
FROM python:3.11-slim

# Install system dependencies for git and PDF processing
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency manifest and install
COPY pyproject.toml .
RUN uv pip install --system -e .

# Copy source code
COPY . .

# Create audit output directories
RUN mkdir -p audit/report_onself_generated \
    audit/report_onpeer_generated \
    audit/report_bypeer_received

# Default entry point
CMD ["python", "src/graph.py"]
