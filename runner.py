"""
runner.py

Purpose:
Iterates over the `server_list.csv` provided by the user and attempts to run the `IperfClientRunner`
against each IP/Port combination. Handles gracefully skipping offline servers and logging exact
failure reasons to `results/failures.csv` until `n` successful captures are completed.
"""
import csv
import os
import random
from iperf3_client import IperfClientRunner

def load_server_list(filename):
    servers = []
    if not os.path.exists(filename):
        return servers
        
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None) # Skip header
        for row in reader:
            if not row or not row[0].strip():
                continue
            ip = row[0].strip()
            raw_port = row[1].strip() if len(row) > 1 else ""
            if raw_port:
                port = int(raw_port.split('-')[0].strip())
            else:
                port = 5201
            servers.append((ip, port))
            
    return servers

def run_experiments(server_list_file, n, duration, interval, timeout, seed, outdir):
    os.makedirs(outdir, exist_ok=True)
    failures_log = os.path.join(outdir, "failures.csv")
    
    servers = load_server_list(server_list_file)
    if not servers:
        print(f"Error: Could not load servers from {server_list_file}")
        return

    random.seed(seed)
    random.shuffle(servers)

    success_count = 0
    server_idx = 0
    
    with open(failures_log, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["server_ip", "port", "reason"])

    while success_count < n and server_idx < len(servers):
        ip, port = servers[server_idx]
        server_idx += 1
        
        print(f"[{success_count+1}/{n}] Attempting test on {ip}:{port}...")
        
        runner = IperfClientRunner(ip, port, timeout=timeout)
        success, paths, meta = runner.run_test(duration, interval, outdir)
        
        if success:
            print(f" -> Success! Trace saved to {paths['trace']}")
            success_count += 1
        else:
            reason = meta.get('failure_reason', 'unknown_error')
            print(f" -> Failed: {reason}")
            with open(failures_log, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([ip, port, reason])
                
    if success_count < n:
        print(f"\nWarning: Reached end of server list. Only {success_count}/{n} tests succeeded.")
    else:
        print(f"\nSuccessfully completed all {n} requested tests.")
