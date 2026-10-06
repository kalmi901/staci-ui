# ----------------------
# Stage 1: STACI BUILDER
# ----------------------
# C++ build environment
FROM debian:bookworm-slim AS staci-builder

ARG STACI_COMMIT=b215127e10acce0d404922dbcd2eda623f8f47e2

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libsuitesparse-dev \
    libhdf5-dev \
    libpagmo-dev \
    libeigen3-dev \
    libigraph-dev \
    libarpack2-dev \
    libglpk-dev \
    libplfit-dev \
    nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone https://github.com/hoscsaba/staci.git \
    && cd staci \
    && git checkout ${STACI_COMMIT}

RUN cmake \
        -S /build/staci \
        -B /build/staci/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DSTACI_BUILD_OPTIMIZERS=ON \
        -DSTACI_ENABLE_HDF5=ON \
        -DBUILD_TESTING=OFF \
        -DSTACI_BUILD_CPP_EXAMPLES=OFF \
        -DSTACI_BUILD_MATLAB_MEX=OFF \
    && cmake --build /build/staci/build \
        --target \
            staci \
            staci_split \
            staci_calibrate \
            staci_flush \
        --parallel 1 \
        --verbose


RUN test -x /build/staci/build/staci \
    && test -x /build/staci/build/staci_split \
    && test -x /build/staci/build/staci_calibrate \
    && test -x /build/staci/build/staci_flush

# ----------------------
# Stage 2: APP RUNTIME
# ----------------------
FROM python:3.13-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libumfpack5 \
    libhdf5-103-1 \
    libpagmo8 \
    libigraph3 \
    libarpack2 \
    libglpk40 \
    libplfit0 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/staci

COPY --from=staci-builder \
    /build/staci/build/staci \
    /build/staci/build/staci_split \
    /build/staci/build/staci_calibrate \
    /build/staci/build/staci_flush \
    /opt/staci/

RUN test -x /opt/staci/staci \
    && test -x /opt/staci/staci_split \
    && test -x /opt/staci/staci_calibrate \
    && test -x /opt/staci/staci_flush

# Fail the Docker build immedieately if a shared library is missing
RUN set -eu; \
    for executable in \
        staci \
        staci_split \
        staci_calibrate \
        staci_flush; \
    do \
        ldd "/opt/staci/${executable}"; \
        if ldd "/opt/staci/${executable}" | grep -q "not found"; then \
            echo "Missing shared library for ${executable}" >&2; \
            exit 1; \
        fi; \
    done

# Python application dependecies
WORKDIR /app

COPY requirements.txt requirements-deploy.txt ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && pip install --no-cache-dir -r requirements-deploy.txt \
    && apt-get purge -y --auto-remove g++ \
    && rm -rf /var/lib/apt/lists/*

# Application source
COPY app.py ./
COPY src ./src
COPY assets ./assets

# Runtime configuration
ENV STACI_EXECUTABLE=/opt/staci/staci
ENV STACI_SPLIT_EXECUTABLE=/opt/staci/staci_split
ENV STACI_CALIBRATE_EXECUTABLE=/opt/staci/staci_calibrate
ENV STACI_FLUSH_EXECUTABLE=/opt/staci/staci_flush
ENV STACI_UI_DATA_DIR=/data
ENV PORT=8050
ENV DASH_DEBUG=0

RUN mkdir -p /data/uploads /data/runs

EXPOSE 8050

#CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--worker-class", "gthread", "--workers", "1", "--threads", "4", "--timeout", "600", "app:server"]

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --worker-class gthread --workers 1 --threads 4 --timeout 600 app:server"]

# ----------------------
# Stage 3: TEST
# ----------------------
FROM runtime AS test

COPY requirements-dev.txt pyproject.toml ./

RUN python -m pip install --no-cache-dir \
    -r requirements-dev.txt

COPY tests ./tests

CMD ["python", "-m", "pytest", "-vv"]

# ----------------------
# Stage 4: PRODUCTION
# ----------------------
FROM runtime AS production
