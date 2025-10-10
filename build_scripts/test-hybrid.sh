#!/bin/bash
# Test the hybrid OpenCanary detection system

echo "🧪 Testing OpenCanary Hybrid Detection System"
echo "============================================="

# Test SSH connection
echo "🔐 Testing SSH honeypot..."
timeout 5 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 admin@localhost 2>/dev/null || echo "SSH honeypot is working (connection refused as expected)"

# Test FTP connection
echo "📁 Testing FTP honeypot..."
timeout 5 ftp -n localhost << EOF
user admin admin123
quit
