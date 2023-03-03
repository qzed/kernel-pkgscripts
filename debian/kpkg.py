#!/usr/bin/env python3

import os
import argparse
import multiprocessing
import subprocess
import shutil
import types
from pathlib import Path


DIR_BASE = Path(os.path.realpath(__file__)).parent
DIR_KERNEL_SOURCE = Path(os.path.realpath(os.getcwd()))


def package_make(spec):
    # disable automatic localversion by editing config
    subst = ';'.join([
        's|CONFIG_LOCALVERSION=.*|CONFIG_LOCALVERSION=\\"\\"|g',
        's|CONFIG_LOCALVERSION_AUTO=.*|CONFIG_LOCALVERSION_AUTO=n|g',
    ])
    proc = subprocess.run(["sed", "-i", subst, f"{spec.dir_kernel_src}/.config"])

    makeflags = ["-j{}".format(spec.nprocs)]

    # set up env
    env = dict(os.environ)
    env["LANGUAGE"] = "C"
    env["LANG"] = "C"
    env["EXTRAVERSION"] = ""
    env["LOCALVERSION"] = f"-{spec.kernel_version.suffix}"

    if spec.target:     # set target and toolchain-prefix for cross-compilation
        env["CROSS_COMPILE"] = f"{spec.target}-linux-gnu-"
        env["ARCH"] = {
            "aarch64": "arm64",
            "x86_64": "x86",
        }[spec.target]

    # get kernel package version string
    proc = subprocess.run(["make", "-s"] + makeflags + ["kernelrelease"], cwd=spec.dir_kernel_src,
                          env=env, capture_output=True)
    kernelrelease = str(proc.stdout, encoding='utf-8').strip()

    env["KDEB_PKGVERSION"] = f"{kernelrelease}-{spec.kernel_version.pkgrel}"

    proc = subprocess.Popen(["make"] + makeflags + [spec.make_target], cwd=spec.dir_kernel_src, env=env)
    proc.communicate()

    if not os.path.exists(spec.dir_base / "out"):
        os.mkdir(spec.dir_base / "out")

    for file in os.listdir(spec.dir_kernel_src.parent):
        if file.endswith(".deb") or file.endswith(".buildinfo") or file.endswith('.changes'):
            shutil.move(str(spec.dir_kernel_src.parent / file), str(spec.dir_base / "out" / file))


def cmd_package_clean(args):
    pass


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

    spec.target = args.target if args.target else None

    spec.make_target = args.maketarget

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
    parser = argparse.ArgumentParser(description='Debian kernel build helper.')
    subp = parser.add_subparsers(dest='command')

    p_build = subp.add_parser('build')
    p_build.add_argument('--suffix', '-s', type=str, default='surface')
    p_build.add_argument('--config', '-k', type=str, default='')
    p_build.add_argument('--clean', '-c', type=str, nargs='?', default='', const='clean')
    p_build.add_argument('--htmldocs', action='store_true')
    p_build.add_argument('--target', '-t', type=str, default='')
    p_build.add_argument('--maketarget', '-m', type=str, default='bindeb-pkg')
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
