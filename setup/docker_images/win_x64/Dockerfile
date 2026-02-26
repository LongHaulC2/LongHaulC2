# warning, this version is not tagged/pinned to a version. 
# https://github.com/dockcross/dockcross
FROM dockcross/windows-static-x64

# Install build dependencies: cmake, ninja, ccache, lld (llvm linker) and python3
RUN apt-get update && apt-get install -y \
    cmake \
    ninja-build \
    ccache \
    python3 \
    lld \
    && rm -rf /var/lib/apt/lists/*

# CCACHE dir with proper perms, for faster build times.
ENV CCACHE_DIR=/var/lib/longhaulc2/ccache
RUN mkdir -p /var/lib/longhaulc2/ccache && chmod 777 /var/lib/longhaulc2/ccache

# Set compiler and force CMake to use Ninja by default
ENV CC=x86_64-w64-mingw32-gcc \
    CXX=x86_64-w64-mingw32-g++ \
    CMAKE_GENERATOR=Ninja