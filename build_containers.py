#!/usr/bin/env python3
"""
Container Build Manager

This script manages the building of Docker containers for the infra-containers project.
It handles building custom Clang compilers and devcontainer images with proper dependency
management and caching.

Usage:
    # Build Clang 21
    ./build_containers.py clang --version 21

    # Build Clang from specific git ref
    ./build_containers.py clang --version 21 --git-ref llvmorg-21.1.2

    # Build devcontainer with Clang 21
    ./build_containers.py devcontainer --clang-version 21

    # Build everything
    ./build_containers.py all --clang-version 21

    # Build with custom parallelism
    ./build_containers.py clang --version 21 --jobs 8

    # Dry run (show what would be built)
    ./build_containers.py all --clang-version 21 --dry-run

Requirements:
    pip install docker
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

try:
    import docker
    from docker.errors import BuildError, ImageNotFound, APIError
except ImportError:
    print("❌ Error: docker package not found. Install it with:", file=sys.stderr)
    print("  pip install docker", file=sys.stderr)
    sys.exit(1)


class ContainerBuilder:
    """Manages building Docker containers with proper dependency handling."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.root_dir = Path(__file__).parent
        self.client = docker.from_env() if not dry_run else None

    def _stream_build_output(self, stream, description: str, log_file: Optional[Path] = None):
        """Stream Docker build output with progress information."""
        print(f"\n🔨 {description}")

        log_handle = None
        if log_file and not self.dry_run:
            log_handle = open(log_file, 'w')

        try:
            for chunk in stream:
                if 'stream' in chunk:
                    text = chunk['stream']
                    if self.verbose:
                        print(text, end='', flush=True)
                    if log_handle:
                        log_handle.write(text)
                        log_handle.flush()
                elif 'status' in chunk:
                    # Show pull/push status
                    if self.verbose:
                        status = chunk['status']
                        if 'id' in chunk:
                            print(f"{chunk['id']}: {status}")
                        else:
                            print(status)
                elif 'error' in chunk:
                    error_msg = chunk['error']
                    print(f"❌ Build error: {error_msg}", file=sys.stderr)
                    if log_handle:
                        log_handle.write(f"ERROR: {error_msg}\n")
                    raise BuildError(error_msg, None)
        finally:
            if log_handle:
                log_handle.close()
                print(f"📝 Build log saved to: {log_file}")

    def _image_exists(self, image_tag: str) -> bool:
        """Check if a Docker image exists locally."""
        if self.dry_run:
            return True

        try:
            self.client.images.get(image_tag)
            return True
        except ImageNotFound:
            return False

    def build_clang(
        self,
        version: int,
        git_ref: Optional[str] = None,
        git_url: str = "https://github.com/llvm/llvm-project.git",
        jobs: int = 4,
        tag_suffix: str = "",
    ) -> int:
        """
        Build a custom Clang compiler image.

        Args:
            version: Major version number for tagging
            git_ref: Git branch/tag/commit to build from
            git_url: Git repository URL
            jobs: Number of parallel build jobs
            tag_suffix: Additional suffix for the image tag

        Returns:
            Exit code (0 for success)
        """
        if git_ref is None:
            git_ref = f"llvmorg-{version}.1.2"

        tag = f"clang-ubuntu:{version}{tag_suffix}"
        log_file = self.root_dir / f"build-clang-{version}.log"

        build_args = {
            "LLVM_GIT_REF": git_ref,
            "LLVM_GIT_URL": git_url,
            "NUM_JOBS": str(jobs),
        }

        if self.dry_run:
            print(f"\n[DRY RUN] Would build Clang {version}")
            print(f"  Dockerfile: Dockerfile.clang.ubuntu")
            print(f"  Tag: {tag}")
            print(f"  Build args: {build_args}")
            print(f"  Log file: {log_file}")
            return 0

        try:
            stream = self.client.api.build(
                path=str(self.root_dir),
                dockerfile="Dockerfile.clang.ubuntu",
                tag=tag,
                buildargs=build_args,
                decode=True,
                rm=True,
            )

            self._stream_build_output(
                stream,
                f"Building Clang {version} from {git_ref}",
                log_file if not self.verbose else None
            )

            print(f"✅ Successfully built {tag}")
            return 0

        except BuildError as e:
            print(f"❌ Build failed: {e}", file=sys.stderr)
            return 1
        except APIError as e:
            print(f"❌ Docker API error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}", file=sys.stderr)
            return 1

    def build_devcontainer(
        self,
        clang_version: int,
        tag_suffix: str = "",
    ) -> int:
        """
        Build a devcontainer image with custom Clang.

        Args:
            clang_version: Clang version to use
            tag_suffix: Additional suffix for the image tag

        Returns:
            Exit code (0 for success)
        """
        clang_base_image = f"clang-ubuntu:{clang_version}{tag_suffix}"
        tag = f"devcontainer-clang:{clang_version}{tag_suffix}"

        # Check if base Clang image exists
        if not self._image_exists(clang_base_image):
            print(f"❌ Error: Base image {clang_base_image} not found. Build it first with:", file=sys.stderr)
            print(f"  ./build_containers.py clang --version {clang_version}", file=sys.stderr)
            return 1

        build_args = {
            "CLANG_BASE_IMAGE": clang_base_image,
        }

        if self.dry_run:
            print(f"\n[DRY RUN] Would build devcontainer with Clang {clang_version}")
            print(f"  Dockerfile: Dockerfile.devcontainer.clang")
            print(f"  Tag: {tag}")
            print(f"  Build args: {build_args}")
            return 0

        try:
            stream = self.client.api.build(
                path=str(self.root_dir),
                dockerfile="Dockerfile.devcontainer.clang",
                tag=tag,
                buildargs=build_args,
                decode=True,
                rm=True,
            )

            self._stream_build_output(
                stream,
                f"Building devcontainer with Clang {clang_version}",
                None  # Don't log devcontainer builds
            )

            print(f"✅ Successfully built {tag}")
            return 0

        except BuildError as e:
            print(f"❌ Build failed: {e}", file=sys.stderr)
            return 1
        except APIError as e:
            print(f"❌ Docker API error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}", file=sys.stderr)
            return 1

    def build_all(
        self,
        clang_version: int,
        git_ref: Optional[str] = None,
        jobs: int = 4,
    ) -> int:
        """
        Build both Clang and devcontainer images.

        Args:
            clang_version: Clang version to build
            git_ref: Git branch/tag/commit to build from
            jobs: Number of parallel build jobs

        Returns:
            Exit code (0 for success)
        """
        print(f"🔨 Building Clang {clang_version} and devcontainer...")

        # Build Clang first
        result = self.build_clang(clang_version, git_ref=git_ref, jobs=jobs)
        if result != 0:
            return result

        # Then build devcontainer
        result = self.build_devcontainer(clang_version)
        if result != 0:
            return result

        print(f"\n✅ Successfully built all containers for Clang {clang_version}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Build Docker containers for custom Clang compilers and devcontainers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Build target")

    # Clang subcommand
    clang_parser = subparsers.add_parser("clang", help="Build custom Clang compiler image")
    clang_parser.add_argument(
        "--version",
        type=int,
        required=True,
        help="Clang major version (e.g., 19, 20, 21)",
    )
    clang_parser.add_argument(
        "--git-ref",
        help="Git branch/tag/commit to build from (default: llvmorg-{version}.1.2)",
    )
    clang_parser.add_argument(
        "--git-url",
        default="https://github.com/llvm/llvm-project.git",
        help="Git repository URL for LLVM",
    )
    clang_parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel build jobs (default: 4)",
    )
    clang_parser.add_argument(
        "--tag-suffix",
        default="",
        help="Additional suffix for image tag",
    )

    # Devcontainer subcommand
    dev_parser = subparsers.add_parser("devcontainer", help="Build devcontainer image with custom Clang")
    dev_parser.add_argument(
        "--clang-version",
        type=int,
        required=True,
        help="Clang version to use (must be built first)",
    )
    dev_parser.add_argument(
        "--tag-suffix",
        default="",
        help="Additional suffix for image tag",
    )

    # All subcommand
    all_parser = subparsers.add_parser("all", help="Build both Clang and devcontainer")
    all_parser.add_argument(
        "--clang-version",
        type=int,
        required=True,
        help="Clang version to build",
    )
    all_parser.add_argument(
        "--git-ref",
        help="Git branch/tag/commit to build from (default: llvmorg-{version}.1.2)",
    )
    all_parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel build jobs (default: 4)",
    )

    # Global options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    builder = ContainerBuilder(dry_run=args.dry_run, verbose=args.verbose)

    try:
        if args.command == "clang":
            return builder.build_clang(
                version=args.version,
                git_ref=args.git_ref,
                git_url=args.git_url,
                jobs=args.jobs,
                tag_suffix=args.tag_suffix,
            )
        elif args.command == "devcontainer":
            return builder.build_devcontainer(
                clang_version=args.clang_version,
                tag_suffix=args.tag_suffix,
            )
        elif args.command == "all":
            return builder.build_all(
                clang_version=args.clang_version,
                git_ref=args.git_ref,
                jobs=args.jobs,
            )
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
