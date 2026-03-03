# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# ripgrep is added for faster code search (rg command)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ripgrep \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy the dependency definitions
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the current project in editable mode to ensure sub-packages are found
RUN pip install -e .

# Expose ports
# 8000: Main app (context_pilot serve)
# 8001: Planning Expert A2A service
EXPOSE 8000 8001

# Set environment variables
ENV PROJECT_ROOT=/app
ENV PYTHONUNBUFFERED=1

# Run entrypoint script
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
