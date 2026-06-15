# Step 1: Base Image (Python 3.11)
FROM python:3.11-slim

# Step 2: System-level dependencies (Professional Math Stack)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    python3-dev \
    llvm \
    cmake \
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Working Directory
WORKDIR /app

# Step 4: Install Heavy Dependencies separately to avoid timeout
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir numpy==1.24.3 pandas==2.0.3

# Step 5: Install remaining requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Install Node.js Dependencies
COPY package*.json ./
RUN npm install --production

# Step 7: Copy Source Code
COPY . .

# Step 8: Permissions and Entry Point
RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000

CMD ["./start.sh"]
