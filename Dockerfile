FROM alpine:latest

RUN apk -U add \
    py2-pip py2-requests py2-yaml \
    openssh-client rsync \
    curl zip unzip

# Install the CI scripts
ADD dist /dist
RUN pip install /dist/wordpress-cd-0.2.14.tar.gz

# Source to be built should be mounted here
WORKDIR /src
