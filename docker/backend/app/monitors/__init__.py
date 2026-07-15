"""Independent asyncio-task monitors (ping, dns, http, speedtest,
traceroute, tcpdump). Each monitor implements a common BaseMonitor
interface, owns its own interval/scheduling, and emits results as
domain events rather than writing to the DB directly.

Modules:
    base.py            BaseMonitor — interval loop, per-tick exception
                        isolation. Task creation is the scheduler's job.
    ping_analytics.py  Pure functions: jitter, rolling avg, packet loss %,
                        severity classification. Zero I/O.
    network_utils.py   Default gateway auto-detection (best-effort,
                        never raises).
    pinger.py           Default ICMP pinger (wraps icmplib).
    ping_monitor.py     PingMonitor — the concrete monitor, wiring
                        analytics + pinger + repository + event bus.
"""
