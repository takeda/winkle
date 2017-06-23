FROM us.gcr.master.openx.org/ox-registry/registry.hub.docker.com/library/alpine:3.6

RUN apk update && \
    apk add haproxy=1.7.5-r1 \
            python3=3.6.1-r3 \
            ca-certificates \
            socat=1.7.3.2-r1

RUN pip3.6 install --trusted-host maven.openx.org -i https://maven.openx.org/artifactory/api/pypi/pypi-virtual/simple winkle
RUN mkdir /var/run/winkle
