# Assignment 2 - CS 536

## Setup & Prerequisites
If on windows, make sure to run wsl so that you can run the bash script.

**CRITICAL**: You MUST have Docker Engine or **Docker Desktop** open and running before executing this pipeline. Because standard Windows networking lacks the native `linux/tcp.h` `TCP_INFO` metrics, this project strictly runs inside a containerized Ubuntu 24.04 kernel.

## Usage

To automatically compile the Docker image and execute the master pipeline inside the container, use the provided Bash script. Execute this from Git Bash, WSL, or any bash-compatible terminal:

```bash
# Simply run the script. By default, it automatically uses `--server_list server_list.csv -n 10 --duration 60`
./run_experiments.sh

# You can still optionally override the defaults if needed:
# ./run_experiments.sh -n 5 --duration 30

# Fast-forward Mode: Skip Q1/Q2 data collection and ONLY train the Q3 ML model on existing traces:
# ./run_experiments.sh --ml_only

# Recommended: For training a robust ML Model, specify n=25 traces explicitly:
# ./run_experiments.sh -n 25
```


## Files

1. `run_all.py` : Master orchestration script.
2. `runner.py` : Handles iterating over servers and robust retries.
3. `iperf3_client.py` : Binds protocol connection and data transmission loop.
4. `proto.py` : iperf3 Control Connection state machine.
5. `tcpinfo.py` : Extracts native TCP_INFO metrics via `getsockopt`.
6. `plotting.py` : Generates PDFs/PNGs and Markdown observations.

## Notes

iperf connection:
  - These are the steps to establishing the connection:
      1. Client opens a standard TCP socket to iperf server
      2. Client generates and sends a cookie. In iperf, this is a 37 byte string, or 36 bytes of alphanumeric characters + 1 byte null-terminator
      3. Server accepts cookie, client sends a JSON object containing configuration info
        1. First needs to send the length, a 4 byte integer
        2. JSON payload.
      4. Server parses and sends back a "CREATE_STREAMS" message or its own JSON
      5. Client opens a second TCP connection with same cookie and starts sending data
