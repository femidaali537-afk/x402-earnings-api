# Step 1: Base Image (Python 3.11 use kar rahe hain for neuralforecast)
FROM python:3.11-slim

# Step 2: System Dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    python3-dev \
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Working Directory
WORKDIR /app

# Step 4: Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Step 5: Install Node.js Dependencies
COPY package*.json ./
RUN npm install --production

# Step 6: Copy Source Code
COPY . .

# Step 7: Environment Variables
ENV PORT=3000
ENV PYTHON_API_URL=http://localhost:8000

# Step 8: Permissions & Entry Point
RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000

CMD ["./start.sh"]
