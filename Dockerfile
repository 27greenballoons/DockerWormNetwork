# Use the same base image as the other Python services
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the worm script into the container
COPY worm.py .

# The command to run the worm will be specified in the docker-compose.yaml
