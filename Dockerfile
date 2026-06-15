# Use Python 3.10 as base
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    python3-dev \
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies
COPY package*.json ./
RUN npm install --production

# Copy the rest of the code
COPY . .

# Environment variables
ENV PORT=3000
ENV PYTHON_API_URL=http://localhost:8000

# Permissions and Ports
RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000

# Start command
CMD ["./start.sh"]
