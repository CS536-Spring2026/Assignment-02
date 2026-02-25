"""
iperf3_client.py

Purpose:
Acts as the active iperf3 test driver to coordinate both the Control Connection and the Data Stream.
After successfully authenticating with the target server via the Control socket, it dynamically binds
a new ephemeral TCP socket to blast NULL bytes (the Data socket) over the specified duration.

While streaming data, it regularly polls the `tcpinfo.py` module to extract native socket metrics 
(like snd_cwnd and rtt) and writes them out to a dedicated trace.csv file alongside goodput.
"""
import os
import time
import socket
import csv
import json
from proto import Iperf3Client
from tcpinfo import get_tcp_stats_extended

class IperfClientRunner:
    def __init__(self, server_ip, server_port, timeout=10.0):
        self.server_ip = server_ip
        self.server_port = server_port
        self.timeout = timeout
        self.proto = Iperf3Client(server_ip, server_port, timeout)
        self.data_socket = None
        
    def run_test(self, duration, interval, outdir):
        """
        Executes a single test, saving trace to <outdir>/<server_ip>/trace.csv
        and metadata to <outdir>/<server_ip>/meta.json.
        Returns: (success, dict_of_paths, metadata)
        """
        dest_dir = os.path.join(outdir, self.server_ip)
        os.makedirs(dest_dir, exist_ok=True)
        
        trace_path = os.path.join(dest_dir, "trace.csv")
        meta_path = os.path.join(dest_dir, "meta.json")
        
        metadata = {
            "server": self.server_ip,
            "port": self.server_port,
            "start_time": time.time(),
            "duration": duration,
            "interval": interval,
            "status": "started",
            "failure_reason": None
        }

        def connect_cb(ip, port, cookie):
            try:
                print(f"[{ip}] TCP Socket: Binding dedicated stream to port {port}...")
                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.data_socket.settimeout(10.0)
                self.data_socket.connect((ip, port))
                print(f"[{ip}] TCP Socket: Connected. Sending 37-byte authentication cookie...")
                self.data_socket.sendall(cookie)
                return True
            except Exception as e:
                print(f"[{ip}] TCP Socket Error: {e}")
                return False

        def transmit_cb():
            print(f"[{self.server_ip}] Initializing transmission for {duration} seconds with {interval}s TCP_INFO sampling...")
            return self._transmit_data(duration, interval, trace_path)

        print(f"\n[{self.server_ip}] --- Initiating iperf3 test ---")
        print(f"[{self.server_ip}] Opening Control socket on port {self.server_port}...")
        success, reason = self.proto.connect()
        if not success:
            print(f"[{self.server_ip}] Failed to open Control socket: {reason}")
            metadata["status"] = "failed"
            metadata["failure_reason"] = reason
            self._write_meta(meta_path, metadata)
            return False, {"trace": None, "meta": meta_path}, metadata
            
        success, reason = self.proto.run_control_session(duration, connect_cb, transmit_cb)
        
        metadata["end_time"] = time.time()
        
        if success:
            metadata["status"] = "success"
        else:
            metadata["status"] = "failed"
            metadata["failure_reason"] = reason

        self._write_meta(meta_path, metadata)
        
        if self.data_socket:
            try:
                self.data_socket.close()
            except:
                pass
                
        return success, {"trace": trace_path if success else None, "meta": meta_path}, metadata

    def _write_meta(self, path, meta):
        with open(path, 'w') as f:
            json.dump(meta, f, indent=4)

    def _transmit_data(self, duration, interval, trace_path):
        try:
            chunk_size = 16384
            payload = b'\x00' * chunk_size
            
            start_time = time.time()
            end_time = start_time + duration
            last_log_time = start_time
            
            # Initial poll
            initial_stats = get_tcp_stats_extended(self.data_socket)
            last_bytes_acked = initial_stats.get('bytes_acked', 0)
            if not last_bytes_acked:
                last_bytes_acked = 0
            
            total_bytes_sent = 0
            log_entries = []
            
            # To handle non-blocking writes elegantly
            self.data_socket.settimeout(0.5)
            
            while True:
                current_time = time.time()
                if current_time >= end_time:
                    break
                    
                try:
                    self.data_socket.sendall(payload)
                    total_bytes_sent += chunk_size
                except socket.timeout:
                    # Timeout on send means buffer full, we just loop and poll stats
                    pass
                except BlockingIOError:
                    pass
                    
                elapsed = current_time - last_log_time
                if elapsed >= interval:
                    stats = get_tcp_stats_extended(self.data_socket)
                    curr_bytes_acked = stats.get('bytes_acked', 0)
                    
                    if curr_bytes_acked > 0:
                        bytes_in_interval = curr_bytes_acked - last_bytes_acked
                        last_bytes_acked = curr_bytes_acked
                    else:
                        bytes_in_interval = total_bytes_sent - last_bytes_acked
                        last_bytes_acked = total_bytes_sent
                        
                    goodput_bps = (bytes_in_interval / elapsed) * 8
                    
                    log_entries.append({
                        'timestamp': round(current_time - start_time, 3),
                        'goodput_bps': round(goodput_bps, 2),
                        'snd_cwnd': stats.get('snd_cwnd'),
                        'rtt_ms': stats.get('rtt_ms'),
                        'retransmits': stats.get('retransmits'),
                        'rttvar': stats.get('rttvar'),
                        'pacing_rate': stats.get('pacing_rate'),
                        'bytes_sent': stats.get('bytes_sent'),
                        'delivery_rate': stats.get('delivery_rate')
                    })
                    last_log_time = current_time

            with open(trace_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp', 'goodput_bps', 'snd_cwnd', 'rtt_ms', 'retransmits', 
                    'rttvar', 'pacing_rate', 'bytes_sent', 'delivery_rate'
                ])
                writer.writeheader()
                writer.writerows(log_entries)
                
            # Close the data socket NOW so the server can transition to IPERF_DONE
            if self.data_socket:
                self.data_socket.close()
                self.data_socket = None

            return True
        except Exception as e:
            return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--port", type=int, default=5201)
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()
    
    client = IperfClientRunner(args.server, args.port)
    success, paths, meta = client.run_test(args.duration, 0.2, "results")
    print(f"Success: {success}, Reason: {meta.get('failure_reason')}")
