# Arch Linux Kernel Build Files

Use at your own risk.

_Note: This is based on the official Arch Linux build files that can be obtained via ABS (as always consult [ArchWiki][1] for details)._

## Usage

### Before you build

- Clone/symlink/checkout your linux source files to `src/linux`.
  Apply patches/modifications if neccesary, the build process will not change these.

- Adapt the PKGBUILD to your liking, specifically you might want to adapt the first couple of lines, i.e. `_basever`, `_extraver`, `pkgrel`, and `pkgbase`
  (those are just for package naming and do not influence the build process at all).

- Adapt the numbers of cores you want to use (`NPROC`) in the Makefile.

### Building the Kernel

- Run `make`.
  The final packages should be in `out/` once it's finished.

[1]: https://wiki.archlinux.org/index.php/Kernel/Arch_Build_System
