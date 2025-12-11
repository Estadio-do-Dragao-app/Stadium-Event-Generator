FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY simulator/ ./simulator/
COPY test.py .

# Create outputs directory
RUN mkdir -p outputs

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "simulator/dragao_simulator.py"]
