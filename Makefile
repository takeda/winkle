.PHONY:

PROJECT_PATH ?= github.corp.openx.com

PACKAGE_NAME := winkle

PACKAGE_REGISTRY := us.gcr.master.openx.org/ox-registry/black

SOURCE_VERSION := $(shell git describe --tags --always --dirty)

TAG := $(SOURCE_VERSION)

BUILD_IMAGE_NAME ?= us.gcr.master.openx.org/ox-registry/black/winkle-build
BUILD_IMAGE_TAG ?= latest

release.buildimg:
	docker build -t $(PACKAGE_REGISTRY)/$(PACKAGE_NAME)-build:$(TAG) -f docker/Dockerfile.build .

# Create a release (docker image)
release:
	docker build --build-arg imageName=$(BUILD_IMAGE_NAME) --build-arg imageTag=$(BUILD_IMAGE_TAG) -t $(PACKAGE_REGISTRY)/$(PACKAGE_NAME):$(TAG) -f docker/Dockerfile.release .

# shell into a build container
devshell:
	docker container run \
        --rm \
        --name=winkle-dev \
        -v $(HOME):/home/$(USER) \
        -v $(CURDIR):/src \
        -w /src \
        -ti $(BUILD_IMAGE_NAME):$(BUILD_IMAGE_TAG) \
        /bin/sh
