# Use Python 3.11 slim image optimized for ARM (Raspberry Pi)
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for I2C and OLED display
RUN apt-get update && apt-get install -y \
    gcc \
    libi2c-dev \
    i2c-tools \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Create a non-root user but keep it in the i2c group for device access
RUN adduser --disabled-password --gecos '' appuser && \
    usermod -a -G i2c appuser && \
    chown -R appuser:appuser /app

# Create directory for database
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Command to run the application
CMD ["python", "main.py"]
