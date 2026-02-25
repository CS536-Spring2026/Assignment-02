# -----------------------------------------------------------------------------
# Dockerfile
#
# Purpose:
# Fulfills the Assignment 2 requirement to execute the iperf3 pipeline within a 
# standardized `ubuntu:24.04` Linux container. This ensures that the Python script 
# has native access to the kernel's `tcp_info` structs to extract CWND and RTT.
# -----------------------------------------------------------------------------

# Must use the required Ubuntu 24.04 base image
FROM ubuntu:24.04

# Prevent interactive prompts from stalling the build
ENV DEBIAN_FRONTEND=noninteractive

# Install Python, pip, venv, and basic networking utilities
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    iproute2 \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a virtual environment and update the PATH
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy your requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . .

# Execute the master python script. Additional args to docker run are passed here.
ENTRYPOINT ["python3", "run_all.py"]
