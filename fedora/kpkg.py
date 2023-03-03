#!/usr/bin/env python3

import os
import stat
import argparse
import multiprocessing
import subprocess
import shutil
import types
from pathlib import Path


DIR_BASE = Path(os.path.realpath(__file__)).parent
DIR_KERNEL_SOURCE = os.path.realpath(os.getcwd())


def get_base_version(spec):
    version = None
    patchlevel = None
    sublevel = None

    with open(spec.dir_kernel_src / 'Makefile') as fd:
        for line in fd:
            line = line.strip()

            if line.startswith("VERSION"):
                version = line.split("=")[1].strip()
            elif line.startswith("PATCHLEVEL"):
                patchlevel = line.split("=")[1].strip()
            elif line.startswith("SUBLEVEL"):
                sublevel = line.split("=")[1].strip()

            if version is not None and patchlevel is not None and sublevel is not None:
                break

    return f"{version}.{patchlevel}.{sublevel}"


def package_make(spec):
    version = get_base_version(spec)

    dir_build = spec.dir_base / "build"
    dir_rpms = dir_build / "RPMS"
    dir_out = spec.dir_base / "out"

    env = dict(os.environ)
    env["LANGUAGE"] = "C"
    env["LANG"] = "C"
    env["RPM_BUILD_NCPUS"] = str(spec.nprocs)
    env["KBUILD_VERSION"] = version
    env["KBUILD_RELEASE"] = str(spec.kernel_version.pkgrel)
    env["KBUILD_SUFFIX"] = spec.kernel_version.suffix

    if spec.sb.key is not None:
        env["KBUILD_SB_KEY"] = str(spec.sb.key)

    if spec.sb.cert is not None:
        env["KBUILD_SB_CERT"] = str(spec.sb.cert)

    if spec.target:     # set toolchain for cross-compilation
        env["KBUILD_TOOLCHAIN"] = f"{spec.target}-linux-gnu-"

    rpmbuildargs = [
        "--define", f"_topdir {dir_build}",
        "--define", f"_specdir {spec.dir_base}",
        "--define", f"_builddir {spec.dir_kernel_src}",
    ]

    if spec.target:     # set target for cross compilation
        rpmbuildargs += ["--target", spec.target]

    proc = subprocess.Popen(["rpmbuild"] + rpmbuildargs + ["-ba", "kernel.spec"], cwd=spec.dir_base, env=env)
    proc.communicate()

    if not os.path.exists(spec.dir_base / "out"):
        os.mkdir(spec.dir_base / "out")

    for arch in os.listdir(dir_rpms):
        for file in os.listdir(dir_rpms / arch):
            if file.endswith(".rpm"):
                shutil.move(str(dir_rpms / arch / file), str(dir_out / file))


def cmd_package_clean(args):
    shutil.rmtree(DIR_BASE / "build", True)


def cmd_package_clean_all(args):
    cmd_package_clean()
    shutil.rmtree(DIR_BASE / "out", True)


def cmd_package(args):
    if args.subcommand == "clean":
        cmd_package_clean(args)
    elif args.subcommand == "clean-all":
        cmd_package_clean_all(args)


def cmd_kernel_make(args):
    proc = subprocess.Popen(["make", "-C", DIR_KERNEL_SOURCE] + args.options, cwd=DIR_BASE)
    proc.communicate()


def cmd_build(args):
    spec = types.SimpleNamespace()

    spec.nprocs = args.j
    spec.target = args.target if args.target else None

    spec.dir_kernel_src = Path(DIR_KERNEL_SOURCE)
    spec.dir_base = Path(DIR_BASE)

    spec.kernel_version = types.SimpleNamespace()
    spec.kernel_version.suffix = args.suffix
    spec.kernel_version.pkgrel = args.pkgrel

    spec.sb = types.SimpleNamespace()
    spec.sb.key = Path(args.sbsign_key).absolute() if args.sbsign_key is not None else None
    spec.sb.cert = Path(args.sbsign_cert).absolute() if args.sbsign_cert is not None else None

    package_make(spec)


def main():
    parser = argparse.ArgumentParser(description='Arch-Linux kernel build helper.')
    subp = parser.add_subparsers(dest='command')

    p_build = subp.add_parser('build')
    p_build.add_argument('--suffix', '-s', type=str, default='surface')
    p_build.add_argument('--target', '-t', type=str, default='')
    p_build.add_argument('--pkgrel', type=int, default=1)
    p_build.add_argument('--sbsign-key', type=str)
    p_build.add_argument('--sbsign-cert', type=str)
    p_build.add_argument('-j', type=int, default=multiprocessing.cpu_count())

    p_package = subp.add_parser('p')
    p_package_subp = p_package.add_subparsers(dest='subcommand')
    p_package_subp.add_parser('clean')
    p_package_subp.add_parser('clean-all')

    p_kernel = subp.add_parser('k')
    p_kernel.add_argument('options', nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "p":
        cmd_package(args)
    elif args.command == "k":
        cmd_kernel_make(args)


if __name__ == '__main__':
    main()
