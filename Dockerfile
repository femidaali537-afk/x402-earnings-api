FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl build-essential gcc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
COPY . .
RUN chmod +x start.sh
EXPOSE 3000
EXPOSE 8000
CMD ["bash", "start.sh"]