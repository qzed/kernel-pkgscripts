# Input/configuration environtment variables:
#   - KBUILD_VERSION        set package version base tag
#   - KBUILD_RELEASE        override pkgrel (default: 1)
#   - KBUILD_SUFFIX         set package and kernel suffix, e.g. 'lts'
#   - KBUILD_TOOLCHAIN      toolchain prefix for cross compilation (optional)
#   - KBUILD_SB_KEY         SecureBoot key for signing
#   - KBUILD_SB_CERT        SecureBoot cert (.crt) for signing
#
# Based on https://github.com/linux-surface/linux-surface/blob/master/pkg/fedora/kernel-surface/kernel-surface.spec#L178

%global kernel_version %{getenv:KBUILD_VERSION}
%global kernel_release %{getenv:KBUILD_RELEASE}
%global kernel_suffix %{getenv:KBUILD_SUFFIX}
%global kernel_toolchain %{getenv:KBUILD_TOOLCHAIN}
%global kernel_sb_key %{getenv:KBUILD_SB_KEY}
%global kernel_sb_cert %{getenv:KBUILD_SB_CERT}

%global fedora_title %{kernel_version}-%{kernel_suffix} (Custom)

%global kernel_suffix_esc %(echo %{kernel_suffix} | sed 's/-/_/g')

%global kernel_localversion %{kernel_release}.%{kernel_suffix_esc}%{?dist}.%{_target_cpu}
%global kernel_config kernel-%{kernel_version}-%{_target_cpu}.config
%global kernel_name %{kernel_version}-%{kernel_localversion}

%global kernel_modpath %{buildroot}/lib/modules/%{kernel_name}


Name:       kernel-%{kernel_suffix}
Summary:    The Linux Kernel - custom edition
Version:    %{kernel_version}
Release:    %{kernel_release}%{?dist}
License:    GPLv2

AutoReqProv: no

Provides: installonlypkg(kernel-%{kernel_suffix})
Provides: kernel-uname-r = %{kernel_name}
Provides: kernel-core-uname-r = %{kernel_name}
Provides: kernel-modules-uname-r = %{kernel_name}

Requires(pre): coreutils, systemd >= 203-2, /usr/bin/kernel-install
Requires(pre): dracut >= 027
Requires(pre): linux-firmware >= 20150904-56.git6ebf5d57
Requires(preun): systemd >= 200

BuildRequires: openssl openssl-devel
BuildRequires: kmod, patch, bash, tar, git-core, sbsigntools
BuildRequires: bzip2, xz, findutils, gzip, m4, perl-interpreter,
BuildRequires: perl-Carp, perl-devel, perl-generators, make, diffutils,
BuildRequires: gawk, gcc, binutils, redhat-rpm-config, hmaccalc, bison
BuildRequires: flex, net-tools, hostname, bc, elfutils-devel
BuildRequires: gcc-plugin-devel dwarves

# Used to mangle unversioned shebangs to be Python 3
BuildRequires: python3-devel

Conflicts: xfsprogs < 4.3.0-1
Conflicts: xorg-x11-drv-vmmouse < 13.0.99
BuildConflicts: rhbuildsys(DiskFree) < 500Mb
BuildConflicts: rpm < 4.13.0.1-19
BuildConflicts: dwarves < 1.13

ExclusiveArch: x86_64 aarch64

%global debug_package %{nil}
%global _build_id_links alldebug

%description
The Linux Kernel, the operating system core itself, custom edition.

%package devel
Summary: Development package for building kernel modules for kernel-%{kernel_suffix}
AutoReqProv: no
Provides: installonlypkg(kernel-%{kernel_suffix})
Provides: kernel-devel-uname-r = %{kernel_name}

%description devel
This package provides kernel headers and makefiles sufficient to build modules
against the kernel-%{kernel_suffix} package.


%if "%{kernel_toolchain}"
%global mkopt_toolchain "CROSS_COMPILE=%{kernel_toolchain}"
%endif

%define asmarch %{_target_cpu}
%define hdrarch %{_target_cpu}
%define kernel_arch %{_target_cpu}

%ifarch x86_64
%define asmarch x86
%define hdrarch x86
%define kernel_arch x86
%endif

%ifarch aarch64
%define asmarch arm64
%define hdrarch arm64
%define kernel_arch arm64
%endif

%define kmake() { \
    make %{?_smp_mflags} \
    LOCALVERSION=-%{kernel_localversion} \
    EXTRAVERSION="" \
    KBUILD_BUILD_VERSION=%{kernel_release} \
    ARCH=%{kernel_arch} \
    %{?mkopt_toolchain} \
    %* \
}


%prep

# This Prevents scripts/setlocalversion from mucking with our version numbers.
touch .scmversion

# Override localversion in .config
sed -i "s|CONFIG_LOCALVERSION=.*|CONFIG_LOCALVERSION=\"\"|g" ".config"
sed -i "s|CONFIG_LOCALVERSION_AUTO=.*|CONFIG_LOCALVERSION_AUTO=n|g" ".config"

# This ensures build-ids are unique to allow parallel debuginfo
sed -i "s|CONFIG_BUILD_SALT=.*|CONFIG_BUILD_SALT=\"%{kernel_name}\"|g" ".config"

# Configure kernel
%{kmake} oldconfig
%{kmake} prepare


%build

# Build the kernel
%{kmake} all

# Disable stripping (doesn't seem to work for cross-compilation and also
# removes module signatures...)
%define __os_install_post \
  /usr/lib/rpm/brp-compress\
%{nil}


%install
mkdir -p %{buildroot}/boot
mkdir -p %{kernel_modpath}

# Install devicetrees
%ifarch %{arm} aarch64
    %{kmake} dtbs_install INSTALL_DTBS_PATH=%{buildroot}/boot/dtb-%{kernel_name}
    cp -r %{buildroot}/boot/dtb-%{kernel_name} %{kernel_modpath}/dtb
%endif

# Install modules
%{kmake} INSTALL_MOD_PATH=%{buildroot} modules_install KERNELRELEASE=%{kernel_name}

# Install vmlinuz
image_name=$(%{kmake} -s image_name)

if [ ! -z "%{kernel_sb_key}" ] && [ ! -z "%{kernel_sb_cert}" ]; then
    sbsign --key "%{kernel_sb_key}" --cert "%{kernel_sb_cert}" --output "${image_name}" "${image_name}"
fi

install -m 755 "${image_name}" "%{buildroot}/boot/vmlinuz-%{kernel_name}"
install -m 755 "${image_name}" "%{kernel_modpath}/vmlinuz"

# Install System.map and .config
install -m 644 System.map %{kernel_modpath}/System.map
install -m 644 System.map %{buildroot}/boot/System.map-%{kernel_name}
install -m 644 .config %{kernel_modpath}/config
install -m 644 .config %{buildroot}/boot/config-%{kernel_name}

# hmac sign the kernel for FIPS
sha512hmac %{buildroot}/boot/vmlinuz-%{kernel_name} | sed -e "s,%{buildroot},," > %{kernel_modpath}/.vmlinuz.hmac
cp %{kernel_modpath}/.vmlinuz.hmac %{buildroot}/boot/.vmlinuz-%{kernel_name}.hmac

# mark modules executable so that strip-to-file can strip them
find %{kernel_modpath} -name "*.ko" -type f | xargs --no-run-if-empty chmod u+x

# Setup directories for -devel files
rm -f %{kernel_modpath}/build
rm -f %{kernel_modpath}/source
mkdir -p %{kernel_modpath}/build
pushd %{kernel_modpath}
    ln -s build source
popd

# first copy everything
cp --parents $(find  -type f -name "Makefile*" -o -name "Kconfig*") %{kernel_modpath}/build
cp Module.symvers %{kernel_modpath}/build
cp System.map %{kernel_modpath}/build
if [ -s Module.markers ]; then
	cp Module.markers %{kernel_modpath}/build
fi

# then drop all but the needed Makefiles/Kconfig files
rm -rf %{kernel_modpath}/build/scripts
rm -rf %{kernel_modpath}/build/include
cp .config %{kernel_modpath}/build
cp -a scripts %{kernel_modpath}/build
rm -rf %{kernel_modpath}/build/scripts/tracing
rm -f %{kernel_modpath}/build/scripts/spdxcheck.py

if [ -f tools/objtool/objtool ]; then
    cp -a tools/objtool/objtool %{kernel_modpath}/build/tools/objtool/ || :

    # these are a few files associated with objtool
    cp -a --parents tools/build/Build.include %{kernel_modpath}/build/
    cp -a --parents tools/build/Build %{kernel_modpath}/build/
    cp -a --parents tools/build/fixdep.c %{kernel_modpath}/build/
    cp -a --parents tools/scripts/utilities.mak %{kernel_modpath}/build/

    # also more than necessary but it's not that many more files
    cp -a --parents tools/objtool/* %{kernel_modpath}/build/
    cp -a --parents tools/lib/str_error_r.c %{kernel_modpath}/build/
    cp -a --parents tools/lib/string.c %{kernel_modpath}/build/
    cp -a --parents tools/lib/subcmd/* %{kernel_modpath}/build/
fi


if [ -d arch/%{hdrarch}/scripts ]; then
    cp -a arch/%{hdrarch}/scripts %{kernel_modpath}/build/arch/x86/ || :
fi

if [ -f arch/%{hdrarch}/*lds ]; then
    cp -a arch/%{hdrarch}/*lds %{kernel_modpath}/build/arch/x86/ || :
fi

if [ -f arch/%{asmarch}/kernel/module.lds ]; then
    cp -a --parents arch/%{asmarch}/kernel/module.lds %{kernel_modpath}/build/
fi

rm -f %{kernel_modpath}/build/scripts/*.o
rm -f %{kernel_modpath}/build/scripts/*/*.o

if [ -d arch/%{asmarch}/include ]; then
    cp -a --parents arch/%{asmarch}/include %{kernel_modpath}/build/
fi

%ifarch aarch64
    # arch/arm64/include/asm/xen references arch/arm
    cp -a --parents arch/arm/include/asm/xen %{kernel_modpath}/build/
    # arch/arm64/include/asm/opcodes.h references arch/arm
    cp -a --parents arch/arm/include/asm/opcodes.h %{kernel_modpath}/build/
%endif
    # include the machine specific headers for ARM variants, if available.
%ifarch %{arm}
    # include a few files for 'make prepare'
    cp -a --parents arch/arm/tools/gen-mach-types %{kernel_modpath}/build/
    cp -a --parents arch/arm/tools/mach-types %{kernel_modpath}/build/
%endif

cp -a include %{kernel_modpath}/build/include

%ifarch i686 x86_64
    # files for 'make prepare' to succeed with kernel-devel
    cp -a --parents arch/x86/entry/syscalls/syscall_32.tbl %{kernel_modpath}/build/
    cp -a --parents arch/x86/entry/syscalls/syscall_64.tbl %{kernel_modpath}/build/
    cp -a --parents arch/x86/tools/relocs_32.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/tools/relocs_64.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/tools/relocs.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/tools/relocs_common.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/tools/relocs.h %{kernel_modpath}/build/

    cp -a --parents scripts/syscalltbl.sh %{kernel_modpath}/build/
    cp -a --parents scripts/syscallhdr.sh %{kernel_modpath}/build/

    # Yes this is more includes than we probably need. Feel free to sort out
    # dependencies if you so choose.
    cp -a --parents tools/include/* %{kernel_modpath}/build/
    cp -a --parents arch/x86/purgatory/purgatory.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/purgatory/stack.S %{kernel_modpath}/build/
    cp -a --parents arch/x86/purgatory/setup-x86_64.S %{kernel_modpath}/build/
    cp -a --parents arch/x86/purgatory/entry64.S %{kernel_modpath}/build/
    cp -a --parents arch/x86/boot/string.h %{kernel_modpath}/build/
    cp -a --parents arch/x86/boot/string.c %{kernel_modpath}/build/
    cp -a --parents arch/x86/boot/ctype.h %{kernel_modpath}/build/
%endif


# Make sure the Makefile, version.h, and auto.conf have a matching
# timestamp so that external modules can be built

touch -r %{kernel_modpath}/build/Makefile \
    %{kernel_modpath}/build/include/generated/uapi/linux/version.h \
    %{kernel_modpath}/build/include/config/auto.conf

mkdir -p %{buildroot}/usr/src/kernels
mv %{kernel_modpath}/build %{buildroot}/usr/src/kernels/%{kernel_name}

# This is going to create a broken link during the build, but we don't use
# it after this point.  We need the link to actually point to something
# when kernel-devel is installed, and a relative link doesn't work across
# the F17 UsrMove feature.
ln -sf /usr/src/kernels/%{kernel_name} %{kernel_modpath}/build

# prune junk from kernel-devel
find %{buildroot}/usr/src/kernels -name ".*.cmd" -delete

# remove files that will be auto generated by depmod at rpm -i time
pushd %{kernel_modpath}
	rm -f modules.{alias*,builtin.bin,dep*,*map,symbols*,devname,softdep}
popd

# build a BLS config for this kernel
cat >%{kernel_modpath}/bls.conf <<EOF
title Fedora (%{kernel_name}) %{fedora_title}
version %{kernel_name}
linux /vmlinuz-%{kernel_name}
initrd /initramfs-%{kernel_name}.img
options \$kernelopts
grub_users \$grub_users
grub_arg --unrestricted
grub_class kernel
EOF

# Mangle /usr/bin/python shebangs to /usr/bin/python3
# Mangle all Python shebangs to be Python 3 explicitly
# -p preserves timestamps
# -n prevents creating ~backup files
# -i specifies the interpreter for the shebang
# This fixes errors such as
# *** ERROR: ambiguous python shebang in /usr/bin/kvm_stat: #!/usr/bin/python. Change it to python3 (or python2) explicitly.
# We patch all sources below for which we got a report/error.
%py3_shebang_fix %{buildroot}/usr/src/kernels/%{kernel_name}/scripts/show_delta


%clean
rm -rf %{buildroot}

%posttrans
/bin/kernel-install add %{kernel_name} /lib/modules/%{kernel_name}/vmlinuz || exit $?

%preun
/bin/kernel-install remove %{kernel_name} /lib/modules/%{kernel_name}/vmlinuz || exit $?

%files
%defattr (-, root, root)
/lib/modules/%{kernel_name}
%ghost /boot/vmlinuz-%{kernel_name}
%ghost /boot/config-%{kernel_name}
%ghost /boot/System.map-%{kernel_name}
%ghost /boot/.vmlinuz-%{kernel_name}.hmac
	
%ifarch %{arm} aarch64
%ghost /boot/dtb-%{kernel_name}
%endif

%files devel
%defattr (-, root, root)
/usr/src/kernels/%{kernel_name}


%changelog
* Thu Mar 02 2023 Maximilian Luz <m@mxnluz.io>
- Initial version
