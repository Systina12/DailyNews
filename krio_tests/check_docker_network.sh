#!/bin/bash
echo "=========================================="
echo "Docker 网络诊断"
echo "=========================================="

echo -e "\n1. FreshRSS 容器信息:"
docker inspect 1Panel-freshrss-WMI | grep -A 10 "Networks"

echo -e "\n2. FreshRSS 容器 IP:"
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 1Panel-freshrss-WMI

echo -e "\n3. FreshRSS 所在网络:"
docker inspect 1Panel-freshrss-WMI | grep "NetworkMode"

echo -e "\n4. 所有 Docker 网络:"
docker network ls

echo -e "\n5. 测试从宿主机访问容器 IP:"
curl -v --connect-timeout 3 http://172.18.0.6/api/greader.php/accounts/ClientLogin 2>&1 | head -20

echo -e "\n6. 测试从宿主机访问 localhost:51264:"
curl -v --connect-timeout 3 http://localhost:51264/api/greader.php/accounts/ClientLogin 2>&1 | head -20

echo -e "\n7. 测试从宿主机访问容器名:"
curl -v --connect-timeout 3 http://1Panel-freshrss-WMI/api/greader.php/accounts/ClientLogin 2>&1 | head -20

echo -e "\n=========================================="
echo "建议:"
echo "  - 如果 localhost:51264 可以访问，使用它"
echo "  - 如果容器 IP 不通，检查 Docker 网络配置"
echo "=========================================="
