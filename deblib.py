#!/usr/bin/env python3
"""
deb-buildscripts main python library

Contains basic functionality to build deb packages from scratch
"""
import subprocess
import shutil
import os
from collections import defaultdict

class PackagingError(Exception):
    pass

name = ""
version = None
debversion = None
homepage = None
build_depends = []

# Key (suffix to override_dh_auto_) ; value: list of make commands
build_config = defaultdict(list)

def get_name():
    global name
    if name == None:
        raise PackagingError("No name set (set_name())")
    return name

def set_name(arg):
    global name
    name = arg

def get_version():
    global version
    if version == None:
        raise PackagingError("No version set (set_version())")
    return version

def get_debversion():
    global debversion
    if debversion == None:
        raise ValueError("No debversion set (set_debversion())")
    return debversion

def set_version(arg, gitcount=False):
    global version
    version = arg
    if gitcount:
        gitrev = cmd_output("git rev-list --all | wc -l".format(get_name()))
        version += "-{}".format(gitrev.strip())

def set_debversion(arg):
    global debversion
    debversion = "{}-{}".format(get_version(), arg)

def cmd(arg, cwd=True):
    if cwd:
        arg = "cd {} && {}".format(get_name(), arg)
    subprocess.run(arg, shell=True)

def cmd_output(arg, cwd=True):
    if cwd:
        arg = "cd {} && {}".format(get_name(), arg)
    return subprocess.check_output(arg, shell=True)

def git_clone(url):
    subprocess.run(["git", "clone", url, get_name()])

def pack_source():
    # Remove .git
    shutil.rmtree(os.path.join(get_name(), ".git"), ignore_errors=True)
    shutil.rmtree(os.path.join(get_name(), "debian"), ignore_errors=True)
    # Pack source archive
    subprocess.run("tar cJvf {}_{}.orig.tar.xz {}".format(get_name(), get_version(), get_name()))

def debian_dirpath():
    return os.path.join(get_name(), "debian")

def create_debian_dir():
    os.path.makedirs(debian_dirpath())

def copy_license():
    dst = os.path.join(debian_dirpath(), "copyright")
    for filename in ["COPYING", "LICENSE"]:
        fn = os.path.join(get_name(), filename)
        if os.path.isfile(fn):
            shutil.copy(filename, dst)
            return
    raise PackagingError("Can't find license file!")

def create_debian():
    "Create the debian directory. Call this AFTER setting all config options"

def create_dummy_changelog():
    arg = "DEBEMAIL=ukoehler@techoverflow.net dch --create -v {} --package {} \"\" && dch -r \"\""
    cmd(arg.formt(get_debversion(), get_name()))

def intitialize_control():
    with open(control_filepath(), "w") as outfile:
        print("Source: {}".format(get_name()), file=outfile)
        print("Maintainer: None <none@example.com>", file=outfile)
        print("Section: misc", file=outfile)
        print("Priority: optional", file=outfile)
        print("Standards-Version: 3.9.2", file=outfile)
        print("Build-Depends: {}".format(" ,".join(
            ["debhelper (>= 8)"] + build_depends)), file=outfile)

def get_dpkg_architecture():
    """
    Get the dpkg architecture, e.g. amd64
    """
    arch = cmd_output("dpkg-architecture | grep DEB_BUILD_ARCH=", cwd=False)
    arch = arch.decode("utf-8").strip().rpartition("=")[2]
    return arch

def control_filepath():
    return os.path.join(debian_dirpath(), "control")

def control_add_package(suffix=None, depends=[], arch_specific=True, description=None):
    global homepage
    package_name = get_name()
    if suffix:
        package_name += "-" + suffix
    arch = get_dpkg_architecture() if arch_specific else "all"
    # Auto-determine some deps for 
    if arch_specific:
        depends += ["${shlibs:Depends}", "${misc:Depends}"]
    # Append to control file
    with open(control_filepath(), "a") as outfile:
        print("", file=outfile)
        print("Package: " + package_name, file=outfile)
        print("Architecture: " + arch, file=outfile)
        print("Depends: " + ", ".join(depends), file=outfile)
        if homepage:
            print("Homepage: " + homepage, file=outfile)
        if description:
            print("Description: " + description, file=outfile)

def init_misc_files():
    """
    Write miscellaneous files:
      - debian/compat
      - debian/source/format
    """
    os.makedirs(os.path.join(debian_dirpath(), "source"))
    with open(os.path.join(debian_dirpath(), "compat")) as outf:
        outf.write("8")
    with open(os.path.join(debian_dirpath(), "source", "format")) as outf:
        outf.write("3.0 (quilt)")

def parallelism():
    try:
        return os.cpu_count()
    except: # <= python 3.4
        return 2

def build_config_cmake(targets=["all"], cmake_opts=[], parallel=os.cp):
    """
    Configure the build for cmake
    """
    build_config["configure"] = [
        "cmake . -DCMAKE_INSTALL_PREFIX=debian/{}/usr {}".format(
            get_name(), " ".join(cmake_opts))
    ]
    build_config["build"] = [
        "make {} -j{}".format(
            " ".join(targets), parallelism())]
    build_config["install"] = [
        "mkdir -p debian/{}/usr".format(get_name())
        "make install"
    ]
    build_depends.append("cmake")

def test_config(arg):
    """Configure a command to run for testing"""
    build_config["test"] = [arg]

def install_usr_dir_to_package(src, suffix):
    """
    Use this to e.g. move the include dir from the main package
    directory where it was installed.

    src is relative to the install directory, not the project directory

    Call after build_config_...()

    move_usr_dir_to_package("usr/include", "dev")
    moves the /usr/include folder to <name>-dev/usr/
    """
    # Dont add mkdir twice
    mkdir = "mkdir -p debian/{}-dev/usr/".format(suffix)
    if mkdir not in build_config["install"]:
        build_config["install"].append(mkdir)
    # Add move command
    build_config["install"].append(
        "mv debian/{}/{} debian/{}-dev/usr/".format(
            get_name(), src, get_name(), suffix)
    )

def install_file(src, dst, suffix=None):
    """
    Copy arbitrary files from the project directory

    Call after build_config_...()

    install_copy_file("lib/foo.so", "usr/lib/")
    copies lib/foo.so from the project dir to <name>/usr/lib/
    """
    dstproj = get_name() if suffix is None else get_name() + "-" + suffix
    # Dont add mkdir twice
    mkdir = "mkdir -p debian/{}/{}".format("debian/{}/{}")
    if mkdir not in build_config["install"]:
        build_config["install"].append(mkdir)
    # Add move command
    build_config["install"].append(
        "cp {} debian/{}/{}".format(src, dstproj, dst)
    )

def write_rules():
    """
    Call after al
    """
    with open(os.path.join(debian_dirpath(), "rules")) as outf:
        print('#!/usr/bin/make -f', file=outf)
        print('%:', file=outf)
        print('\tdh $@', file=outf)
        for key, cmds in build_config.items():
            print('override_dh_auto_{}:'.format(key), file=outf)
            for cmd in cmds:
            print('\t{}'.format(cmd), file=outf)

def perform_debuild():
    cmd("debuild -S -uc", cwd=False)