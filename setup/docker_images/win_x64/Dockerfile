
# warning, this version is not taggeed/pinned to a version. 
#https://github.com/dockcross/dockcross
FROM dockcross/windows-static-x64

RUN apt update && apt install -y \
    cmake
    #ninja-build \
    #python3 \
    #&& rm -rf /var/lib/apt/lists/*

ENV CC=x86_64-w64-mingw32-gcc \
    CXX=x86_64-w64-mingw32-g++ \
    #CMAKE_GENERATOR=Ninja
