ARG IMAGE_TAG
FROM us.gcr.master.openx.org/ox-registry/black/winkle-dev:$IMAGE_TAG

RUN pip3.6 install --trusted-host maven.openx.org -i https://maven.openx.org/artifactory/api/pypi/pypi-virtual/simple winkle

RUN mkdir /var/run/winkle
