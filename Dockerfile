FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpcap-dev \
    sudo \
    vim \
    netcat-openbsd \
    wget \
    curl \
    telnet \
    nmap \
    net-tools \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install OpenCanary using setup.py
RUN pip install --no-cache-dir .

# Fix line endings in bash scripts (Windows -> Unix)
RUN find /app/bin -name "*.sh" -o -name "*" -type f -executable | xargs -I {} dos2unix {} 2>/dev/null || true

# Fix twistd path in opencanaryd script
RUN sed -i 's|${DIR}/twistd|/usr/local/bin/twistd|g' /app/bin/opencanaryd

# Install additional packages for hybrid functionality
RUN pip install --no-cache-dir kafka-python redis prometheus-client flask scapy pcapy-ng

# Set environment variables
ENV PYTHONPATH="/app"

# Set the default application
ENTRYPOINT ["bash", "/app/bin/opencanaryd"]

# Set default arguments
CMD ["--dev", "--uid=nobody", "--gid=nogroup"]