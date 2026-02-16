# Assignment 2 - CS 536

## Usage

1. `run_experiments.sh` : runs all scripts. optional -n flag for number of destinations.

## Files

1. `iperf_client.py` : establishes iperf connection

## Notes

iperf connection:
  - These are the steps to establishing the connection:
      1. Client opens a standard TCP socket to iperf server
      2. Client generates and sends a cookie. In iperf, this is a 37 byte string, or 36 bytes of alphanumeric characters + 1 byte null-terminator
      3. Server accepts cookie, client sends a JSON object containing configuration info
        1. First needs to send the length, a 4 byte integer
        2. JSON payload
      4. Server parses and sends back a "CREATE_STREAMS" message or its own JSON
      5. Client opens a second TCP connection with same cookie and starts sending data
