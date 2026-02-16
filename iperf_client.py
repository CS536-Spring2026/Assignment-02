import socket
import argparse
import random
import string
import json
import struct
import sys
import time
import csv
import os

def get_tcp_stats(sock):
    """
    Extracts key metrics from the Linux TCP_INFO struct.
    Offsets are based on standard Linux kernel tcp.h
    """
    TCP_INFO = getattr(socket, 'TCP_INFO', 11)
    # Grab 128 bytes of the struct from the kernel
    raw_tcp_info = sock.getsockopt(socket.IPPROTO_TCP, TCP_INFO, 128)

    # struct.unpack_from reads specific C-types from the byte buffer
    # 'I' is a 32-bit unsigned integer, 'Q' is a 64-bit unsigned integer
    # tcpi_rtt is typically at offset 28 (microseconds)
    rtt = struct.unpack_from('I', raw_tcp_info, 28)[0]

    # tcpi_snd_cwnd is typically at offset 40 (number of MSS segments)
    snd_cwnd = struct.unpack_from('I', raw_tcp_info, 40)[0]

    # tcpi_total_retrans is typically at offset 64 (total retransmitted packets)
    retransmits = struct.unpack_from('I', raw_tcp_info, 64)[0]

    # tcpi_bytes_acked is at offset 120 (total bytes)
    bytes_acked = struct.unpack_from('Q', raw_tcp_info, 120)[0]
    return bytes_acked, snd_cwnd, rtt, retransmits

def generate_iperf_cookie():
  """
  Generates a 37-byte iperf3 cookie (36 chars + null terminator).
  """
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

def run_data_transmission(server_ip, server_port, cookie, duration):
    """Opens the data socket, sends the cookie, and transmits data."""
    try:
        print(f"Opening data connection to {server_ip}:{server_port}...")
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.settimeout(10.0)
        data_socket.connect((server_ip, server_port))

        # 1. Send the exact same cookie to bind this socket to the control session
        data_socket.sendall(cookie)
        print("Data connection established. Starting transmission...")

        # 2. Prepare a dummy payload (e.g., an 8KB chunk of zeros)
        chunk_size = 8192
        payload = b'\x00' * chunk_size

        start_time = time.time()
        end_time = start_time + duration

        total_bytes_sent = 0

        # Setup for Goodput measurement
        interval = 0.2  # 200ms intervals
        last_log_time = time.time()
        last_bytes_acked = 0

        # Store results for the Q1(c) plots and tables
        goodput_log = []

        # 3. The Transmission Loop
        while time.time() < end_time:
            # Send the payload
            data_socket.sendall(payload)
            total_bytes_sent += chunk_size

            # Check if it is time to measure goodput
            current_time = time.time()
            elapsed_time = current_time - last_log_time

            if elapsed_time >= interval:
                # Extract total bytes acked from the kernel 
                current_bytes_acked, cwnd, rtt, retrans = get_tcp_stats(data_socket)

                # Calculate bytes specifically acked in this exact interval
                bytes_in_interval = current_bytes_acked - last_bytes_acked

                # Apply the formula: (bytes / seconds) * 8 = bits/s 
                goodput_bps = (bytes_in_interval / elapsed_time) * 8

                goodput_log.append((
                    current_time - start_time,
                    goodput_bps,
                    cwnd,
                    rtt,
                    retrans
                ))

                # Reset the counters for the next interval
                last_log_time = current_time
                last_bytes_acked = current_bytes_acked

        print(f"Transmission complete. Pushed {total_bytes_sent / (1024*1024):.2f} MB to the socket buffer.")

        # Log data for 1c) and 2) analysis
        # Ensure the results directory exists
        os.makedirs('./results', exist_ok=True)
        filename = f"./results/{server_ip}_stats.csv"

        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write the header row
            writer.writerow(['timestamp', 'goodput_bps', 'snd_cwnd', 'rtt', 'retransmits'])

            # Write all the logged data
            writer.writerows(goodput_log)

        print(f"Data successfully saved to {filename}")

    except socket.timeout:
        print("Data connection timed out.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Data transmission error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'data_socket' in locals():
            data_socket.close()

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

    # The server needs a brief moment to process the JSON and open its data listener
    time.sleep(0.5)

    # Open the data connection and start the test
    run_data_transmission(args.server, args.port, cookie, args.time)

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


