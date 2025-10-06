# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Expose (optional; Railway provides PORT env at runtime)
EXPOSE 8501

# Health check (use PORT if provided)
HEALTHCHECK CMD python -c "import os,requests; requests.get(f'http://localhost:{os.environ.get("PORT","8501")}/_stcore/health')" || exit 1

# Run Streamlit app on provided PORT (fallback 8501)
CMD ["sh", "-c", "streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-8501}"]
