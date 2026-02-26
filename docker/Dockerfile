# Use the same base image as the other Python services
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install the requests library required by the script
RUN pip install --no-cache-dir requests

# Copy the worm script into the container
COPY worm.py .

# Ensure Python logs are sent straight to the terminal/dashboard
ENV PYTHONUNBUFFERED=1

# The command to run the worm will be specified in the docker-compose.yaml