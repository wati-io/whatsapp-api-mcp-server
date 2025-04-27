FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY whatsapp-api-mcp-server/pyproject.toml whatsapp-api-mcp-server/LICENSE ./

# Install Python dependencies
RUN pip install --no-cache-dir .[cli]

# Copy the source code
COPY whatsapp-api-mcp-server/src ./src
COPY whatsapp-api-mcp-server/run.sh ./

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the entry point
ENTRYPOINT ["python", "-m", "whatsapp_mcp.main"] 