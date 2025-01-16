# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install MuseScore and other system dependencies
RUN apt-get update && apt-get install -y \
    musescore3 \
    xvfb \
    wget \
    libqt5widgets5 \
    libqt5network5 \
    libqt5gui5 \
    libqt5core5a \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Create a working directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will use
EXPOSE 8080

# Run the application
#xvfb-run", 
CMD ["python", "app.py"]
