#!/bin/bash
echo "=================================================="
echo "   INSIGHT Tool - Troubleshooting Script          "
echo "=================================================="

echo "[1] Checking System Resources..."
echo "Memory:"
free -h
echo ""
echo "Disk Space:"
df -h /
echo ""

echo "[2] Checking Docker Containers..."
docker compose ps -a
echo ""

echo "[3] Checking Docker Logs (Last 50 lines)..."
echo "--- Neo4j Logs ---"
docker compose logs --tail=50 neo4j
echo ""
echo "--- Insight Tool Logs ---"
docker compose logs --tail=50 insight-tool
echo ""

echo "[4] Checking Network..."
echo "Public IP:"
curl -s ifconfig.me
echo ""
echo "Listening Ports:"
netstat -tulpn | grep LISTEN
