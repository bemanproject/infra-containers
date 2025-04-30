#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

ARG base_image=mcr.microsoft.com/devcontainers/cpp:1-ubuntu-24.04
FROM ${base_image}

# Create the vscode user
RUN bash <<EOF
    if ! id "vscode" &>/dev/null; then
        apt-get update && apt-get install -y sudo adduser
        useradd -ms /bin/bash -p "" vscode && usermod -aG sudo vscode
    fi
EOF

USER vscode
WORKDIR /tmp

# Install basic utilities, CMake and Ninja.
# Latest CMake needed for most of the beman libraries,
# so we need to install via kitware's apt repo
RUN bash <<EOF
    sudo apt-get install -y ca-certificates gpg wget git
    wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | sudo tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null
    echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ noble main' | sudo tee /etc/apt/sources.list.d/kitware.list >/dev/null
    sudo apt-get update && sudo apt-get install -y cmake

    sudo apt-get install -y ninja-build
EOF

# Newer gcc/ llvm is needed to avoid ASAN Stalling, which is turned on by default across beman projects.
# See: https://github.com/google/sanitizers/issues/1614
# Minimal version: clang-18.1.3, gcc-13.2
ARG compiler_kind=gnu
ARG compiler_version=14

COPY install_compiler.sh .
RUN bash install_compiler.sh ${compiler_kind} ${compiler_version}

# Common dependency: google-test
RUN sudo apt-get install -y libgtest-dev

# Pre-commit is beman library's standard linting tool
RUN sudo apt-get install -y pipx
RUN pipx install pre-commit
ENV PATH="/home/vscode/.local/bin:${PATH}"

ENTRYPOINT ["/usr/bin/bash"]
