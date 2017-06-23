.PHONY:

PROJECT_PATH ?= github.corp.openx.com

PACKAGE_NAME := winkle

PACKAGE_REGISTRY := us.gcr.master.openx.org/ox-registry/black

SOURCE_VERSION := $(shell git describe --tags --always --dirty)

TAG := $(SOURCE_VERSION)

# Create a release (docker image)
release:
	docker build -t $(PACKAGE_REGISTRY)/$(PACKAGE_NAME):$(TAG) -f Dockerfile .
	@echo "Created $(PACKAGE_REGISTRY)/$(PACKAGE_NAME):$(TAG)"
