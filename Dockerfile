# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies (MuseScore 3, libraries)
RUN apt-get update && apt-get install -y \
    musescore3 \
    libmusescore3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a working directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will use
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
