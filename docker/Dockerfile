# 1. Start with a lightweight Python base image
FROM python:3.9-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install necessary system tools for the worm and Flask dependencies
RUN apt-get update && apt-get install -y \
    iproute2 \
    wget \
    curl \
    sshpass \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask requests

# 4. Copy the entire 'flask' folder into the container's '/app'
COPY flask/ .

# 5. Create the upload landing zone and ensure it has write permissions
RUN mkdir -p /uploads && chmod 777 /uploads

# 6. Force Python to print logs to the terminal immediately (no buffering)
ENV PYTHONUNBUFFERED=1

# 7. Inform Docker the container listens on port 8000
EXPOSE 8000

# 8. Start the Flask server
CMD ["python", "app.py"]