# Dockerfile

FROM alpine:3.13

RUN apk add --no-cache tinyproxy

# Copy the tinyproxy configuration file
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf

# Copy the start script to the container
COPY start.sh /usr/local/bin/start.sh

# Make the start script executable
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8888

# Run the start script when the container starts
CMD ["/usr/local/bin/start.sh"]
