#!/usr/bin/env python3

import os
import pylxd
import fabric
import types
import argparse
import multiprocessing

from pathlib import Path
from termcolor import cprint


def get_container(client=pylxd.Client(), name='root'):
    return client.containers.get(name)


def get_container_ip(container, family='inet'):
    net = dict(container.state().network)
    del net['lo']

    for iface, iface_state in net.items():
        for addr in iface_state['addresses']:
            if addr['family'] == family and addr['scope'] == 'global':
                return addr['address']


def remote_override_conf(connection, dir_kernel_src):
    subst = ';'.join([
        's|CONFIG_LOCALVERSION=.*|CONFIG_LOCALVERSION=\\"\\"|g',
        's|CONFIG_LOCALVERSION_AUTO=.*|CONFIG_LOCALVERSION_AUTO=n|g',
    ])

    cmd = f'sed -i "{subst}" "{dir_kernel_src}/.config"'

    connection.run(cmd, hide=True)


def remote_get_nproc(connection):
    return int(connection.run('nproc', hide=True).stdout.strip())


def remote_get_kernelrelease(connection, spec):
    cmd = ' '.join([
        'make -s',
        f'-C {spec.dir_kernel_src}',
        f'-j{spec.nprocs}',
        f'LOCALVERSION="{spec.kernel_version.local}"',
        f'EXTRAVERSION="{spec.kernel_version.extra}"',
        'kernelrelease',
    ])

    return connection.run(cmd, hide=True).stdout.strip()


def remote_make_target(connection, target, spec):
    cmd = ' '.join([
        'make',
        f'-C {spec.dir_kernel_src}',
        f'-j{spec.nprocs}',
        f'LOCALVERSION="{spec.kernel_version.local}"',
        f'EXTRAVERSION="{spec.kernel_version.extra}"',
        f'{target}',
    ])

    connection.run(cmd, pty=True)


def remote_make_target_full(connection, target, spec):
    cmd = ' '.join([
        'make',
        f'-C {spec.dir_kernel_src}',
        f'-j{spec.nprocs}',
        f'LOCALVERSION="{spec.kernel_version.local}"',
        f'EXTRAVERSION="{spec.kernel_version.extra}"',
        f'KDEB_PKGVERSION="{spec.pkg.pkgversion}"',
        f'KDEB_SOURCENAME="{spec.pkg.sourcename}"',
        f'KDEB_CHANGELOG_DIST="{spec.pkg.changelog_dist}"',
        f'{target}',
    ])

    connection.run(cmd, pty=True)


def remote_xfer_packages(connection, dir_out, dir_kernel_src):
    dir_remote_out = Path(dir_kernel_src).parent

    cmd = ' '.join([
        f'cd {dir_remote_out}'
        '&&'
        'find .',
        '-maxdepth 1',
        '-type f \\( -name "*.deb" -o -name "*.changes" -o -name "*.buildinfo" \\)',
    ])

    # get the filenames of the produced files
    files = connection.run(cmd, hide=True)
    files = files.stdout.split()

    if files:
        Path(dir_out).mkdir(parents=True, exist_ok=True)

    # copy files back to host and delete on remote
    for f in files:
        print(f'  {Path(f)}')
        connection.get(dir_remote_out / f, local=dir_out / f)
        connection.run(f'rm -f \"{dir_remote_out / f}\"')


def makepkg(spec):
    # get and start container
    container = get_container(name=spec.container.name)
    container.start()

    # get container IP
    container_ip = get_container_ip(container)

    # connect and run build commands
    with fabric.Connection(host=container_ip, user=spec.container.user) as con:
        # get number of processors if not set
        if spec.nprocs is None:
            spec.nprocs = remote_get_nproc(con)

        # clean
        if spec.clean:
            cprint(f'Cleaning kernel source using {spec.clean}', 'white', attrs=['bold'])
            remote_make_target(con, spec.clean, spec)
            print()

        # set config
        if spec.config:
            cprint(f'Applying config file \'{spec.config}\'', 'white', attrs=['bold'])
            con.put(local=str(spec.config), remote=str(Path(spec.dir_kernel_src) / '.config'))
            print()

        # force configuration variables for version
        if spec.kernel_version.override:
            cprint(f'Forcing config options for version', 'white', attrs=['bold'])
            remote_override_conf(con, spec.dir_kernel_src)
            print()

        # configure
        cprint('Configuring...', 'white', attrs=['bold'])
        remote_make_target(con, 'oldconfig', spec)
        remote_make_target(con, 'prepare', spec)
        print()

        # compute package version if not specified
        if spec.pkg.pkgversion is None:
            cprint(f'Getting kernelrelease version', 'white', attrs=['bold'])
            krel = remote_get_kernelrelease(con, spec)
            print(f'  {krel}\n')

            spec.pkg.pkgversion = f'{krel}-{spec.pkg.pkgrel}'

        # build package
        cprint(f'Building kernel package in {Path(spec.dir_kernel_src)}', 'white', attrs=['bold'])
        remote_make_target_full(con, spec.target, spec)
        print()

        # move packages to host
        cprint('Moving package files back to host', 'white', attrs=['bold'])
        remote_xfer_packages(con, spec.dir_pkg_out, spec.dir_kernel_src)


def cmd_build(args):
    spec = types.SimpleNamespace()

    spec.target = args.target
    spec.nprocs = args.j

    spec.dir_kernel_src = 'devel/linux'
    spec.dir_pkg_out = Path(os.path.realpath(__file__)).parent / 'out'

    spec.config = args.config
    spec.clean = args.clean

    spec.kernel_version = types.SimpleNamespace()
    spec.kernel_version.override = True
    spec.kernel_version.local = f'-surface-{args.suffix}' if args.suffix else '-surface'
    spec.kernel_version.extra = ''

    spec.pkg = types.SimpleNamespace()
    spec.pkg.pkgversion = None
    spec.pkg.pkgrel = args.pkgrel
    spec.pkg.sourcename = 'linux-surface'
    spec.pkg.changelog_dist = 'unstable'

    spec.container = types.SimpleNamespace()
    spec.container.name = 'kdev-deb10'
    spec.container.user = 'build'

    makepkg(spec)


def main():
    parser = argparse.ArgumentParser(description='Debian kernel build helper')
    subp = parser.add_subparsers(dest='command')

    p_build = subp.add_parser('build')
    p_build.add_argument('--target', '-t', type=str, default='deb-pkg')
    p_build.add_argument('--suffix', '-s', type=str, default='')
    p_build.add_argument('--config', '-k', type=str, default='')
    p_build.add_argument('--clean', '-c', type=str, nargs='?', default='', const='clean')
    p_build.add_argument('--pkgrel', type=int, default=1)
    p_build.add_argument('-j', type=int, default=None)

    args = parser.parse_args()

    if args.command == 'build':
        cmd_build(args)


if __name__ == '__main__':
    main()
