#!/bin/bash
# Stop the hybrid OpenCanary detection system

echo "🛑 Stopping OpenCanary Hybrid Detection System"
echo "=============================================="

# Stop and remove containers
docker-compose -f docker-compose-hybrid.yml down

# Optional: Remove volumes (uncomment if you want to clear data)
# docker-compose -f docker-compose-hybrid.yml down -v

echo "✅ System stopped successfully"
echo ""
echo "💾 Data is preserved in ./hybrid-data/"
echo "🔄 To start again: ./build_scripts/start-hybrid.sh"
