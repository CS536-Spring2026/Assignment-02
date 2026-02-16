import socket
import argparse
import random
import string
import json
import struct
import sys

def generate_iperf_cookie():
  """Generates a 37-byte iperf3 cookie (36 chars + null terminator)."""
  chars = string.ascii_letters + string.digits
  cookie_str = ''.join(random.choice(chars) for _ in range(36))
  # Encode to bytes and append the null byte (\x00)
  return cookie_str.encode('ascii') + b'\x00'

def send_parameters(ctrl_socket, duration):
  """Sends the JSON parameter block required by iperf3."""
  # iperf3 expects specific keys to configure the test
  params = {
      "tcp": True,
      "omit": 0,
      "time": duration,
      "parallel": 1,
      "client_version": "3.1.3" # Spoofing a standard client version
  }
  json_str = json.dumps(params)
  json_bytes = json_str.encode('utf-8')

  # iperf3 requires a 32-bit integer (network byte order) indicating the JSON length
  # struct.pack('>I', length) creates a Big-Endian (network) unsigned int
  length_prefix = struct.pack('>I', len(json_bytes))

  # Send the length, then the actual JSON payload
  ctrl_socket.sendall(length_prefix + json_bytes)
  print(f"Sent JSON parameters: {json_str}")

def main():
  parser = argparse.ArgumentParser(description="Custom iPerf3 Python Client")
  parser.add_argument("--server", type=str, required=True, help="iPerf3 server IP")
  parser.add_argument("--port", type=int, default=5201, help="Server port (default 5201)")
  parser.add_argument("--time", type=int, default=10, help="Test duration in seconds")
  args = parser.parse_args()

  print(f"Starting control connection to {args.server}:{args.port}...")

  try:
    # Establish control connection 
    ctrl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctrl_socket.settimeout(10.0)
    ctrl_socket.connect((args.server, args.port))

    # Send the session cookie
    cookie = generate_iperf_cookie()
    ctrl_socket.sendall(cookie)
    print("Cookie sent.")

    # Perform JSON parameter exchange 
    send_parameters(ctrl_socket, args.time)

    # TODO: Read server response, open the data connection , and transmit data[cite: 15].

  except socket.timeout:
    print(f"Error: Connection to {args.server} timed out.", file=sys.stderr)

    # Exit with non-zero code to tell bash scipt we failed to connect
    sys.exit(-1)
  except Exception as e:
    print(f"Error connecting to {args.server}: {e}", file=sys.stderr)
    sys.exit(-1)
  finally:
    # Ensures proper termination [cite: 16]
    if 'ctrl_socket' in locals():
        ctrl_socket.close()

if __name__ == "__main__":
  main()


