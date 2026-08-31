# ----------------------
# Stage 1: STACI BUILDER
# ----------------------
# C++ build environment
FROM debian:bookworm-slim AS staci-builder

ARG STACI_COMMIT=892e0a2a02c2ef0da944dfa138df74d39ed12f13

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libsuitesparse-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone https://github.com/hoscsaba/staci.git \
    && cd staci \
    && git checkout ${STACI_COMMIT}

# GCC portability fix for the pinned STACI revision.
RUN grep -q '^#include <algorithm>' /build/staci/src/Csatorna.cpp \
    || sed -i '1i#include <algorithm>' /build/staci/src/Csatorna.cpp

RUN cmake \
        -S /build/staci \
        -B /build/staci/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DSTACI_BUILD_OPTIMIZERS=OFF \
        -DSTACI_ENABLE_HDF5=ON \
        -DBUILD_TESTING=OFF \
    && cmake --build /build/staci/build --parallel 2


RUN test -x /build/staci/build/staci

# ----------------------
# Stage 2: APP RUNTIME
# ----------------------
FROM python:3.13-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsuitesparse-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/staci

COPY --from=staci-builder \
    /build/staci/build/staci \
    /opt/staci/staci

RUN test -x /opt/staci/staci

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
ENV STACI_UI_DATA_DIR=/data
ENV PORT=8050
ENV DASH_DEBUG=0

RUN mkdir -p /data/uploads /data/runs

EXPOSE 8050

CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--worker-class", "gthread", "--workers", "1", "--threads", "4", "--timeout", "600", "app:server"]