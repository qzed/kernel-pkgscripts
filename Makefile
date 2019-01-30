NPROC=24

.PHONY: all clean clean-kbuild

all:
	MAKEFLAGS="-j${NPROC}" makepkg -ef
	@rm linux.install.pkg
	@mkdir -p out && mv *.tar.xz out

clean-kbuild:
	@rm -rf pkg
	@rm -f out/*.tar.xz
	@rm -f src/version
	@rm -f src/linux/localversion.10-pkgrel
	@rm -f src/linux/localversion.20-pkgname

clean: clean-kbuild
	$(MAKE) -C src/linux clean

