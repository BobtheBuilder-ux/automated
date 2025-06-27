#!/bin/bash

# Keep Alive Script for Automated Job Application Backend
# This script pings the backend every 13 minutes to prevent it from sleeping
# Designed for Render.com free tier which sleeps after 15 minutes of inactivity

# Configuration
BACKEND_URL="https://automated-uayp.onrender.com"
LOG_FILE="/tmp/backend_keepalive.log"
MAX_LOG_SIZE=1048576  # 1MB in bytes

# Function to rotate log file if it gets too large
rotate_log() {
    if [[ -f "$LOG_FILE" && $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt $MAX_LOG_SIZE ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.old"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Log rotated" > "$LOG_FILE"
    fi
}

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to send notification (optional - requires mail command)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Uncomment the following lines if you want email notifications
    # if command -v mail >/dev/null 2>&1; then
    #     echo "$message" | mail -s "Backend Keep-Alive: $status" your-email@example.com
    # fi
    
    log_message "NOTIFICATION: $status - $message"
}

# Function to check backend health
check_backend() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local response
    local http_code
    
    log_message "Checking backend health..."
    
    # Try health endpoint first
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response.tmp \
        --connect-timeout 30 \
        --max-time 60 \
        --retry 2 \
        --retry-delay 5 \
        "$BACKEND_URL/health" 2>/dev/null)
    
    http_code="${response: -3}"
    
    if [[ "$http_code" == "200" ]]; then
        log_message "✅ Backend is healthy (HTTP $http_code)"
        return 0
    else
        log_message "❌ Health check failed (HTTP $http_code)"
        
        # Try alternative endpoint
        response=$(curl -s -w "%{http_code}" -o /tmp/root_response.tmp \
            --connect-timeout 30 \
            --max-time 60 \
            --retry 1 \
            "$BACKEND_URL/" 2>/dev/null)
        
        http_code="${response: -3}"
        
        if [[ "$http_code" =~ ^[23] ]]; then
            log_message "✅ Backend responding on root endpoint (HTTP $http_code)"
            return 0
        else
            log_message "❌ Backend not responding (HTTP $http_code)"
            send_notification "FAILED" "Backend not responding. HTTP Code: $http_code"
            return 1
        fi
    fi
}

# Function to wake up backend
wake_backend() {
    log_message "🚀 Attempting to wake up backend..."
    
    # Try multiple endpoints to ensure backend wakes up
    local endpoints=("/health" "/" "/applications" "/discovery-stats")
    local success=false
    
    for endpoint in "${endpoints[@]}"; do
        log_message "Pinging: $BACKEND_URL$endpoint"
        
        response=$(curl -s -w "%{http_code}" -o /dev/null \
            --connect-timeout 15 \
            --max-time 30 \
            "$BACKEND_URL$endpoint" 2>/dev/null)
        
        http_code="${response: -3}"
        
        if [[ "$http_code" =~ ^[23] ]]; then
            log_message "✅ Backend woke up via $endpoint (HTTP $http_code)"
            success=true
            break
        else
            log_message "⚠️  No response from $endpoint (HTTP $http_code)"
        fi
        
        # Small delay between requests
        sleep 2
    done
    
    if [[ "$success" == "true" ]]; then
        send_notification "SUCCESS" "Backend successfully woken up"
        return 0
    else
        send_notification "FAILED" "Failed to wake up backend after trying all endpoints"
        return 1
    fi
}

# Main execution
main() {
    rotate_log
    log_message "🔄 Starting keep-alive check..."
    
    if check_backend; then
        log_message "✅ Keep-alive successful - backend is running"
    else
        log_message "⚠️  Backend appears down, attempting to wake..."
        if wake_backend; then
            log_message "✅ Wake-up successful"
        else
            log_message "❌ Wake-up failed - manual intervention may be required"
        fi
    fi
    
    log_message "🏁 Keep-alive check completed"
    echo "---" >> "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main