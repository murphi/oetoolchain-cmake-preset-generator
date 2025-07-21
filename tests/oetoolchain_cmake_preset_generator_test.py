# Copyright (C) 2025 Martin Engelmann <murphi@posteo.de>

import pytest
from oetoolchain_cmake_preset_generator.main import (
    environment_parse_line,
    environment_parse_lines,
    get_oe_toolchain_path,
    get_sdk_base_path,
    prepare_cmake_preset,
    resolve_environment_variables,
    toolchain_parse_line,
    toolchain_parse_lines,
)

test_data_environment_parse_line = [
    ("export GDB=arm-foo-linux-gnueabi-gdb\n", "GDB", "arm-foo-linux-gnueabi-gdb"),
    ("export CPP=\"\"\n", "CPP", ""),
    (
        'export CXXFLAGS=" -O2 -pipe -g -feliminate-unused-debug-types "\n',
        "CXXFLAGS",
        " -O2 -pipe -g -feliminate-unused-debug-types ",
    ),
]


@pytest.mark.parametrize("line,variable,value", test_data_environment_parse_line)
def test_environment_parse_line(line: str, variable: str, value: str):
    result = environment_parse_line(line)
    assert result[variable] == value


def test_environment_parse_lines():
    lines = ["export A=a\n", "export B=b\n"]
    result = environment_parse_lines(lines)
    assert result["A"] == "a"
    assert result["B"] == "b"


def test_environment_parse_file():
    data = """# Check for LD_LIBRARY_PATH being set, which can break SDK and generally is a bad practice
# http://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html#AEN80
# http://xahlee.info/UnixResource_dir/_/ldpath.html
# Only disable this check if you are absolutely know what you are doing!
if [ ! -z "${LD_LIBRARY_PATH:-}" ]; then
    echo "Your environment is misconfigured, you probably need to 'unset LD_LIBRARY_PATH'"
    echo "but please check why this was set in the first place and that it's safe to unset."
    echo "The SDK will not operate correctly in most cases when LD_LIBRARY_PATH is set."
    echo "For more references see:"
    echo "  http://tldp.org/HOWTO/Program-Library-HOWTO/shared-libraries.html#AEN80"
    echo "  http://xahlee.info/UnixResource_dir/_/ldpath.html"
    return 1
fi

export OECORE_NATIVE_SYSROOT="/opt/foo/sysroots/x86_64-pokysdk-linux"
export OECORE_TARGET_SYSROOT="$SDKTARGETSYSROOT"
export OECORE_ACLOCAL_OPTS="-I /opt/foo/sysroots/x86_64-pokysdk-linux/usr/share/aclocal"
export OECORE_BASELIB="lib"
export OECORE_TARGET_ARCH="arm"
export OECORE_TARGET_OS="linux-gnueabi"
unset command_not_found_handle
export ARCH=arm
export CROSS_COMPILE=arm-foo-linux-gnueabi-

# Append environment subscripts
if [ -d "$OECORE_TARGET_SYSROOT/environment-setup.d" ]; then
    for envfile in $OECORE_TARGET_SYSROOT/environment-setup.d/*.sh; do
            . $envfile
    done
fi
"""
    result = environment_parse_lines(data.split("\n"))
    assert result["ARCH"] == "arm"
    assert result["OECORE_NATIVE_SYSROOT"] == "/opt/foo/sysroots/x86_64-pokysdk-linux"


def test_resolve_environment_variables():
    environment = {"A": "a", "B": "foo $A foo"}
    result = resolve_environment_variables(environment)
    assert result == {"A": "a", "B": "foo a foo"}


def test_toolchain_parse_line():
    line = r"set( CMAKE_FIND_ROOT_PATH $ENV{OECORE_TARGET_SYSROOT} )\n"
    result = toolchain_parse_line(line)
    assert result == ["OECORE_TARGET_SYSROOT"]


def test_toolchain_parse_lines():
    lines = [
        r"set( CMAKE_CXX_FLAGS $ENV{CXXFLAGS}  CACHE STRING \"\" FORCE )",
        r"set( CMAKE_SYSROOT $ENV{OECORE_TARGET_SYSROOT} )",
    ]
    result = toolchain_parse_lines(lines)
    assert result == ["CXXFLAGS", "OECORE_TARGET_SYSROOT"]


def test_get_oe_toolchain_path():
    environment = {"OECORE_NATIVE_SYSROOT": "/opt/foo/sysroots/x86_64-pokysdk-linux"}
    result = get_oe_toolchain_path(environment)
    assert (
        result
        == "/opt/foo/sysroots/x86_64-pokysdk-linux/usr/share/cmake/OEToolchainConfig.cmake"
    )


def test_get_sdk_base_path():
    environment = {"OECORE_NATIVE_SYSROOT": "/opt/foo/sysroots/x86_64-pokysdk-linux"}
    result = get_sdk_base_path(environment)
    assert result == "/opt/foo"


def test_prepare_cmake_preset():
    environment = {"OECORE_NATIVE_SYSROOT": "/opt/foo/sysroots/x86_64-pokysdk-linux"}
    result = prepare_cmake_preset("the_name", "Ninja", environment)

    expected = {
        "version": 3,
        "configurePresets": [
            {
                "name": "the_name",
                "description": "Generated from OpenEmbedded SDK in /opt/foo",
                "generator": "Ninja",
                "environment": {
                    "OECORE_NATIVE_SYSROOT": "/opt/foo/sysroots/x86_64-pokysdk-linux"
                },
                "toolchainFile": "/opt/foo/sysroots/x86_64-pokysdk-linux/usr/share/cmake/OEToolchainConfig.cmake",
            }
        ],
    }
    assert expected == result
