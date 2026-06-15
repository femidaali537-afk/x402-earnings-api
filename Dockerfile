FROM python:3.10-slim

# Install Node.js & basic tools
RUN apt-get update && apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node deps
COPY package*.json ./
RUN npm install --production

# Copy all files
COPY . .

# Environment setup
ENV PORT=3000
ENV PYTHON_API_URL=http://localhost:8000
RUN chmod +x start.sh

EXPOSE 3000
EXPOSE 8000

CMD ["bash", "start.sh"]
