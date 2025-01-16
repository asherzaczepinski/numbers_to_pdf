# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install MuseScore and essential Qt/Xcb libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    musescore3 \
    wget \
    libqt5widgets5 \
    libqt5network5 \
    libqt5gui5 \
    libqt5core5a \
    libqt5printsupport5 \
    libxrender1 \
    libxext6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables so Qt renders offscreen
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Create a working directory
WORKDIR /app

# Copy project files to the container
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will listen on
EXPOSE 8080

# Run the Flask application (no xvfb)
CMD ["python", "app.py"]
