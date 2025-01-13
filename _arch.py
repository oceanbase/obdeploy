# coding: utf-8
# Copyright (c) 2025 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import ctypes
import struct

_ppc64_native_is_best = True

# dict mapping arch -> ( multicompat, best personality, biarch personality )
multilibArches = { 
    "x86_64":  ( "athlon", "x86_64", "athlon" ),
    "sparc64v": ( "sparcv9v", "sparcv9v", "sparc64v" ),
    "sparc64": ( "sparcv9", "sparcv9", "sparc64" ),
    "ppc64":   ( "ppc", "ppc", "ppc64" ),
    "s390x":   ( "s390", "s390x", "s390" ),
}
if _ppc64_native_is_best:
    multilibArches["ppc64"] = ( "ppc", "ppc64", "ppc64" )

arches = {
    # ia32
    "athlon": "i686",
    "i686": "i586",
    "geode": "i686",
    "i586": "i486",
    "i486": "i386",
    "i386": "noarch",
    
    # amd64
    "x86_64": "athlon",
    "amd64": "x86_64",
    "ia32e": "x86_64",

    #ppc64le
    "ppc64le":  "noarch",

    # ppc
    "ppc64p7": "ppc64",
    "ppc64pseries": "ppc64",
    "ppc64iseries": "ppc64",    
    "ppc64": "ppc",
    "ppc": "noarch",
    
    # s390{,x}
    "s390x": "s390",
    "s390": "noarch",
    
    # sparc
    "sparc64v": "sparcv9v",
    "sparc64": "sparcv9",
    "sparcv9v": "sparcv9",
    "sparcv9": "sparcv8",
    "sparcv8": "sparc",
    "sparc": "noarch",

    # alpha
    "alphaev7":   "alphaev68",
    "alphaev68":  "alphaev67",
    "alphaev67":  "alphaev6",
    "alphaev6":   "alphapca56",
    "alphapca56": "alphaev56",
    "alphaev56":  "alphaev5",
    "alphaev5":   "alphaev45",
    "alphaev45":  "alphaev4",
    "alphaev4":   "alpha",
    "alpha":      "noarch",

    # arm
    "armv7l": "armv6l",
    "armv6l": "armv5tejl",
    "armv5tejl": "armv5tel",
    "armv5tel": "noarch",

    #arm hardware floating point
    "armv7hnl": "armv7hl",
    "armv7hl": "noarch",

    # arm64
    "arm64": "noarch",

    # aarch64
    "aarch64": "noarch",

    # super-h 
    "sh4a": "sh4",
    "sh4": "noarch",
    "sh3": "noarch",
    
    #itanium
    "ia64": "noarch",
}

#  Will contain information parsed from /proc/self/auxv via _parse_auxv().
# Should move into rpm really.
_aux_vector = {
    "platform": "",
    "hwcap": 0,
}

    
def _try_read_cpuinfo():
    """ Try to read /proc/cpuinfo ... if we can't ignore errors (ie. proc not
        mounted). """
    try:
        return open("/proc/cpuinfo", "r")
    except:
        return []


def _parse_auxv():
    """ Read /proc/self/auxv and parse it into global dict for easier access
        later on, very similar to what rpm does. """
    # In case we can't open and read /proc/self/auxv, just return
    try:
        data = open("/proc/self/auxv", "rb").read()
    except:
        return

    # Define values from /usr/include/elf.h
    AT_PLATFORM = 15
    AT_HWCAP = 16
    fmtlen = struct.calcsize("LL")
    offset = 0
    platform = ctypes.c_char_p()

    # Parse the data and fill in _aux_vector dict
    while offset <= len(data) - fmtlen:
        at_type, at_val = struct.unpack_from("LL", data, offset)
        if at_type == AT_PLATFORM:
            platform.value = at_val
            _aux_vector["platform"] = platform.value
        if at_type == AT_HWCAP:
            _aux_vector["hwcap"] = at_val
        offset = offset + fmtlen


def getCanonX86Arch(arch):
    # 
    if arch == "i586":
        for line in _try_read_cpuinfo():
            if line.startswith("model name"):
                if line.find("Geode(TM)") != -1:
                    return "geode"
                break
        return arch
    # only athlon vs i686 isn't handled with uname currently
    if arch != "i686":
        return arch

    # if we're i686 and AuthenticAMD, then we should be an athlon
    for line in _try_read_cpuinfo():
        if line.startswith("vendor") and line.find("AuthenticAMD") != -1:
            return "athlon"
        # i686 doesn't guarantee cmov, but we depend on it
        elif line.startswith("flags"):
            if line.find("cmov") == -1:
                return "i586"
            break

    return arch


def getCanonARMArch(arch):
    # the %{_target_arch} macro in rpm will let us know the abi we are using 
    try:
        import rpm
        target = rpm.expandMacro('%{_target_cpu}')
        if target.startswith('armv7h'):
            return target
    except:
        pass
    return arch


def getCanonPPCArch(arch):
    # FIXME: should I do better handling for mac, etc?
    if arch != "ppc64":
        return arch

    machine = None
    for line in _try_read_cpuinfo():
        if line.find("machine") != -1:
            machine = line.split(':')[1]
            break

    platform = _aux_vector["platform"]
    if machine is None and not platform:
        return arch

    try:
        if platform.startswith("power") and int(platform[5:].rstrip('+')) >= 7:
            return "ppc64p7"
    except:
        pass

    if machine is None:
        return arch

    if machine.find("CHRP IBM") != -1:
        return "ppc64pseries"
    if machine.find("iSeries") != -1:
        return "ppc64iseries"
    return arch


def getCanonSPARCArch(arch):
    # Deal with sun4v, sun4u, sun4m cases
    SPARCtype = None
    for line in _try_read_cpuinfo():
        if line.startswith("type"):
            SPARCtype = line.split(':')[1]
            break
    if SPARCtype is None:
        return arch

    if SPARCtype.find("sun4v") != -1:
        if arch.startswith("sparc64"):
            return "sparc64v"
        else:
            return "sparcv9v"
    if SPARCtype.find("sun4u") != -1:
        if arch.startswith("sparc64"):
            return "sparc64"
        else:
            return "sparcv9"
    if SPARCtype.find("sun4m") != -1:
        return "sparcv8"
    return arch

def getCanonX86_64Arch(arch):
    if arch != "x86_64":
        return arch

    vendor = None
    for line in _try_read_cpuinfo():
        if line.startswith("vendor_id"):
            vendor = line.split(':')[1]
            break
    if vendor is None:
        return arch

    if vendor.find("Authentic AMD") != -1 or vendor.find("AuthenticAMD") != -1:
        return "amd64"
    if vendor.find("GenuineIntel") != -1:
        return "ia32e"
    return arch

 
def getCanonArch(skipRpmPlatform = 0):
    if not skipRpmPlatform and os.access("/etc/rpm/platform", os.R_OK):
        try:
            f = open("/etc/rpm/platform", "r")
            line = f.readline()
            f.close()
            (arch, vendor, opersys) = line.split("-", 2)
            return arch
        except:
            pass
        
    arch = os.uname()[4]

    _parse_auxv()

    if (len(arch) == 4 and arch[0] == "i" and arch[2:4] == "86"):
        return getCanonX86Arch(arch)

    if arch.startswith("arm"):
        return getCanonARMArch(arch)
    if arch.startswith("ppc"):
        return getCanonPPCArch(arch)
    if arch.startswith("sparc"):
        return getCanonSPARCArch(arch)
    if arch == "x86_64":
        return getCanonX86_64Arch(arch)
    return arch


canonArch = getCanonArch()


def isMultiLibArch(arch=None):
    """returns true if arch is a multilib arch, false if not"""
    if arch is None:
        arch = canonArch

    if arch not in arches: # or we could check if it is noarch
        return 0
    
    if arch in multilibArches:
        return 1
        
    if arches[arch] in multilibArches:
        return 1
    
    return 0


def getBaseArch(myarch=None):
    """returns 'base' arch for myarch, if specified, or canonArch if not.
       base arch is the arch before noarch in the arches dict if myarch is not
       a key in the multilibArches."""

    if not myarch:
        myarch = canonArch

    if myarch not in arches: # this is dumb, but <shrug>
        return myarch

    if myarch.startswith("sparc64"):
        return "sparc"
    elif myarch == "ppc64le":
        return "ppc64le"
    elif myarch.startswith("ppc64") and not _ppc64_native_is_best:
        return "ppc"
    elif myarch.startswith("arm64"):
        return "arm64"
    elif myarch.startswith("armv7h"):
        return "armhfp"
    elif myarch.startswith("arm"):
        return "arm"
        
    if isMultiLibArch(arch=myarch):
        if myarch in multilibArches:
            return myarch
        else:
            return arches[myarch]
    
    if myarch in arches:
        basearch = myarch
        value = arches[basearch]
        while value != 'noarch':
            basearch = value
            value = arches[basearch]
    
        return basearch


def getArchList(thisarch=None):
    # this returns a list of archs that are compatible with arch given
    if not thisarch:
        thisarch = canonArch
    
    archlist = [thisarch]
    while thisarch in arches:
        thisarch = arches[thisarch]
        archlist.append(thisarch)

    # hack hack hack
    # sparc64v is also sparc64 compat
    if archlist[0] == "sparc64v":
        archlist.insert(1,"sparc64")
    
    # if we're a weirdo arch - add noarch on there.
    if len(archlist) == 1 and archlist[0] == thisarch:
        archlist.append('noarch')
    return archlist

