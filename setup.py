
import os

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.develop import develop as _develop
from setuptools.command.install_lib import install_lib as _install_lib

PACKAGE_NAME = 'racmorph'
PACKAGE_VERSION = '0.1.0'
_PTH_NAME = 'racmorph.pth'
_SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
_PTH_SOURCE = os.path.join(_SETUP_DIR, _PTH_NAME)


def _copy_pth(cmd, dest_dir):
    """Copy racmorph.pth into dest_dir (must be site-packages / purelib)."""

    if not dest_dir:
        return
    if not os.path.isfile(_PTH_SOURCE):
        raise RuntimeError('missing %s' % _PTH_SOURCE)
    cmd.mkpath(dest_dir)
    cmd.copy_file(_PTH_SOURCE, os.path.join(dest_dir, _PTH_NAME))


class build_py(_build_py):
    """Put racmorph.pth in build/lib so wheels install it to site-packages.

    setup.cfg data_files with '.' installs to the venv prefix instead, and
    Python never auto-imports .pth files from there.
    """

    def run(self):
        super().run()
        if getattr(self, 'editable_mode', False):
            install = self.get_finalized_command('install')
            _copy_pth(self, install.install_lib)
            return
        _copy_pth(self, self.build_lib)


class install_lib(_install_lib):
    """Ensure racmorph.pth is in the install_lib dir (wheel purelib / site-packages)."""

    def run(self):
        super().run()
        _copy_pth(self, self.install_dir)


class develop(_develop):
    """Editable installs: copy .pth into site-packages, not the project tree."""

    def run(self):
        super().run()
        _copy_pth(self, self.install_dir)


setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    packages=[PACKAGE_NAME],
    install_requires=["tzdata"],
    include_package_data=False,
    cmdclass={
        'build_py': build_py,
        'install_lib': install_lib,
        'develop': develop,
    },
)
