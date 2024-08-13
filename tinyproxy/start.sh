#!/bin/sh

# Extract the IP address from the OLLAMA_HOST environment variable
OLLAMA_HOST_IP=$(echo $OLLAMA_HOST | sed 's|http://||' | cut -d ':' -f 1)

# Replace the placeholder in the filter file
echo "^${OLLAMA_HOST_IP}$" > /etc/tinyproxy/filter
echo "api.anthropic.com" >> /etc/tinyproxy/filter
echo "api.tavily.com" >> /etc/tinyproxy/filter

# Start tinyproxy
exec tinyproxy -d