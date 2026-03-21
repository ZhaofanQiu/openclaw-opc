#!/bin/bash
# OpenClaw OPC - Cloudflare Tunnel Setup Script
# 
# This script helps you quickly set up Cloudflare Tunnel for secure external access
# to your OpenClaw OPC Dashboard without needing a public IP.
#
# Usage:
#   chmod +x scripts/setup_tunnel.sh
#   ./scripts/setup_tunnel.sh
#
# Documentation: docs/CLOUDFLARE_TUNNEL.md

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "   Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running or you don't have permission to use Docker."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env file created. Please review and edit it."
        else
            print_error ".env.example not found. Please ensure you're in the project root directory."
            exit 1
        fi
    fi
}

# Pull cloudflared image
pull_cloudflared() {
    print_header "Pulling Cloudflared Image"
    docker pull cloudflare/cloudflared:latest
    print_success "Cloudflared image pulled successfully"
}

# Login to Cloudflare
cloudflare_login() {
    print_header "Cloudflare Authentication"
    echo ""
    echo "This will open your browser to authenticate with Cloudflare."
    echo "Please make sure you have a Cloudflare account."
    echo ""
    read -p "Press Enter to continue..."
    
    echo ""
    print_info "Starting Cloudflare login..."
    docker run --rm -it \
        -v "$HOME/.cloudflared:/etc/cloudflared" \
        cloudflare/cloudflared:latest tunnel login
    
    if [ $? -eq 0 ]; then
        print_success "Successfully authenticated with Cloudflare"
    else
        print_error "Failed to authenticate with Cloudflare"
        exit 1
    fi
}

# Create tunnel
create_tunnel() {
    print_header "Creating Cloudflare Tunnel"
    
    echo ""
    read -p "Enter a name for your tunnel [opc-dashboard]: " tunnel_name
    tunnel_name=${tunnel_name:-opc-dashboard}
    
    print_info "Creating tunnel: $tunnel_name"
    
    output=$(docker run --rm -it \
        -v "$HOME/.cloudflared:/etc/cloudflared" \
        cloudflare/cloudflared:latest tunnel create "$tunnel_name" 2>&1)
    
    echo "$output"
    
    # Extract tunnel ID
    tunnel_id=$(echo "$output" | grep -oP 'id \K[a-f0-9-]+' | head -1)
    
    if [ -z "$tunnel_id" ]; then
        # Try alternative extraction
        tunnel_id=$(echo "$output" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
    fi
    
    if [ -n "$tunnel_id" ]; then
        print_success "Tunnel created with ID: $tunnel_id"
        echo "$tunnel_id" > "$HOME/.cloudflared/tunnel_id.txt"
    else
        print_warning "Could not extract tunnel ID automatically. Please check the output above."
        read -p "Enter the tunnel ID manually (or press Enter to skip): " tunnel_id
    fi
}

# Get tunnel token
get_tunnel_token() {
    print_header "Retrieving Tunnel Token"
    
    if [ -f "$HOME/.cloudflared/tunnel_id.txt" ]; then
        tunnel_id=$(cat "$HOME/.cloudflared/tunnel_id.txt")
    else
        read -p "Enter your tunnel ID: " tunnel_id
    fi
    
    if [ -z "$tunnel_id" ]; then
        print_error "Tunnel ID is required"
        exit 1
    fi
    
    print_info "Getting token for tunnel: $tunnel_id"
    
    # Try to get token
    token=$(docker run --rm \
        -v "$HOME/.cloudflared:/etc/cloudflared" \
        cloudflare/cloudflared:latest tunnel token "$tunnel_id" 2>&1)
    
    if [ $? -eq 0 ] && [ -n "$token" ]; then
        print_success "Token retrieved successfully"
        echo ""
        echo -e "${GREEN}Your Tunnel Token:${NC}"
        echo "===================================="
        echo "$token"
        echo "===================================="
        echo ""
        
        # Save token to file
        echo "$token" > "$HOME/.cloudflared/tunnel_token.txt"
        print_info "Token saved to: $HOME/.cloudflared/tunnel_token.txt"
        
        # Ask if user wants to update .env file
        echo ""
        read -p "Update .env file with this token? [Y/n]: " update_env
        update_env=${update_env:-Y}
        
        if [[ $update_env =~ ^[Yy]$ ]]; then
            update_env_file "$token"
        fi
    else
        print_error "Failed to retrieve token"
        echo "$token"
        exit 1
    fi
}

# Update .env file with token
update_env_file() {
    local token=$1
    
    if [ -f ".env" ]; then
        # Check if CLOUDFLARE_TUNNEL_TOKEN already exists
        if grep -q "^CLOUDFLARE_TUNNEL_TOKEN=" .env; then
            # Update existing token
            sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=$token|" .env
        else
            # Add new token
            echo "" >> .env
            echo "# Cloudflare Tunnel Configuration" >> .env
            echo "CLOUDFLARE_TUNNEL_TOKEN=$token" >> .env
        fi
        
        # Also enable API Key authentication
        if grep -q "^API_KEY_AUTH_ENABLED=" .env; then
            sed -i 's/^API_KEY_AUTH_ENABLED=.*/API_KEY_AUTH_ENABLED=true/' .env
        else
            echo "API_KEY_AUTH_ENABLED=true" >> .env
        fi
        
        # Generate API_KEY_SECRET if not exists
        if ! grep -q "^API_KEY_SECRET=" .env || grep -q "^API_KEY_SECRET=change-me" .env; then
            new_secret=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | head -1)
            if grep -q "^API_KEY_SECRET=" .env; then
                sed -i "s|^API_KEY_SECRET=.*|API_KEY_SECRET=$new_secret|" .env
            else
                echo "API_KEY_SECRET=$new_secret" >> .env
            fi
            print_success "Generated secure API_KEY_SECRET"
        fi
        
        print_success ".env file updated"
    else
        print_error ".env file not found"
    fi
}

# Configure DNS
configure_dns() {
    print_header "Configuring DNS"
    
    if [ -f "$HOME/.cloudflared/tunnel_id.txt" ]; then
        tunnel_id=$(cat "$HOME/.cloudflared/tunnel_id.txt")
    else
        read -p "Enter your tunnel ID: " tunnel_id
    fi
    
    echo ""
    echo "You can configure DNS in two ways:"
    echo "1. Use a custom domain (you need to own the domain and add it to Cloudflare)"
    echo "2. Use Cloudflare's free trycloudflare.com domain (temporary, for testing)"
    echo ""
    
    read -p "Do you want to configure DNS now? [Y/n]: " configure_dns
    configure_dns=${configure_dns:-Y}
    
    if [[ ! $configure_dns =~ ^[Yy]$ ]]; then
        print_info "Skipping DNS configuration. You can do this later from Cloudflare Dashboard."
        return
    fi
    
    read -p "Enter your domain (e.g., opc.yourdomain.com): " domain
    
    if [ -z "$domain" ]; then
        print_warning "No domain provided, skipping"
        return
    fi
    
    print_info "Configuring DNS route: $domain → tunnel $tunnel_id"
    
    docker run --rm -it \
        -v "$HOME/.cloudflared:/etc/cloudflared" \
        cloudflare/cloudflared:latest tunnel route dns "$tunnel_id" "$domain"
    
    if [ $? -eq 0 ]; then
        print_success "DNS configured successfully: $domain"
        
        # Update CORS_ORIGINS in .env
        if [ -f ".env" ]; then
            # Extract domain for CORS
            cors_domain="https://$domain"
            if grep -q "^CORS_ORIGINS=" .env; then
                sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$cors_domain|" .env
            else
                echo "CORS_ORIGINS=$cors_domain" >> .env
            fi
            print_success "Updated CORS_ORIGINS in .env"
        fi
    else
        print_error "Failed to configure DNS"
        print_info "You can manually configure DNS from Cloudflare Dashboard:"
        print_info "  https://dash.cloudflare.com/ → Zero Trust → Access → Tunnels"
    fi
}

# Start services
start_services() {
    print_header "Starting OpenClaw OPC with Cloudflare Tunnel"
    
    read -p "Do you want to start the services now? [Y/n]: " start_now
    start_now=${start_now:-Y}
    
    if [[ $start_now =~ ^[Yy]$ ]]; then
        print_info "Starting services with docker-compose.prod.yml..."
        
        if docker-compose -f docker-compose.prod.yml up -d; then
            print_success "Services started successfully"
            echo ""
            echo -e "${GREEN}Your OpenClaw OPC is now running!${NC}"
            echo ""
            echo "Check status:"
            echo "  docker-compose -f docker-compose.prod.yml ps"
            echo ""
            echo "View logs:"
            echo "  docker-compose -f docker-compose.prod.yml logs -f"
            echo ""
            echo "If you configured a custom domain, access it via:"
            if [ -f "$HOME/.cloudflared/last_domain.txt" ]; then
                domain=$(cat "$HOME/.cloudflared/last_domain.txt")
                echo "  https://$domain"
            else
                echo "  https://your-domain.com (replace with your actual domain)"
            fi
        else
            print_error "Failed to start services"
            exit 1
        fi
    else
        print_info "You can start services later with:"
        echo "  docker-compose -f docker-compose.prod.yml up -d"
    fi
}

# Show menu
show_menu() {
    echo ""
    print_header "OpenClaw OPC - Cloudflare Tunnel Setup"
    echo ""
    echo "This script will guide you through:"
    echo "  1. Authenticating with Cloudflare"
    echo "  2. Creating a secure tunnel"
    echo "  3. Getting your tunnel token"
    echo "  4. Configuring DNS (optional)"
    echo "  5. Starting the services"
    echo ""
    echo "Choose an option:"
    echo "  1) Full Setup (Recommended)"
    echo "  2) Login to Cloudflare only"
    echo "  3) Create tunnel only"
    echo "  4) Get token from existing tunnel"
    echo "  5) Configure DNS only"
    echo "  6) Start services only"
    echo "  0) Exit"
    echo ""
    read -p "Enter your choice [1]: " choice
    choice=${choice:-1}
    
    case $choice in
        1)
            check_docker
            check_env_file
            pull_cloudflared
            cloudflare_login
            create_tunnel
            get_tunnel_token
            configure_dns
            start_services
            ;;
        2)
            check_docker
            pull_cloudflared
            cloudflare_login
            ;;
        3)
            check_docker
            pull_cloudflared
            create_tunnel
            ;;
        4)
            check_docker
            pull_cloudflared
            get_tunnel_token
            ;;
        5)
            check_docker
            configure_dns
            ;;
        6)
            start_services
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    # Check if running in project root
    if [ ! -f "docker-compose.prod.yml" ]; then
        print_error "Please run this script from the project root directory"
        echo "  cd /path/to/openclaw-opc"
        echo "  ./scripts/setup_tunnel.sh"
        exit 1
    fi
    
    # If arguments provided, run specific function
    if [ $# -gt 0 ]; then
        case $1 in
            login)
                check_docker
                pull_cloudflared
                cloudflare_login
                ;;
            create)
                check_docker
                pull_cloudflared
                create_tunnel
                ;;
            token)
                check_docker
                get_tunnel_token
                ;;
            dns)
                check_docker
                configure_dns
                ;;
            start)
                start_services
                ;;
            *)
                echo "Usage: $0 [login|create|token|dns|start]"
                exit 1
                ;;
        esac
    else
        # Interactive menu
        show_menu
    fi
    
    echo ""
    print_header "Setup Complete!"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Review your .env file: cat .env"
    echo "  2. Create an API Key for Dashboard access:"
    echo "     python3 create_api_key.py"
    echo "  3. Access your Dashboard via the configured domain"
    echo ""
    echo -e "${BLUE}For troubleshooting, see:${NC}"
    echo "  docs/CLOUDFLARE_TUNNEL.md"
    echo ""
}

main "$@"
