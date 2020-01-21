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
DIR_KERNEL_SOURCE = DIR_BASE / "linux"


def package_make(spec):
    env = dict(os.environ)
    env["KBUILD_KERNELSRC"] = spec.dir_kernel_src
    env["KBUILD_SUFFIX"] = spec.kernel_version.suffix
    env["KBUILD_RELEASE"] = str(spec.kernel_version.pkgrel)
    env["KBUILD_CONFIG"] = os.path.realpath(spec.config) if spec.config else ''
    env["KBUILD_CLEAN"] = spec.clean
    env["KBUILD_HTMLDOCS"] = 'y' if spec.htmldocs else 'n'

    pkgflags = ["-fs"]
    if spec.signature.sign:
        pkgflags += ["--sign"]

    if spec.signature.key:
        pkgflags += ["--key", spec.signature.key]

    makeflags = "MAKEFLAGS=-j{}".format(spec.nprocs)

    proc = subprocess.Popen(["makepkg"] + pkgflags + [makeflags], cwd=spec.dir_base, env=env)
    proc.communicate()

    if not os.path.exists(spec.dir_base / "out"):
        os.mkdir(spec.dir_base / "out")

    for file in os.listdir(spec.dir_base):
        if file.endswith(".pkg.tar.xz") or file.endswith(".pkg.tar.zst"):
            shutil.move(str(spec.dir_base / file), str(spec.dir_base / "out" / file))

        if file.endswith(".sig"):
            shutil.move(str(spec.dir_base / file), str(spec.dir_base / "out" / file))

    if os.path.exists(spec.dir_base / "linux.install.pkg"):
        os.remove(spec.dir_base / "linux.install.pkg")


def cmd_package_clean(args):
    if os.path.exists(DIR_BASE / "pkg"):
        os.chmod(DIR_BASE / "pkg", stat.S_IWRITE | stat.S_IEXEC | stat.S_IREAD)

    shutil.rmtree(DIR_BASE / "src", True)
    shutil.rmtree(DIR_BASE / "pkg", True)

    for file in os.listdir(DIR_BASE):
        if file.endswith(".pkg.tar.xz"):
            os.remove(DIR_BASE / file)

        if file.endswith(".sig"):
            os.remove(DIR_BASE / file)

    if os.path.exists(DIR_BASE / "linux.install.pkg"):
        os.remove(DIR_BASE / "linux.install.pkg")


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
    spec.config = args.config
    spec.clean = args.clean
    spec.htmldocs = args.htmldocs

    spec.dir_kernel_src = DIR_KERNEL_SOURCE
    spec.dir_base = DIR_BASE

    spec.kernel_version = types.SimpleNamespace()
    spec.kernel_version.suffix = args.suffix
    spec.kernel_version.pkgrel = args.pkgrel

    spec.signature = types.SimpleNamespace()
    spec.signature.sign = args.sign
    spec.signature.key = args.key

    package_make(spec)


def main():
    parser = argparse.ArgumentParser(description='Arch-Linux kernel build helper.')
    subp = parser.add_subparsers(dest='command')

    p_build = subp.add_parser('build')
    p_build.add_argument('--suffix', '-s', type=str, default='')
    p_build.add_argument('--config', '-k', type=str, default='')
    p_build.add_argument('--clean', '-c', type=str, nargs='?', default='', const='clean')
    p_build.add_argument('--htmldocs', action='store_true')
    p_build.add_argument('--sign', action='store_true')
    p_build.add_argument('--key', type=str, default='')
    p_build.add_argument('--pkgrel', type=int, default=1)
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
