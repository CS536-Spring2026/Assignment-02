"""
tcpinfo.py

Purpose:
Acts as a cross-platform data extractor for the Linux `TCP_INFO` C-struct.
Uses the `getsockopt` syscall to dump the 256 byte native socket structure into Python,
and carefully unpacks it using precise byte offsets tailored for the Ubuntu 24.04 Kernel (linux/tcp.h).
"""
import socket
import struct
import math

def get_tcp_stats_extended(sock):
    """
    Extracts key metrics and recommended metrics from the Linux TCP_INFO struct.
    Gracefully handles platforms without full TCP_INFO support using math.nan for floats or 0.

    Returns a dictionary:
    {
        'bytes_acked': int or 0,
        'snd_cwnd': int or nan,
        'rtt_ms': float or nan,        # normalized to milliseconds
        'retransmits': int or nan,
        'rttvar': float or nan,
        'pacing_rate': float or nan,
        'bytes_sent': int or nan,
        'delivery_rate': float or nan
    }
    """
    stats = {
        'bytes_acked': 0,
        'snd_cwnd': math.nan,
        'rtt_ms': math.nan,
        'retransmits': math.nan,
        'rttvar': math.nan,
        'pacing_rate': math.nan,
        'bytes_sent': math.nan,
        'delivery_rate': math.nan
    }

    try:
        TCP_INFO = getattr(socket, 'TCP_INFO', 11)
        raw_tcp_info = sock.getsockopt(socket.IPPROTO_TCP, TCP_INFO, 256)
        buffer_len = len(raw_tcp_info)

        # ---------------------------------------------------------
        # Struct parsing based on typical Linux kernel tcp.h offsets
        # ---------------------------------------------------------

        # tcpi_rtt (offset 68, microseconds) -> unsigned int (I)
        if buffer_len >= 72:
            rtt_us = struct.unpack_from('I', raw_tcp_info, 68)[0]
            stats['rtt_ms'] = rtt_us / 1000.0 if rtt_us > 0 else math.nan
        
        # tcpi_rttvar (offset 72, microseconds) -> unsigned int (I)
        if buffer_len >= 76:
            rttvar_us = struct.unpack_from('I', raw_tcp_info, 72)[0]
            stats['rttvar'] = rttvar_us / 1000.0 if rttvar_us > 0 else math.nan

        # tcpi_snd_cwnd (offset 80, MSS segments) -> unsigned int (I)
        if buffer_len >= 84:
            stats['snd_cwnd'] = struct.unpack_from('I', raw_tcp_info, 80)[0]

        # tcpi_total_retrans (offset 100, packets) -> unsigned int (I)
        if buffer_len >= 104:
            stats['retransmits'] = struct.unpack_from('I', raw_tcp_info, 100)[0]

        # tcpi_pacing_rate (offset 104, bytes per second) -> unsigned long long (Q)
        if buffer_len >= 112:
            stats['pacing_rate'] = struct.unpack_from('Q', raw_tcp_info, 104)[0]

        # tcpi_bytes_acked (offset 120, bytes) -> unsigned long long (Q)
        if buffer_len >= 128:
            stats['bytes_acked'] = struct.unpack_from('Q', raw_tcp_info, 120)[0]
        
        # tcpi_delivery_rate (offset 160 in UBUNTU 24.04, bytes per second) -> unsigned long long (Q)
        if buffer_len >= 168:
            stats['delivery_rate'] = struct.unpack_from('Q', raw_tcp_info, 160)[0]

        # tcpi_bytes_sent (offset 200 in UBUNTU 24.04, bytes) -> unsigned long long (Q)
        if buffer_len >= 208:
            stats['bytes_sent'] = struct.unpack_from('Q', raw_tcp_info, 200)[0]

    except (AttributeError, OSError, struct.error):
        # Fallback for systems (like Mac/Windows without WSL) that don't support TCP_INFO
        pass

    return stats
