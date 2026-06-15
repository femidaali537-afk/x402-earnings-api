FROM python:3.10-slim-bullseye

# System dependencies for math libraries
RUN apt-get update && apt-get install -y \
    curl build-essential gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment Variables
ENV PORT=3000
ENV PYTHON_API_URL=http://localhost:8000

RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000

CMD ["./start.sh"]
