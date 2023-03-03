# Linux Kernel Packaging Helpers

Build distro-specific kernel packages from checked out (potentially dirty) and configured git kernel source tree.
Customized for my personal use-cases.


## Usage

Run the `<distro>/kpkg.py` scripts directly from the checked out tree.

For example, run
```sh
../kbuild/fedora/kpkg.py build -j 24 -s my-kernel
```
to build a kernel for Fedora with local-version suffix `-my-kernel` (specified by `-s`; the full version would be something like `6.2.1-1-my-kernel`) using 24 threads/processes (specified by `-j`).
The architecture will be the same as the host system.
Similarly, for Fedora, the distribution target (e.g. Fedora 37) will also be the same as the host system.

Note that invocation of the packaging scripts assumes that a suitable config has been generated for the target architecture and is available at `.config` in the kernel source tree.

Use `kpkg.py --help` to see all available options.


### Cross-compiling

Make sure to install the respective cross-compilation toolchain, e.g. `aarch64-linux-gnu-gcc` for `aarch64`.
You can specify the target architecture via the parameter `-t`.
For example, to compile an AArch64 (ARM64) kernel for Arch Linux, run
```sh
../kbuild/arch/kpkg.py build -j 24 -s my-kernel -t aarch64  
```
from inside the kernel tree.


### Building from Different Host-Distributions

You can use the provided Containerfiles with [toolbox](https://github.com/containers/toolbox) to compile packages for different distributions than the host distribution.
All required dependencies should already be included.

To set up a toolbox, build the container via (for example)
```sh
podman build -t archlinux-kernel-toolbox -f fedora/toolbox/Containerfile
```
and create the toolbox 
```sh
toolbox create --image localhost/archlinux-kernel-toolbox kbuild-archlinux
```

You can then enter the toolbox via
```sh
toolbox enter kbuild-archlinux
```
and run the Arch Linux packaging (`arch/kpkg.py`) script from there.


### SecureBoot Signing

For Fedora and Arch Linux, kernels can be automatically signed for secure boot with a machine owner key (MOK).
You can generate such a key pair by running the provided `keys/generate.sh` script.

To sign kernel images, use `--sbsign-key <key-file>` and `--sbsign-cert <crt-file>`.
For example, to build a signed kernel for Fedora, run
```sh
../kbuild/fedora/kpkg.py build -j 24 -s my-kernel \
    --sbsign-key ../kbuild/keys/mok.key \
    --sbsign-cert ../kbuild/keys/mok.crt
```

## Supported Use-Cases

Supported distributions:
- Arch Linux
- Fedora
- Debian (limited)

Supported architectures:
- `x86_64` (only tested by compiling natively on `x86`)
- `aarch64` (only tested by cross-compiling from `x86`)
