# PyBusta Systemd Deployment Guide

This guide explains how to deploy PyBusta as a headless systemd service for production use.

## Quick Deployment

### Standard Deployment

For a standard deployment with an empty Flibusta directory:

```bash
sudo ./deployment/deploy.sh
```

### Deployment with Existing Flibusta Archive

If you already have a Flibusta archive directory, you can symlink it instead of copying:

```bash
sudo ./deployment/deploy.sh --flibusta-dir /path/to/your/flibusta/archive
```

This will:
- Create a dedicated `pybusta` system user
- Set up directory structure in `/opt/pybusta` and `/var/lib/pybusta`
- **Symlink** your existing Flibusta archive directory (saves disk space and time)
- Install PyBusta with all dependencies
- Configure and enable the systemd service

### Deployment Options

| Option | Description | Example |
|--------|-------------|---------|
| `--flibusta-dir DIR` | Symlink existing Flibusta archive directory | `--flibusta-dir /mnt/archives/flibusta` |
| `--service-file FILE` | Choose systemd service file | `--service-file pybusta.service` |
| `--help` | Show help message | `--help` |

**Examples:**

```bash
# Standard deployment (you'll copy files later)
sudo ./deployment/deploy.sh

# Use existing archive directory
sudo ./deployment/deploy.sh --flibusta-dir /home/user/flibusta-mirror

# Use direct module execution with existing archive
sudo ./deployment/deploy.sh --service-file pybusta.service --flibusta-dir /mnt/data/flibusta
```

## Manual Deployment

### 1. Prerequisites

- Linux system with systemd
- Python 3.8+
- Root/sudo access

### 2. Create System User

```bash
sudo groupadd --system pybusta
sudo useradd --system --gid pybusta \
             --home-dir /var/lib/pybusta \
             --no-create-home \
             --shell /bin/false \
             --comment "PyBusta service user" \
             pybusta
```

### 3. Create Directory Structure

```bash
sudo mkdir -p /opt/pybusta
sudo mkdir -p /var/lib/pybusta/{db,books,fb2.Flibusta.Net}
sudo mkdir -p /var/log/pybusta
sudo mkdir -p /tmp/pybusta

# Set ownership
sudo chown -R pybusta:pybusta /var/lib/pybusta
sudo chown -R pybusta:pybusta /var/log/pybusta
sudo chown pybusta:pybusta /tmp/pybusta
```

### 4. Install Application

```bash
# Copy source code
sudo cp -r src pyproject.toml README.md /opt/pybusta/

# Create virtual environment
sudo python3 -m venv /opt/pybusta/.venv
sudo /opt/pybusta/.venv/bin/pip install --upgrade pip
sudo /opt/pybusta/.venv/bin/pip install -e /opt/pybusta

# Set ownership
sudo chown -R pybusta:pybusta /opt/pybusta
```

### 5. Install Systemd Service

Choose one of the service files:

**Option A: Using CLI command (recommended)**
```bash
sudo cp deployment/pybusta-cli.service /etc/systemd/system/pybusta.service
```

**Option B: Direct module execution**
```bash
sudo cp deployment/pybusta.service /etc/systemd/system/
```

Then enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pybusta
```

### 6. Configure Data Location

**Option A: Copy files to the data directory**

Copy your Flibusta archive files to the data directory:

```bash
sudo cp /path/to/your/archives/* /var/lib/pybusta/fb2.Flibusta.Net/
sudo chown -R pybusta:pybusta /var/lib/pybusta/fb2.Flibusta.Net/
```

**Option B: Symlink existing directory (recommended)**

If you have an existing Flibusta archive directory, symlink it instead:

```bash
# Remove the empty directory created earlier
sudo rm -rf /var/lib/pybusta/fb2.Flibusta.Net

# Create symlink to your existing archive
sudo ln -sf /path/to/your/flibusta/archive /var/lib/pybusta/fb2.Flibusta.Net

# Ensure the pybusta user can read the source directory
# You may need to add the pybusta user to the appropriate group
sudo usermod -a -G $(stat -c %G /path/to/your/flibusta/archive) pybusta
```

**Verify the setup:**

Make sure the index file is accessible:
```bash
ls -la /var/lib/pybusta/fb2.Flibusta.Net/flibusta_fb2_local.inpx
```

### 7. Start the Service

```bash
sudo systemctl start pybusta
sudo systemctl status pybusta
```

## Configuration

### Flibusta Archive Management

**Why use symlinks?**

When deploying PyBusta, you have two options for managing Flibusta archive data:

1. **Copy files** to `/var/lib/pybusta/fb2.Flibusta.Net/`
2. **Symlink** an existing directory (recommended)

**Benefits of symlinking:**
- **Saves disk space**: No duplication of potentially large archive files
- **Faster deployment**: No time spent copying gigabytes of data
- **Shared archives**: Multiple PyBusta instances can use the same archive
- **Easy updates**: Update the source directory and all symlinked instances get the new data
- **Backup efficiency**: Only need to backup one copy of archive data

**Considerations:**
- Source directory must remain accessible to the `pybusta` user
- Source directory should not be moved or deleted
- Permissions must be properly configured for the `pybusta` user to read the source

### Environment Variables

The service can be configured via environment variables in the systemd unit file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PYBUSTA_DATA_DIR` | `/var/lib/pybusta` | Base data directory |
| `PYBUSTA_DB_PATH` | `/var/lib/pybusta/db` | Database storage |
| `PYBUSTA_EXTRACT_PATH` | `/var/lib/pybusta/books` | Extracted books location |
| `PYBUSTA_TMP_PATH` | `/tmp/pybusta` | Temporary files |
| `PYBUSTA_INDEX_FILE` | `/var/lib/pybusta/fb2.Flibusta.Net/flibusta_fb2_local.inpx` | Index file path |

### Web Server Configuration

For the CLI-based service, you can modify the command line arguments:

```ini
ExecStart=/opt/pybusta/.venv/bin/pybusta web --host 0.0.0.0 --port 8080
```

### Custom Configuration

To customize the configuration:

1. Edit the service file:
   ```bash
   sudo systemctl edit pybusta
   ```

2. Add your overrides:
   ```ini
   [Service]
   Environment=PYBUSTA_DATA_DIR=/custom/path
   Environment=PYBUSTA_PORT=9000
   ```

3. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart pybusta
   ```

## Service Management

### Basic Operations

```bash
# Start the service
sudo systemctl start pybusta

# Stop the service
sudo systemctl stop pybusta

# Restart the service
sudo systemctl restart pybusta

# Check status
sudo systemctl status pybusta

# Enable auto-start on boot
sudo systemctl enable pybusta

# Disable auto-start
sudo systemctl disable pybusta
```

### Monitoring and Logs

```bash
# View real-time logs
sudo journalctl -u pybusta -f

# View recent logs
sudo journalctl -u pybusta --since "1 hour ago"

# View all logs
sudo journalctl -u pybusta

# Check service status
systemctl is-active pybusta
systemctl is-enabled pybusta
```

### Health Check

The service provides a health endpoint:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status":"healthy","version":"2.0.0"}
```

## Security Considerations

The systemd service includes several security hardening features:

- **Dedicated User**: Runs as `pybusta` system user (no shell access)
- **Limited Permissions**: `NoNewPrivileges=yes`
- **Filesystem Protection**: `ProtectSystem=strict`, `ProtectHome=yes`
- **Private Temp**: `PrivateTmp=yes`
- **Resource Limits**: File and process limits configured

### Additional Security (Optional)

For enhanced security, consider:

1. **Firewall Rules**: Restrict access to port 8080
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 8080
   ```

2. **Reverse Proxy**: Use nginx/apache with SSL
3. **SELinux/AppArmor**: Configure security policies

## Troubleshooting

### Service Won't Start

1. Check service status and logs:
   ```bash
   sudo systemctl status pybusta
   sudo journalctl -u pybusta --since "5 minutes ago"
   ```

2. Verify file permissions:
   ```bash
   ls -la /opt/pybusta/
   ls -la /var/lib/pybusta/
   ```

3. Test manual execution:
   ```bash
   sudo -u pybusta /opt/pybusta/.venv/bin/pybusta web --port 8081
   ```

### Common Issues

1. **Port Already in Use**: Change port in service file
2. **Permission Denied**: Check file ownership and permissions
3. **Index File Missing**: Ensure Flibusta archives are properly copied or symlinked
4. **Python Module Not Found**: Verify virtual environment installation
5. **Symlink Permission Issues**: Ensure `pybusta` user can read the source directory

### Symlink-Specific Troubleshooting

**Issue: Service can't read symlinked Flibusta directory**

```bash
# Check if symlink exists and points to correct location
ls -la /var/lib/pybusta/fb2.Flibusta.Net

# Test if pybusta user can read the source directory
sudo -u pybusta test -r /path/to/source/directory && echo "OK" || echo "Permission denied"

# Check source directory permissions
ls -la /path/to/source/directory

# Add pybusta user to source directory's group
sudo usermod -a -G $(stat -c %G /path/to/source/directory) pybusta

# Alternative: Make source directory readable by others
sudo chmod o+rx /path/to/source/directory
```

**Issue: Symlink broken after moving source directory**

```bash
# Check if symlink is broken
ls -la /var/lib/pybusta/fb2.Flibusta.Net

# Update symlink to new location
sudo rm /var/lib/pybusta/fb2.Flibusta.Net
sudo ln -sf /new/path/to/flibusta/archive /var/lib/pybusta/fb2.Flibusta.Net

# Restart service
sudo systemctl restart pybusta
```

**Issue: Multiple PyBusta instances with same source**

```bash
# This is actually supported! Multiple instances can safely share
# the same source directory via symlinks

# Instance 1
sudo ln -sf /shared/flibusta /var/lib/pybusta1/fb2.Flibusta.Net

# Instance 2  
sudo ln -sf /shared/flibusta /var/lib/pybusta2/fb2.Flibusta.Net
```

### Service File Validation

Test the service file syntax:
```bash
sudo systemd-analyze verify /etc/systemd/system/pybusta.service
```

## Performance Tuning

For high-traffic deployments:

1. **Resource Limits**: Increase in service file
   ```ini
   LimitNOFILE=100000
   LimitNPROC=8192
   ```

2. **Database Optimization**: Consider moving to PostgreSQL for large datasets
3. **Caching**: Implement Redis for search results caching
4. **Load Balancing**: Run multiple instances behind a load balancer

## Backup Strategy

Important data to backup:

- **Database**: `/var/lib/pybusta/db/`
- **Configuration**: `/etc/systemd/system/pybusta.service`
- **Extracted Books**: `/var/lib/pybusta/books/` (if needed)

Example backup script:
```bash
#!/bin/bash
sudo systemctl stop pybusta
sudo tar -czf pybusta-backup-$(date +%Y%m%d).tar.gz \
    /var/lib/pybusta/db \
    /etc/systemd/system/pybusta.service
sudo systemctl start pybusta
```

## Uninstallation

To completely remove PyBusta:

```bash
# Stop and disable service
sudo systemctl stop pybusta
sudo systemctl disable pybusta

# Remove service file
sudo rm /etc/systemd/system/pybusta.service
sudo systemctl daemon-reload

# Remove application and data
sudo rm -rf /opt/pybusta
sudo rm -rf /var/lib/pybusta
sudo rm -rf /var/log/pybusta

# Remove user (optional)
sudo userdel pybusta
sudo groupdel pybusta
``` 