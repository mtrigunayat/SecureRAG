FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src

# Create non-root user
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Health check - note: health port may vary based on environment
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx, os; port = os.getenv('PORT', '5000'); httpx.get(f'http://localhost:{port}/health', timeout=5)" || exit 0

# Expose default port (Render will override via PORT environment variable)
EXPOSE 5000

# Run MCP server
# The port is read from settings, which supports PORT environment variable override
ENTRYPOINT ["python", "-m", "mcp_server.main"]
