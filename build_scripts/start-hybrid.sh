#!/bin/bash
# Start the hybrid OpenCanary detection system

set -e

echo "🚀 Starting OpenCanary Hybrid Detection System"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start services
echo "🐳 Building and starting services..."
docker-compose -f docker-compose-hybrid.yml up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose-hybrid.yml ps

# Display access information
echo ""
echo "🎉 OpenCanary Hybrid System is running!"
echo "======================================="
echo ""
echo "📱 Service Access URLs:"
echo "  • OpenCanary Honeypot:     http://localhost (ports 21,22,23,80,443,3306)"
echo "  • Kafka UI:               http://localhost:8080"
echo "  • Redis Commander:        http://localhost:8081"
echo "  • Event Processor API:    http://localhost:8082"
echo "  • Prometheus Metrics:     http://localhost:9090"
echo "  • Grafana Dashboards:     http://localhost:3000 (admin/hybrid-admin-2024)"
echo ""
echo "🔧 Management Commands:"
echo "  • View logs:              docker-compose -f docker-compose-hybrid.yml logs -f"
echo "  • Stop system:            docker-compose -f docker-compose-hybrid.yml down"
echo "  • Restart services:       docker-compose -f docker-compose-hybrid.yml restart"
echo ""
echo "🔍 Testing the System:"
echo "  • Test SSH:               ssh admin@localhost"
echo "  • Test FTP:               ftp localhost"
echo "  • Test HTTP:              curl http://localhost"
echo "  • Test Telnet:            telnet localhost 23"
echo ""
echo "📈 Monitoring:"
echo "  • View threats:           curl http://localhost:8082/threats"
echo "  • View metrics:           curl http://localhost:8082/metrics"
echo "  • Kafka topics:           http://localhost:8080"
echo ""
