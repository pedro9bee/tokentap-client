# Troubleshooting Guide

Common issues and solutions.

## Services Won't Start

### Docker not running

```bash
# Check Docker
docker ps

# macOS: Start Docker Desktop
open -a Docker

# Linux: Start Docker daemon
sudo systemctl start docker
```

### Port already in use

```bash
# Check what's using port 8080
lsof -i :8080

# Or port 3000
lsof -i :3000

# Change ports in docker-compose.yml if needed
```

### Containers fail to start

```bash
# View logs
tokentap logs

# Restart with rebuild
tokentap down
tokentap up --build

# Remove volumes and start fresh (WARNING: deletes data)
docker compose down -v
tokentap up
```

## Proxy Not Intercepting Traffic

### HTTPS_PROXY not set

```bash
# Check environment
echo $HTTPS_PROXY  # Should show: http://127.0.0.1:8080

# Re-run shell integration
tokentap install
source ~/.zshrc  # or ~/.bashrc
```

### Proxy health check fails

```bash
# Test proxy
curl -x http://127.0.0.1:8080 http://localhost/health

# Check proxy container
docker logs tokentap-client-proxy-1

# Restart proxy
tokentap down && tokentap up
```

### HTTPS certificate errors

```bash
# Trust the CA certificate
tokentap install-cert

# Verify certificate exists
ls -la ~/.mitmproxy/mitmproxy-ca-cert.pem

# Copy from container if missing
docker cp tokentap-client-proxy-1:/root/.mitmproxy/mitmproxy-ca-cert.pem ~/.mitmproxy/
```

## Dashboard Not Accessible

### Web container not running

```bash
# Check status
tokentap status

# View web logs
tokentap logs web

# Restart
tokentap down && tokentap up
```

### Port 3000 in use

```bash
# Check what's using it
lsof -i :3000

# Change port in docker-compose.yml
# Or set environment variable
export TOKENTAP_WEB_PORT=3001
tokentap down && tokentap up
```

## MongoDB Connection Issues

### Container not running

```bash
# Check status
docker ps | grep mongodb

# View logs
docker logs tokentap-client-mongodb-1

# Restart
docker restart tokentap-client-mongodb-1
```

### Data corruption

```bash
# Stop services
tokentap down

# Remove data volume (WARNING: deletes all events)
docker volume rm tokentap-client_mongodb_data

# Start fresh
tokentap up
```

## Provider Configuration Issues

### Config not loading

```bash
# Check syntax
cat ~/.tokentap/providers.json | jq .

# View logs for errors
tokentap logs proxy | grep -i error

# Reload config
tokentap reload-config
```

### Provider not detected

```bash
# Check if domain is in config
cat ~/.tokentap/providers.json | jq '.providers.yourprovider.domains'

# Enable capture_all to debug
echo '{"capture_mode":"capture_all"}' > ~/.tokentap/providers.json
tokentap reload-config

# Check captured data
docker exec -it tokentap-client-mongodb-1 mongosh tokentap
db.events.find({provider:"unknown"}).limit(1).pretty()
```

## Service Management Issues

### Service won't auto-start

**macOS:**
```bash
# Check if loaded
launchctl list | grep tokentap

# Reload service
launchctl unload ~/Library/LaunchAgents/com.tokentap.service.plist
launchctl load ~/Library/LaunchAgents/com.tokentap.service.plist

# View logs
tail -f ~/.tokentap/logs/service.log
```

**Linux:**
```bash
# Check status
systemctl --user status tokentap.service

# View logs
journalctl --user -u tokentap.service -n 50

# Restart
systemctl --user restart tokentap.service
```

### Service keeps restarting

```bash
# View error logs
# macOS:
tail -f ~/.tokentap/logs/service.error.log

# Linux:
journalctl --user -u tokentap.service -f

# Common causes:
# - Port already in use
# - Docker not running
# - MongoDB connection failed
```

## Performance Issues

### High CPU usage

```bash
# Check container resources
docker stats

# Reduce logging (edit docker-compose.yml):
# Set LOG_LEVEL=ERROR

# Limit captured data
# Edit ~/.tokentap/providers.json:
# Set capture_full_request: false
```

### High memory usage

```bash
# Check MongoDB memory
docker stats tokentap-client-mongodb-1

# Add MongoDB memory limit (docker-compose.yml):
# mem_limit: 512m
```

### Slow dashboard

```bash
# Check number of events
docker exec -it tokentap-client-mongodb-1 mongosh tokentap
db.events.countDocuments()

# Archive old events
db.events.deleteMany({timestamp: {$lt: new Date("2026-01-01")}})

# Create indexes
db.events.createIndex({timestamp: -1})
db.events.createIndex({provider: 1, timestamp: -1})
```

## Common Error Messages

### "Cannot connect to the Docker daemon"

**Solution**: Start Docker Desktop (macOS) or Docker daemon (Linux)

### "Port 8080 is already allocated"

**Solution**: Another process is using port 8080. Stop it or change tokentap's port

### "CA certificate not found"

**Solution**: Run `tokentap up` first to generate the certificate

### "Unknown provider"

**Solution**: Add provider to `~/.tokentap/providers.json` or enable `capture_mode: "capture_all"`

### "Failed to parse JSON response"

**Solution**: Check if API response format matches provider config

## Getting Help

If you can't resolve the issue:

1. **Check logs**:
   ```bash
   tokentap logs
   ~/.tokentap/logs/service.log
   ```

2. **Gather debug info**:
   ```bash
   tokentap status
   docker ps
   echo $HTTPS_PROXY
   cat ~/.tokentap/providers.json | jq .
   ```

3. **Report issue**:
   - [GitHub Issues](https://github.com/jmuncor/tokentap/issues)
   - Include logs and debug info
   - Specify your platform (macOS/Linux, version)

## See Also

- [Quick Start](01_QUICK_START.md)
- [Installation](02_INSTALLATION.md)
- [Service Management](03_SERVICE_MANAGEMENT.md)
