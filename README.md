# Arch Linux Kernel Build Files

Use at your own risk.

_Note: This is based on the official Arch Linux build files that can be obtained via ABS (as always consult [ArchWiki][1] for details)._

## Usage

### Before you build

- Clone/symlink/checkout your linux source files to `./linux`. Apply
  patches/modifications if neccesary, the build process will not change these.

- Configure the PKGBUILD via environment variables. Have a look at the
  PKGBUILD for details.

### Building the Kernel

Run `./kpkg.py build` to build a package. The final packages should be
in `out/` once it's finished.

You can specify some options via the `kpkg.py` helper, for example the
version suffix, e.g. `-lts` by specifying `kpkg.py build -s lts`. You can
specify the number of cores to use e.g. via `-j8`.

[1]: https://wiki.archlinux.org/index.php/Kernel/Arch_Build_System
