# Q2 Observations Helper for 69.48.237.66

## 1. Statistical Correlations (vs Goodput)
| Metric | Pearson | Spearman |
|--------|---------|----------|
| snd_cwnd | 0.078 | 0.234 |
| RTT | -0.068 | 0.004 |
| Retransmits | 0.129 | 0.077 |

## 2. Basic Anomaly Flags
- **RTT Spikes (>50% above mean):** Yes (23 occurrences)
- **Loss Events (intervals with retransmits):** 121
- **Congestion Window Drops:** 97 times

## 3. Notes for Report
- *How does CWND influence Goodput?* -> Look at the correlation table above. A strong positive correlation typically suggests the network is utilizing available bandwidth efficiently, until queues build.
- *What happens during an RTT spike?* -> Check if CWND dropped shortly after. Usually, RTT spikes mean buffer bloat, followed by dropped packets.
- *Anomalous behavior?* -> Ensure the fallback variables recorded NaN where kernel support lacked. Discuss the presence of these events.
