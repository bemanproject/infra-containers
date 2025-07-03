# Beman Container Infrastructure

<!--
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

This repository contains the infrastructure for the Beman project's Docker images. See the
organization's [GitHub Packages page](https://github.com/orgs/bemanproject/packages) for
more information.

## Images

This project builds the following images intended for use by CI for Beman libraries:

- `ghcr.io/bemanproject/infra-containers-gcc`
  - `trunk` (rebuilt weekly)
  - `latest`/`15`/`15.1.0`
  - `14`/`14.3.0`
  - `13`/`13.4.0`
  - `12`/`12.4.0`
  - `11`/`11.5.0`
- `ghcr.io/bemanproject/infra-containers-clang`
  - `trunk` (rebuilt weekly)
  - `latest`/`20`/`20.1.7`
  - `19`/`19.1.7`
  - `18`/`18.1.6`
  - `17`/`17.0.6`
- `ghcr.io/bemanproject/infra-containers-clang-p2996`
  - `latest`/`trunk` (rebuilt weekly)

It also builds the following images intended for use by Docker codespaces:

- `ghcr.io/bemanproject/infra-containers-devcontainer-gcc`
  - `latest`/`14`
- `ghcr.io/bemanproject/infra-containers-devcontainer-clang`
  - `latest`/`20`

Along with the compiler version specified in the tag, these images contain CMake 4.0.3 and
recent versions of ninja and git.

## Implementation Details

The CI images are based on Gentoo Linux for the following reasons:

- Its package repository has fast turnaround of new compiler and tool versions, allowing
  us to ensure we can always provide up-to-date versions
- It provides binary caching of packages, improving image build times relative to needing
  to build everything from source
- It gives us an easy way to build compiler forks from source, such as Bloomberg's fork of
  clang that adds support for reflection, by editing ebuild files
  
The devcontainer images are currently based on Ubuntu so that we can use images from
microsoft/devcontainers as a base.

## Adding Packages

If these images are missing a tool that you need, either:

- Submit a pull request adding an `emerge` command to `Dockerfile.test` and
  `Dockerfile.fromsource` with the Gentoo package for that tool (preferred), or:
- Install the tool inline in the CI job:
  - `emerge-webrsync` to restore the package data that the image build process removes to
    save space
  - `emerge <your-package-name>` to install the tool itself.
