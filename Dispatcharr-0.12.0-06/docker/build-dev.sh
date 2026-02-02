#!/bin/bash
docker build --build-arg BRANCH=dev -t dispatcharr/dispatcharr:dev -f Dockerfile ..

# Get version information
VERSION=$(python -c "import sys; sys.path.append('..'); import version; print(version.__version__)")

# Build with version tag
docker build --build-arg BRANCH=dev \
  -t dispatcharr/dispatcharr:dev \
  -t dispatcharr/dispatcharr:${VERSION} \
  -f Dockerfile ..
