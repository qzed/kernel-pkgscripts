NPROC=24

.phony: all

all:
	MAKEFLAGS="-j${NPROC}" makepkg -ef
	@rm linux.install.pkg
	@mkdir -p out && mv *.tar.xz out

clean-kbuild:
	@rm -f out/*.tar.xz
	@rm -f src/version

clean: clean-kbuild
	$(MAKE) -C src/linux clean

