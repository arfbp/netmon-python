"""Independent asyncio-task monitors (ping, dns, http, speedtest,
traceroute, tcpdump). Each monitor implements a common BaseMonitor
interface, owns its own interval/scheduling, and emits results as
domain events rather than writing to the DB directly."""
