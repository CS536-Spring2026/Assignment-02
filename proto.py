"""
proto.py

Purpose:
Handles the state machine for the iperf3 Control Connection Protocol (Port 5201/5202).
Exchanges initialization parameters, parses JSON state signals (like TEST_START and TEST_RUNNING),
creates the 37-byte hashed cookie needed for authentication, and triggers callback functions
precisely when the server signals it is ready.
"""
import socket
import struct
import json
import random
import string

class ProtocolError(Exception):
    pass

class Iperf3Client:
    """Robust handling of iperf3 Control Connection."""

    # iperf3 States
    TEST_START = 1
    TEST_RUNNING = 2
    TEST_END = 4
    PARAM_EXCHANGE = 9
    CREATE_STREAMS = 10
    SERVER_TERMINATE = 11
    CLIENT_TERMINATE = 12
    EXCHANGE_RESULTS = 13
    DISPLAY_RESULTS = 14
    IPERF_START = 15
    IPERF_DONE = 16
    ACCESS_DENIED = -1
    SERVER_ERROR = -2

    def __init__(self, server_ip, server_port, timeout=10.0):
        self.server_ip = server_ip
        self.server_port = server_port
        self.timeout = timeout
        self.cookie = self._generate_cookie()
        self.ctrl_socket = None

    def _generate_cookie(self):
        """Generates 37-byte cookie (36 chars + null terminator)."""
        import os
        chars = string.ascii_letters + string.digits
        # We must use os.urandom or a distinct Random instance because
        # run_all.py calls random.seed() making cookies identical across test reruns!
        cookie_str = ''.join(chars[b % len(chars)] for b in os.urandom(36))
        return cookie_str.encode('ascii') + b'\x00'

    def connect(self):
        """Establishes control connection."""
        try:
            self.ctrl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ctrl_socket.settimeout(self.timeout)
            self.ctrl_socket.connect((self.server_ip, self.server_port))
            self.ctrl_socket.sendall(self.cookie)
            return True, None
        except socket.timeout:
            return False, "conn_timeout"
        except ConnectionRefusedError:
            return False, "conn_refused"
        except Exception as e:
            return False, f"conn_error_{str(e)}"

    def _read_exact(self, length):
        """Reads exactly length bytes with timeout guards."""
        data = b''
        while len(data) < length:
            chunk = self.ctrl_socket.recv(length - len(data))
            if not chunk:
                raise ProtocolError("socket_closed_prematurely")
            data += chunk
        return data

    def read_state(self):
        try:
            data = self._read_exact(1)
            return data[0]
        except socket.timeout:
            raise ProtocolError("read_state_timeout")

    def send_parameters(self, duration):
        params = {
            "tcp": True,
            "omit": 0,
            "time": duration,
            "parallel": 1,
            "client_version": "3.1.3"
        }
        json_str = json.dumps(params)
        json_bytes = json_str.encode('utf-8')
        length_prefix = struct.pack('>I', len(json_bytes))
        self.ctrl_socket.sendall(length_prefix + json_bytes)

    def send_results(self):
        params = {
            "cpu_util_total": 0,
            "cpu_util_user": 0,
            "cpu_util_system": 0,
            "sender_has_retransmits": 1,
            "streams": [
                {
                   "id": 1,
                   "bytes": 0,
                   "retransmits": 0,
                   "jitter": 0,
                   "errors": 0,
                   "packets": 0
                }
            ]
        }
        json_bytes = json.dumps(params).encode('utf-8')
        length_prefix = struct.pack('>I', len(json_bytes))
        self.ctrl_socket.sendall(length_prefix + json_bytes)

    def recv_results(self):
        len_bytes = self._read_exact(4)
        json_len = struct.unpack('>I', len_bytes)[0]
        json_bytes = self._read_exact(json_len)
        return json.loads(json_bytes.decode('utf-8'))

    def close(self):
        if self.ctrl_socket:
            try:
                self.ctrl_socket.close()
            except:
                pass

    def run_control_session(self, duration, connect_cb, transmit_cb):
        """
        Runs the state machine.
        Returns (success, reason_string)
        """
        try:
            print(f"[{self.server_ip}] Control session started. Waiting for server states...")
            while True:
                state = self.read_state()

                if state == self.PARAM_EXCHANGE:
                    print(f"[{self.server_ip}] State 9 (PARAM_EXCHANGE) -> Sending JSON testing parameters (TCP, {duration}s).")
                    self.send_parameters(duration)
                
                elif state == self.CREATE_STREAMS:
                    print(f"[{self.server_ip}] State 10 (CREATE_STREAMS) -> Opening dedicated data socket and sending cookie...")
                    success = connect_cb(self.server_ip, self.server_port, self.cookie)
                    if not success:
                        print(f"[{self.server_ip}] Data socket connection failed!")
                        self.ctrl_socket.sendall(bytes([self.CLIENT_TERMINATE]))
                        return False, "data_stream_connect_failed"
                    print(f"[{self.server_ip}] Data socket successfully bound.")
                    
                elif state == self.TEST_START:
                    print(f"[{self.server_ip}] State 1 (TEST_START) -> Server is ready! Blasting payload data...")
                    success = transmit_cb()
                    if not success:
                        print(f"[{self.server_ip}] Data transmission explicitly failed.")
                        self.ctrl_socket.sendall(bytes([self.CLIENT_TERMINATE]))
                        return False, "data_stream_failed"
                    
                    print(f"[{self.server_ip}] Local data transmission loop complete. Signaling TEST_END (4)...")
                    self.ctrl_socket.sendall(bytes([self.TEST_END]))

                elif state == self.TEST_RUNNING:
                    print(f"[{self.server_ip}] State 2 (TEST_RUNNING) -> Server acknowledges testing is active.")
                    pass
                    
                elif state == self.EXCHANGE_RESULTS:
                    print(f"[{self.server_ip}] State 13 (EXCHANGE_RESULTS) -> Sending local statistics to server.")
                    self.send_results()
                    _ = self.recv_results()

                elif state == self.DISPLAY_RESULTS:
                    print(f"[{self.server_ip}] State 14 (DISPLAY_RESULTS) -> Server successfully generated results. Test effectively complete!")
                    return True, "success"

                elif state == self.IPERF_DONE:
                    print(f"[{self.server_ip}] State 16 (IPERF_DONE) -> Server is closing down current test.")
                    return True, "success"

                elif state in (self.SERVER_TERMINATE, self.SERVER_ERROR, self.ACCESS_DENIED):
                    print(f"[{self.server_ip}] Server rejected connection with error state: {state}")
                    return False, f"server_rejected_state_{state}"
                    
        except ProtocolError as e:
            return False, str(e)
        except socket.timeout:
            return False, "run_timeout"
        except Exception as e:
            return False, f"run_error_{type(e).__name__}"
        finally:
            self.close()
