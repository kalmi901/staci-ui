# ----------------------
# Stage 1: STACI BUILDER
# ----------------------
# C++ build environment
FROM debian:bookworm-slim AS staci-builder

ARG STACI_COMMIT=c52ec0424ed5e088a47c7e2a629216d777bab5c4

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
    && cmake --build /build/staci/build \
        --target staci staci_split \
        --parallel 1 \
        --verbose


RUN test -x /build/staci/build/staci \
    && test -x /build/staci/build/staci_split

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
    /opt/staci/staci

COPY --from=staci-builder \
    /build/staci/build/staci_split \
    /opt/staci/staci_split

RUN test -x /opt/staci/staci \
    && test -x /opt/staci/staci_split

# Fail the Docke build immedieately if a shared library is missing
RUN ldd /opt/staci/staci \
    && ! ldd /opt/staci/staci | grep "not found" \
    && ldd /opt/staci/staci_split \
    && ! ldd /opt/staci/staci_split | grep "not found"

# Python application dependecies
WORKDIR /app

COPY requirements.txt requirements-deploy.txt ./

RUN pip install --no-cache-dir \
    -r requirements-deploy.txt

# Application source
COPY app.py ./
COPY src ./src
COPY assets ./assets

# Runtime configuration
ENV STACI_EXECUTABLE=/opt/staci/staci
ENV STACI_SPLIT_EXECUTABLE=/opt/staci/staci_split
ENV STACI_UI_DATA_DIR=/data
ENV PORT=8050
ENV DASH_DEBUG=0

RUN mkdir -p /data/uploads /data/runs

EXPOSE 8050

CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--worker-class", "gthread", "--workers", "1", "--threads", "4", "--timeout", "600", "app:server"]