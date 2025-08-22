# Stage 1: Build Stage
# Use a Python base image with the required version
FROM python:3.11-slim as builder

# Set working directory inside the container
WORKDIR /app

# Set the CARGO_HOME environment variable to a writable directory.
# This is the key change to fix the "read-only file system" error.
ENV CARGO_HOME=/tmp/.cargo

# Install build dependencies, including rust toolchain for maturin
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    rustc \
    cargo && \
    # Clean up apt cache to reduce image size
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies.
# The --no-cache-dir flag is often used in Docker to prevent storing cache,
# which helps in reducing the final image size.
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final Stage
# Use a lean base image for the final application
FROM python:3.11-slim

# Set working directory in the final image
WORKDIR /app

# Copy the virtual environment from the build stage to the final stage
# This includes all installed packages, including the compiled Rust binaries.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code into the container
# Replace '.' with the correct path to your application code if it's not in the same directory as the Dockerfile.
COPY . .

# Expose the port your application will run on
# This is a standard port for Uvicorn
EXPOSE 8000

# Command to run your application using python
# This runs your application directly using the python interpreter.
CMD ["python", "main.py"]
