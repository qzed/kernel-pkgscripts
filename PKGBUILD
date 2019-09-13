# Arch-Linux Surface Kernel Build Script
#
# Input/configuration environtment variables:
#   - KBUILD_KERNELSRC      override kernel source directory (default: $PWD/src/linux)
#   - KBUILD_SUFFIX         set package and kernel suffix, e.g. 'lts' (default: '')
#   - KBUILD_RELEASE        override pkgrel (default: 1)
#   - KBUILD_HTMLDOCS       build htmldocs (default: n)
#   - KBUILD_AUTOVER        use kernel versioning as configured in .config (default: n)
#   - KBUILD_CONFIG         apply specified config file
#   - KBUILD_CLEAN          optionally clean with specified target before building
#   - KBUILD_EXTRAVERSION   override kernel EXTRAVERSION
#   - KBUILD_LOCALVERSION   override kernel LOCALVERSION
#


# names, versions, etc.
_ksrc=${KBUILD_KERNELSRC:-"${PWD}/linux"}
_ktag=$(cd ${_ksrc} && git describe --long --tags | sed 's/^v//;s/-.*//')
_ksfx=$(echo ${KBUILD_SUFFIX} | sed -E 's/(.+)/-\1/')
_krel=${KBUILD_RELEASE:-1}
_kpkg="linux-surface${_ksfx}"
_kname="${_kpkg#linux}"

_kextraversion="${KBUILD_EXTRAVERSION:--${_krel}}"
_klocalversion="${KBUILD_LOCALVERSION:-${_kname}}"

_khtmldocs="${KBUILD_HTMLDOCS:-n}"

_kautover=${KBUILD_AUTOVER:-n}
if test "${_kautover}" = "y"; then
    _makevers=()
else
    _makevers=(
        "EXTRAVERSION=${_kextraversion}"
        "LOCALVERSION=${_klocalversion}"
    )
fi


# basic package config
pkgbase="${_kpkg}"
pkgver="${_ktag}"
pkgrel="${_krel}"
arch=('x86_64')
license=('GPL2')
options=('!strip')

makedepends=(
  'xmlto' 'kmod' 'inetutils' 'bc' 'libelf' 'git' 'python-sphinx'
  'python-sphinx_rtd_theme' 'graphviz' 'imagemagick'
)

source=(
    '60-linux.hook'
    '90-linux.hook'
    'linux.preset'
)

sha256sums=(
    'ae2e95db94ef7176207c690224169594d49445e04249d2499e9d2fbc117a0b21'
    '75f99f5239e03238f88d1a834c50043ec32b1dc568f2cc291b07d04718483919'
    'ad6344badc91ad0630caacde83f7f9b97276f80d26a20619a87952be65492c65'
)

prepare() {
    if test ! -z "${KBUILD_CLEAN}"; then
        msg2 "Cleaning kernel source using ${KBUILD_CLEAN}"
        make -C "${_ksrc}" "${_makevers[@]}" ${KBUILD_CLEAN}
    fi

    if test ! -z "${KBUILD_CONFIG}"; then
        msg2 "Applying config file '${KBUILD_CONFIG}'"
        cp "${KBUILD_CONFIG}" "${_ksrc}/.config"
    fi

    if test "${_kautover}" != "y"; then
        msg2 "Overriding version in .config..."
        sed -i "s|CONFIG_LOCALVERSION=.*|CONFIG_LOCALVERSION=\"\"|g" "${_ksrc}/.config"
        sed -i "s|CONFIG_LOCALVERSION_AUTO=.*|CONFIG_LOCALVERSION_AUTO=n|g" "${_ksrc}/.config"
    fi

    msg2 "Configuring..."
    make -C "${_ksrc}" "${_makevers[@]}" -s oldconfig
    make -C "${_ksrc}" "${_makevers[@]}" -s prepare

    msg2 "Generating kernel version..."
    export _kver=$(make -C "${_ksrc}" "${_makevers[@]}" -s kernelrelease)
}

build() {
    msg2 "Building ${_kpkg} kernel version ${_kver}..."

    targets=(bzImage modules)
    if test "${_khtmldocs}" = "y"; then
        targets+=(htmldocs)
    fi

    make -C "${_ksrc}" "${_makevers[@]}" ${targets[@]}
}

_package() {
    pkgdesc="The ${pkgbase/linux/Linux} kernel and modules"
    depends=('coreutils' 'linux-firmware' 'kmod' 'mkinitcpio>=0.7')
    optdepends=('crda: to set the correct wireless channels of your country')
    backup=("etc/mkinitcpio.d/${pkgbase}.preset")
    install="linux.install"

    local modulesdir="${pkgdir}/usr/lib/modules/${_kver}"

    msg2 "Installing boot image..."
    # systemd expects to find the kernel here to allow hibernation
    # https://github.com/systemd/systemd/commit/edda44605f06a41fb86b7ab8128dcf99161d2344
    install -Dm644 "${_ksrc}/$(make -C "${_ksrc}" "${_makevers[@]}" -s image_name)" "${modulesdir}/vmlinuz"
    install -Dm644 "${modulesdir}/vmlinuz" "${pkgdir}/boot/vmlinuz-${pkgbase}"

    msg2 "Installing modules..."
    make -C "${_ksrc}" "${_makevers[@]}" INSTALL_MOD_PATH="${pkgdir}/usr" modules_install

    # a place for external modules,
    # with version file for building modules and running depmod from hook
    local extramodules="extramodules${_kname}"
    local extradir="${pkgdir}/usr/lib/modules/${extramodules}"
    echo "${_kver}" | install -Dm644 /dev/null "${extradir}/version"
    ln -sr "${extradir}" "${modulesdir}/extramodules"

    # remove build and source links
    rm "${modulesdir}"/{source,build}

    msg2 "Installing hooks..."
    # sed expression for following substitutions
    local subst="
      s|%PKGBASE%|${pkgbase}|g
      s|%KERNVER%|${kernver}|g
      s|%EXTRAMODULES%|${extramodules}|g
    "

    # hack to allow specifying an initially nonexisting install file
    sed "${subst}" "${startdir}/${install}" > "${startdir}/${install}.pkg"
    true && install=${install}.pkg

    # fill in mkinitcpio preset and pacman hooks
    sed "${subst}" "linux.preset" | install -Dm644 /dev/stdin \
        "${pkgdir}/etc/mkinitcpio.d/${pkgbase}.preset"
    sed "${subst}" "60-linux.hook" | install -Dm644 /dev/stdin \
        "${pkgdir}/usr/share/libalpm/hooks/60-${pkgbase}.hook"
    sed "${subst}" "90-linux.hook" | install -Dm644 /dev/stdin \
        "${pkgdir}/usr/share/libalpm/hooks/90-${pkgbase}.hook"

    msg2 "Fixing permissions..."
    chmod -Rc u=rwX,go=rX "$pkgdir"
}

_package-headers() {
    pkgdesc="Header files and scripts for building modules for ${pkgbase/linux/Linux} kernel"

    local builddir="${pkgdir}/usr/lib/modules/${_kver}/build"

    cd "${_ksrc}"

    msg2 "Installing build files..."
    install -Dt "$builddir" -m644 Makefile .config Module.symvers System.map vmlinux
    install -Dt "$builddir/kernel" -m644 kernel/Makefile
    install -Dt "$builddir/arch/x86" -m644 arch/x86/Makefile
    cp -t "$builddir" -a scripts

    # add objtool for external module building and enabled VALIDATION_STACK option
    install -Dt "$builddir/tools/objtool" tools/objtool/objtool

    # add xfs and shmem for aufs building
    mkdir -p "$builddir"/{fs/xfs,mm}

    # ???
    mkdir "$builddir/.tmp_versions"

    msg2 "Installing headers..."
    cp -t "$builddir" -a include
    cp -t "$builddir/arch/x86" -a arch/x86/include
    install -Dt "$builddir/arch/x86/kernel" -m644 arch/x86/kernel/asm-offsets.s

    install -Dt "$builddir/drivers/md" -m644 drivers/md/*.h
    install -Dt "$builddir/net/mac80211" -m644 net/mac80211/*.h

    # http://bugs.archlinux.org/task/13146
    install -Dt "$builddir/drivers/media/i2c" -m644 drivers/media/i2c/msp3400-driver.h

    # http://bugs.archlinux.org/task/20402
    install -Dt "$builddir/drivers/media/usb/dvb-usb" -m644 drivers/media/usb/dvb-usb/*.h
    install -Dt "$builddir/drivers/media/dvb-frontends" -m644 drivers/media/dvb-frontends/*.h
    install -Dt "$builddir/drivers/media/tuners" -m644 drivers/media/tuners/*.h

    msg2 "Installing KConfig files..."
    find . -name 'Kconfig*' -exec install -Dm644 {} "$builddir/{}" \;

    msg2 "Removing unneeded architectures..."
    local arch
    for arch in "$builddir"/arch/*/; do
        [[ $arch = */x86/ ]] && continue
        echo "Removing $(basename "$arch")"
        rm -r "$arch"
    done

    msg2 "Removing documentation..."
    rm -r "$builddir/Documentation"

    msg2 "Removing broken symlinks..."
    find -L "$builddir" -type l -printf 'Removing %P\n' -delete

    msg2 "Removing loose objects..."
    find "$builddir" -type f -name '*.o' -printf 'Removing %P\n' -delete

    msg2 "Stripping build tools..."
    local file
    while read -rd '' file; do
        case "$(file -bi "$file")" in
            application/x-sharedlib\;*)      # Libraries (.so)
                strip -v $STRIP_SHARED "$file" ;;
            application/x-archive\;*)        # Libraries (.a)
                strip -v $STRIP_STATIC "$file" ;;
            application/x-executable\;*)     # Binaries
                strip -v $STRIP_BINARIES "$file" ;;
            application/x-pie-executable\;*) # Relocatable binaries
                strip -v $STRIP_SHARED "$file" ;;
        esac
    done < <(find "$builddir" -type f -perm -u+x ! -name vmlinux -print0)

    msg2 "Adding symlink..."
    mkdir -p "$pkgdir/usr/src"
    ln -sr "$builddir" "$pkgdir/usr/src/$pkgbase-$pkgver"

    msg2 "Fixing permissions..."
    chmod -Rc u=rwX,go=rX "$pkgdir"
}

_package-docs() {
    pkgdesc="Kernel hackers manual - HTML documentation that comes with the ${pkgbase/linux/Linux} kernel"

    local builddir="${pkgdir}/usr/lib/modules/${_kver}/build"

    msg2 "Installing documentation..."
    mkdir -p "${builddir}"
    cp -t "${builddir}" -a "${_ksrc}/Documentation"

    msg2 "Removing doctrees..."
    rm -r "${builddir}/Documentation/output/.doctrees"

    if test "${_khtmldocs}" = "y"; then
        msg2 "Moving HTML docs..."
        local src dst
        while read -rd '' src; do
          dst="${builddir}/Documentation/${src#$builddir/Documentation/output/}"
          mkdir -p "${dst%/*}"
          mv "$src" "$dst"
          rmdir -p --ignore-fail-on-non-empty "${src%/*}"
        done < <(find "${builddir}/Documentation/output" -type f -print0)
    else
        # remove HTML-docs in case of dirty build
        rm -rf "${builddir}/Documentation/output"
        rm -rf "${builddir}/Documentation/_images"
    fi

    msg2 "Adding symlink..."
    mkdir -p "${pkgdir}/usr/share/doc"
    ln -sr "${builddir}/Documentation" "${pkgdir}/usr/share/doc/${pkgbase}"

    msg2 "Fixing permissions..."
    chmod -Rc u=rwX,go=rX "${pkgdir}"
}


# dynamically define package functions
pkgname=("${pkgbase}" "${pkgbase}-headers" "${pkgbase}-docs")
for _p in ${pkgname[@]}; do
    eval "package_${_p}() {
        $(declare -f "_package${_p#${pkgbase}}")
        _package${_p#${pkgbase}}
    }"
done
