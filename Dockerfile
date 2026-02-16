# Must use the required Ubuntu 24.04 base image [cite: 75]
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

# Set the working directory inside the container
WORKDIR /app

# Create a virtual environment and update the PATH
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy your requirements file and install dependencies
# (e.g., pandas, matplotlib, scikit-learn for Q2 and Q3)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire codebase into the container [cite: 74]
COPY . .

# Make your master automation script executable [cite: 70]
RUN chmod +x run_experiments.sh

# Execute the full experiment pipeline when the container runs 
ENTRYPOINT ["./run_experiments.sh"]
