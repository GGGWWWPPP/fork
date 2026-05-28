#!/bin/bash
# Auto-Heal Watchdog
# Checks RAM usage every 5 minutes and drops caches or restarts services if >95%

THRESHOLD=95

while true; do
    # Calculate memory usage percentage
    MEM_USAGE=$(free | grep Mem | awk '{print $3/$2 * 100.0}' | cut -d'.' -f1)
    
    if [ "$MEM_USAGE" -gt "$THRESHOLD" ]; then
        echo "$(date): High memory usage detected: ${MEM_USAGE}%. Triggering auto-heal..."
        
        # Drop caches
        sync; echo 3 > /proc/sys/vm/drop_caches
        echo "$(date): Caches dropped."
        
        # Optionally restart Marzban if memory doesn't go down
        sleep 10
        MEM_USAGE_AFTER=$(free | grep Mem | awk '{print $3/$2 * 100.0}' | cut -d'.' -f1)
        if [ "$MEM_USAGE_AFTER" -gt "$THRESHOLD" ]; then
            echo "$(date): Memory still high (${MEM_USAGE_AFTER}%). Restarting Marzban..."
            docker restart nodeconnect-marzban-1
        fi
    else
        echo "$(date): Memory usage normal: ${MEM_USAGE}%."
    fi
    
    sleep 300
done
