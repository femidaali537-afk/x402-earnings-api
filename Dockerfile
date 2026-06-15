# Step 1: Base Image
FROM python:3.11-slim

# Step 2: Install System Tools
RUN apt-get update && apt-get install -y \
    curl build-essential gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Install Node.js
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Step 4: Work Directory
WORKDIR /app

# Step 5: Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Install Node.js Dependencies (YEH MISSING THA ✅)
COPY package*.json ./
RUN npm install

# Step 7: Copy Source Code
COPY . .

# Step 8: Permissions & Ports
RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000

CMD ["bash", "start.sh"]