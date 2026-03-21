FROM python:3.11-slim

# System deps for matplotlib / numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Ensure outputs directory exists
RUN mkdir -p outputs

EXPOSE 8000

CMD ["python", "frontend.py"]
