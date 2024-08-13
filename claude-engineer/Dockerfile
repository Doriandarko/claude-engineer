# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install necessary dependencies for downloading and extracting
RUN apt-get update && apt-get install -y curl unzip

# Download the ttyd binary
RUN curl -Lo /usr/local/bin/ttyd https://github.com/tsl0922/ttyd/releases/download/1.6.3/ttyd.x86_64 \
    && chmod +x /usr/local/bin/ttyd

# Copy the current directory contents into the container at /app
COPY . /app

# Install the dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define the command to run ttyd with the application
CMD ["ttyd", "python", "ollama-eng.py"]
