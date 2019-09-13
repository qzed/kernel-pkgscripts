#!/usr/bin/env python3

import os
import stat
import argparse
import multiprocessing
import subprocess
import shutil
from pathlib import Path


DIR_BASE = Path(os.path.realpath(__file__)).parent
DIR_KERNEL_SOURCE = DIR_BASE / "linux"


def package_make(suffix, config, clean, htmldocs, cores):
    env = dict(os.environ)
    env["KBUILD_KERNELSRC"] = DIR_KERNEL_SOURCE
    env["KBUILD_SUFFIX"] = suffix
    env["KBUILD_CONFIG"] = os.path.realpath(config) if config else ''
    env["KBUILD_CLEAN"] = clean
    env["KBUILD_HTMLDOCS"] = 'y' if htmldocs else 'n'

    makeflags = "MAKEFLAGS=-j{}".format(cores)

    proc = subprocess.Popen(["makepkg", "-fs", makeflags], cwd=DIR_BASE, env=env)
    proc.communicate()

    if not os.path.exists(DIR_BASE / "out"):
        os.mkdir(DIR_BASE / "out")

    for file in os.listdir(DIR_BASE):
        if file.endswith(".pkg.tar.xz"):
            shutil.move(str(DIR_BASE / file), str(DIR_BASE / "out" / file))

    if os.path.exists(DIR_BASE / "linux.install.pkg"):
        os.remove(DIR_BASE / "linux.install.pkg")


def package_cmd_clean():
    if os.path.exists(DIR_BASE / "pkg"):
        os.chmod(DIR_BASE / "pkg", stat.S_IWRITE | stat.S_IEXEC | stat.S_IREAD)

    shutil.rmtree(DIR_BASE / "src", True)
    shutil.rmtree(DIR_BASE / "pkg", True)

    for file in os.listdir(DIR_BASE):
        if file.endswith(".pkg.tar.xz"):
            os.remove(DIR_BASE / file)

    if os.path.exists(DIR_BASE / "linux.install.pkg"):
        os.remove(DIR_BASE / "linux.install.pkg")


def package_cmd_clean_all():
    package_cmd_clean()
    shutil.rmtree(DIR_BASE / "out", True)


def package_cmd(subcommand):
    if subcommand == "clean":
        package_cmd_clean()
    elif subcommand == "clean-all":
        package_cmd_clean_all()


def kernel_make(options):
    proc = subprocess.Popen(["make", "-C", DIR_KERNEL_SOURCE] + options, cwd=DIR_BASE)
    proc.communicate()


def main():
    parser = argparse.ArgumentParser(description='Arch-Linux kernel build helper.')
    subp = parser.add_subparsers(dest='command')

    p_build = subp.add_parser('build')
    p_build.add_argument('--suffix', '-s', type=str, default='')
    p_build.add_argument('--config', '-k', type=str, default='')
    p_build.add_argument('--clean', '-c', type=str, nargs='?', default='', const='clean')
    p_build.add_argument('--htmldocs', action='store_true')
    p_build.add_argument('-j', type=int, default=multiprocessing.cpu_count())

    p_package = subp.add_parser('p')
    p_package_subp = p_package.add_subparsers(dest='subcommand')
    p_package_subp.add_parser('clean')
    p_package_subp.add_parser('clean-all')

    p_kernel = subp.add_parser('k')
    p_kernel.add_argument('options', nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "build":
        package_make(args.suffix, args.config, args.clean, args.htmldocs, args.j)
    elif args.command == "p":
        package_cmd(args.subcommand)
    elif args.command == "k":
        kernel_make(args.options)


if __name__ == '__main__':
    main()
