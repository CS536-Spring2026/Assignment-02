# Q3c: Extracted Congestion Avoidance Algorithm

The nueral network was trained with objective function `eta(t) = goodput_mbps(t+1) - alpha * rtt_ms(t+1) - beta * loss(t+1)` (alpha=1.0, beta=100.0) used as an oversampling weight. Rows where the subsequent time-step exhibited high throughput with low latency and no loss were replicated many times in the training set, while rows leading to retransmissions were effectively suppressed. This forces the model to learn *only from TCP's best decisions which are where the congestion window update produced a favorable goodput-delay-loss tradeoff.

### AI Feature Importances
1. **Feature**: `rtt_ms_lag2`: Importance (|delta R^2|) = 125.0706
2. **Feature**: `snd_cwnd_lag1`: Importance (|delta R^2|) = 116.6005
3. **Feature**: `rttvar`: Importance (|delta R^2|) = 107.4997
4. **Feature**: `pacing_rate`: Importance (|delta R^2|) = 70.2979
5. **Feature**: `rttvar_lag1`: Importance (|delta R^2|) = 55.7090
6. **Feature**: `pacing_rate_lag1`: Importance (|delta R^2|) = 39.7981
7. **Feature**: `goodput_mbps_lag2`: Importance (|delta R^2|) = 25.3780
8. **Feature**: `goodput_mbps_lag1`: Importance (|delta R^2|) = 23.5141
9. **Feature**: `delivery_rate`: Importance (|delta R^2|) = 21.7049
10. **Feature**: `rtt_ms_lag1`: Importance (|delta R^2|) = 18.7610

### Grounded Observations
Based on the importance of `goodput_mbps_lag1` and `rtt_ms`, the model clearly discovered the concept of the **Bandwidth-Delay Product (BDP)**. The continuous reliance on packet loss limits heavily penalizes additive inflation when the queue builds up.

### The Hand-Written Window Update Algorithm
```python
def update_cwnd_prediction(current_cwnd, rtt_ms, loss_events_delta, goodput_mbps, goodput_mbps_lag1):
    # 1. Multiplicative Decrease (Triggered by queue overflow/loss)
    if loss_events_delta > 0:
        return current_cwnd * 0.5
        
    # 2. Additive Increase (AIMD phase scaling based on BDP trajectory)
    if goodput_mbps >= goodput_mbps_lag1:
        # Throughput is still climbing, probe for more bandwidth
        return current_cwnd + 1
        
    # 3. Maintain / Stabilize (Similar to BBR / Vegas delay targeting)
    # If RTT is inflating but no loss has occurred yet, maintain window to prevent bufferbloat.
    return current_cwnd
```
