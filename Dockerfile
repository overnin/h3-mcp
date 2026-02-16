FROM python:3.11-slim

WORKDIR /app

# Install runtime + dev dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy source, tests, and fixtures
COPY src/ src/
COPY tests/ tests/
COPY pyproject.toml ./

# Default env: listen on all interfaces for container networking
ENV H3_MCP_TRANSPORT=streamable-http
ENV H3_MCP_HOST=0.0.0.0
ENV H3_MCP_PORT=8000

EXPOSE 8000

CMD ["python", "src/h3_mcp/server.py"]
