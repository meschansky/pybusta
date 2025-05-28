#!/bin/bash
set -euo pipefail

# PyBusta Deployment Script for systemd
# This script sets up PyBusta as a systemd service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
PYBUSTA_USER="pybusta"
PYBUSTA_GROUP="pybusta"
INSTALL_DIR="/opt/pybusta"
DATA_DIR="/var/lib/pybusta"
LOG_DIR="/var/log/pybusta"
SERVICE_NAME="pybusta"
FLIBUSTA_SOURCE_DIR=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

create_user() {
    log_info "Creating system user and group: $PYBUSTA_USER"
    if ! getent group "$PYBUSTA_GROUP" > /dev/null 2>&1; then
        groupadd --system "$PYBUSTA_GROUP"
    fi
    
    if ! getent passwd "$PYBUSTA_USER" > /dev/null 2>&1; then
        useradd --system --gid "$PYBUSTA_GROUP" \
                --home-dir "$DATA_DIR" \
                --no-create-home \
                --shell /bin/false \
                --comment "PyBusta service user" \
                "$PYBUSTA_USER"
    fi
}

create_directories() {
    log_info "Creating directory structure"
    
    # Application directory
    mkdir -p "$INSTALL_DIR"
    
    # Data directories
    mkdir -p "$DATA_DIR"/{db,books}
    mkdir -p /tmp/pybusta
    
    # Handle Flibusta directory
    if [[ -n "$FLIBUSTA_SOURCE_DIR" ]]; then
        log_info "Symlinking Flibusta directory from: $FLIBUSTA_SOURCE_DIR"
        
        # Validate source directory exists and has expected structure
        if [[ ! -d "$FLIBUSTA_SOURCE_DIR" ]]; then
            log_error "Flibusta source directory does not exist: $FLIBUSTA_SOURCE_DIR"
            exit 1
        fi
        
        # Check for index file in source directory
        if [[ ! -f "$FLIBUSTA_SOURCE_DIR/flibusta_fb2_local.inpx" ]]; then
            log_warn "Index file not found in source directory: $FLIBUSTA_SOURCE_DIR/flibusta_fb2_local.inpx"
            log_warn "Make sure the index file exists before starting the service"
        fi
        
        # Remove existing directory if it exists
        if [[ -e "$DATA_DIR/fb2.Flibusta.Net" ]]; then
            log_info "Removing existing fb2.Flibusta.Net directory/link"
            rm -rf "$DATA_DIR/fb2.Flibusta.Net"
        fi
        
        # Create symlink
        ln -sf "$FLIBUSTA_SOURCE_DIR" "$DATA_DIR/fb2.Flibusta.Net"
        log_info "Created symlink: $DATA_DIR/fb2.Flibusta.Net -> $FLIBUSTA_SOURCE_DIR"
    else
        # Create empty directory as before
        mkdir -p "$DATA_DIR/fb2.Flibusta.Net"
    fi
    
    # Log directory
    mkdir -p "$LOG_DIR"
    
    # Set ownership
    chown -R "$PYBUSTA_USER:$PYBUSTA_GROUP" "$DATA_DIR"
    chown -R "$PYBUSTA_USER:$PYBUSTA_GROUP" "$LOG_DIR"
    chown "$PYBUSTA_USER:$PYBUSTA_GROUP" /tmp/pybusta
    
    # For symlinked directory, ensure the target is readable by pybusta user
    if [[ -n "$FLIBUSTA_SOURCE_DIR" && -L "$DATA_DIR/fb2.Flibusta.Net" ]]; then
        # We can't change ownership of the source directory (it might be owned by another user)
        # but we can ensure the pybusta user can read it
        if ! sudo -u "$PYBUSTA_USER" test -r "$FLIBUSTA_SOURCE_DIR"; then
            log_warn "The pybusta user may not have read access to: $FLIBUSTA_SOURCE_DIR"
            log_warn "You may need to adjust permissions or add the pybusta user to the appropriate group"
        fi
    fi
}

install_application() {
    log_info "Installing PyBusta application to $INSTALL_DIR"
    
    # Copy source code
    cp -r "$PROJECT_ROOT"/{src,pyproject.toml,README.md} "$INSTALL_DIR/"
    
    # Create and setup virtual environment
    python3 -m venv "$INSTALL_DIR/.venv"
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"
    
    # Set ownership
    chown -R "$PYBUSTA_USER:$PYBUSTA_GROUP" "$INSTALL_DIR"
}

install_systemd_service() {
    local service_file="$1"
    log_info "Installing systemd service: $service_file"
    
    cp "$SCRIPT_DIR/$service_file" "/etc/systemd/system/"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
}

print_post_install() {
    log_info "PyBusta has been deployed successfully!"
    echo
    echo "Configuration:"
    echo "  - Install directory: $INSTALL_DIR"
    echo "  - Data directory: $DATA_DIR"
    echo "  - Log directory: $LOG_DIR"
    echo "  - Service user: $PYBUSTA_USER"
    
    if [[ -n "$FLIBUSTA_SOURCE_DIR" ]]; then
        echo "  - Flibusta data: $DATA_DIR/fb2.Flibusta.Net -> $FLIBUSTA_SOURCE_DIR"
        echo
        echo "Flibusta archive configuration:"
        echo "  ✓ Symlinked to existing directory: $FLIBUSTA_SOURCE_DIR"
        if [[ -f "$FLIBUSTA_SOURCE_DIR/flibusta_fb2_local.inpx" ]]; then
            echo "  ✓ Index file found: flibusta_fb2_local.inpx"
        else
            echo "  ⚠ Index file missing: flibusta_fb2_local.inpx"
        fi
    else
        echo "  - Flibusta data: $DATA_DIR/fb2.Flibusta.Net (empty)"
        echo
        echo "Next steps:"
        echo "  1. Copy your Flibusta archive files to: $DATA_DIR/fb2.Flibusta.Net/"
        echo "  2. Ensure the index file is at: $DATA_DIR/fb2.Flibusta.Net/flibusta_fb2_local.inpx"
    fi
    
    echo
    echo "Service management:"
    echo "  3. Start the service: sudo systemctl start $SERVICE_NAME"
    echo "  4. Check status: sudo systemctl status $SERVICE_NAME"
    echo "  5. View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Environment variables can be customized in: /etc/systemd/system/$SERVICE_NAME.service"
    echo "After changes, run: sudo systemctl daemon-reload && sudo systemctl restart $SERVICE_NAME"
}

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Deploy PyBusta as a systemd service"
    echo
    echo "Options:"
    echo "  --service-file FILE    Systemd service file to use"
    echo "                         (default: pybusta-cli.service)"
    echo "                         Available: pybusta.service, pybusta-cli.service"
    echo
    echo "  --flibusta-dir DIR     Path to existing Flibusta archive directory"
    echo "                         If provided, will create a symlink instead of"
    echo "                         copying files. This directory should contain"
    echo "                         flibusta_fb2_local.inpx and archive files."
    echo
    echo "  --help                 Show this help message"
    echo
    echo "Examples:"
    echo "  # Standard deployment (empty Flibusta directory)"
    echo "  sudo $0"
    echo
    echo "  # Deployment with existing Flibusta archive"
    echo "  sudo $0 --flibusta-dir /mnt/archives/flibusta"
    echo
    echo "  # Use direct module execution service"
    echo "  sudo $0 --service-file pybusta.service"
}

main() {
    log_info "Starting PyBusta deployment"
    
    check_root
    
    # Default to CLI service file
    SERVICE_FILE="pybusta-cli.service"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --service-file)
                if [[ -z "${2:-}" ]]; then
                    log_error "Option --service-file requires an argument"
                    exit 1
                fi
                SERVICE_FILE="$2"
                shift 2
                ;;
            --flibusta-dir)
                if [[ -z "${2:-}" ]]; then
                    log_error "Option --flibusta-dir requires an argument"
                    exit 1
                fi
                FLIBUSTA_SOURCE_DIR="$(realpath "$2")"
                shift 2
                ;;
            --help)
                print_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    if [[ ! -f "$SCRIPT_DIR/$SERVICE_FILE" ]]; then
        log_error "Service file not found: $SCRIPT_DIR/$SERVICE_FILE"
        log_error "Available service files:"
        ls -1 "$SCRIPT_DIR"/*.service 2>/dev/null || log_error "No service files found in $SCRIPT_DIR"
        exit 1
    fi
    
    # Validate flibusta directory if provided
    if [[ -n "$FLIBUSTA_SOURCE_DIR" ]]; then
        if [[ ! -d "$FLIBUSTA_SOURCE_DIR" ]]; then
            log_error "Flibusta directory does not exist: $FLIBUSTA_SOURCE_DIR"
            exit 1
        fi
        log_info "Using existing Flibusta directory: $FLIBUSTA_SOURCE_DIR"
    fi
    
    create_user
    create_directories
    install_application
    install_systemd_service "$SERVICE_FILE"
    print_post_install
}

main "$@" 