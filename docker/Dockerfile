# Define base image build arguments (must be before any FROM)
ARG REPO_OWNER=dispatcharr
ARG REPO_NAME=dispatcharr
ARG BASE_TAG=base

# --- Apply enhancements first ---

FROM node:24 AS enhancement-stage

WORKDIR /app
# Copy source code and enhancement script
COPY . /app
COPY apply_enhancements.sh /app/

# Apply enhancements before frontend build
RUN chmod +x /app/apply_enhancements.sh && \
    cd /app && \
    ./apply_enhancements.sh && \
    echo "✓ Dispatcharr enhancements applied successfully"

# --- Build frontend with enhancements ---

FROM node:24 AS frontend-builder

WORKDIR /app/frontend
# Copy enhanced frontend source
COPY --from=enhancement-stage /app/frontend /app/frontend
# remove any node_modules that may have been copied from the host (x86)
RUN rm -rf node_modules || true; \
    npm install --no-audit --progress=false;
RUN    npm run build; \
    rm -rf node_modules .cache

# --- Redeclare build arguments for the next stage ---
ARG REPO_OWNER
ARG REPO_NAME
ARG BASE_TAG

# --- Final image based on the dynamic base ---
FROM ghcr.io/${REPO_OWNER}/${REPO_NAME}:${BASE_TAG} AS final
ENV VIRTUAL_ENV=/dispatcharrpy
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

# Copy enhanced application code
COPY --from=enhancement-stage /app /app
# Copy nginx configuration
COPY ./docker/nginx.conf /etc/nginx/sites-enabled/default
# Clean out existing frontend folder
RUN rm -rf /app/frontend
# Copy built frontend assets (with enhancements)
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Add timestamp argument
ARG TIMESTAMP

# Update version.py with build timestamp if provided
RUN if [ -n "$TIMESTAMP" ]; then \
    echo "Updating timestamp to ${TIMESTAMP} in version.py" && \
    sed -i "s|__timestamp__ = None.*|__timestamp__ = '${TIMESTAMP}'    # Set during CI/CD build process|" /app/version.py && \
    cat /app/version.py; \
    fi

ENTRYPOINT ["/app/docker/entrypoint.sh"]