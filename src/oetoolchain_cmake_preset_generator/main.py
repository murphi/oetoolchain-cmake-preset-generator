#!/usr/bin/env python3

# Copyright (C) 2025 Martin Engelmann <murphi@posteo.de>

from typing import Dict, List, Sequence
import os
import re
import pathlib
import argparse
import json
import sys


VERSION = "0.1"


def environment_parse_line(line: str) -> Dict[str, str]:
    m = re.search(r'export\s+(\w+)\s*=\s*"?(.*?)"?$', line)
    return {m[1]: m[2]} if m else {}


def environment_parse_lines(lines: Sequence[str]) -> Dict[str, str]:
    result = {}
    for each in lines:
        result = result | environment_parse_line(each)
    return result


def environment_parse_file(filename: str) -> Dict[str, str]:
    with open(filename, "r", encoding="utf-8") as environment_file:
        return environment_parse_lines(environment_file.readlines())


def resolve_environment_variables(environment: Dict[str, str]) -> Dict[str, str]:
    resolved = {}
    for key, value in environment.items():
        resolved_value = value
        # Replace occurrences of $VAR with the value of VAR from the environment or os.environ
        for var in environment:
            resolved_value = resolved_value.replace(f"${var}", environment[var])
        for var in environment:
            if f"${var}" in resolved_value and var in os.environ:
                resolved_value = resolved_value.replace(f"${var}", os.environ[var])
        resolved[key] = resolved_value
    return resolved

def get_oe_toolchain_path(environment: Dict[str, str]) -> str:
    return environment["OECORE_NATIVE_SYSROOT"] + "/usr/share/cmake/OEToolchainConfig.cmake"


def get_sdk_base_path(environment: Dict[str, str]) -> str:
    return str(pathlib.Path(environment["OECORE_NATIVE_SYSROOT"]).parent.parent)


def toolchain_parse_line(line: str) -> List[str]:
    m = re.search(r"\$ENV\{([^}]+)\}", line)
    return [m[1]] if m else []


def toolchain_parse_lines(lines: Sequence[str]) -> List[str]:
    result = []
    for each in lines:
        result = result + toolchain_parse_line(each)
    return result


def prepare_cmake_preset(
    name: str, generator: str, environment: Dict[str, str]
) -> Dict:
    return {
        "version": 3,
        "configurePresets": [
            {
                "name": name,
                "description": "Generated from OpenEmbedded SDK in "
                + get_sdk_base_path(environment),
                "generator": generator,
                "environment": environment,
                "toolchainFile": get_oe_toolchain_path(environment),
            }
        ],
    }


def write_cmake_preset(preset_filename: str, preset: Dict):
    if preset_filename == "-":
        json.dump(preset, sys.stdout, indent=2)
    else:
        with open(preset_filename, "w", encoding="UTF-8") as preset_file:
            json.dump(preset, preset_file, indent=2)


def parse_arguments():
    argparser = argparse.ArgumentParser(
        "oetoolchain-cmake-preset-generator",
        description="Generate CMake preset from OpenEmbedded / Yocto toolchain",
    )
    argparser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    argparser.add_argument(
        "-i", "--input", required=True, help="path to environment setup script"
    )
    argparser.add_argument(
        "-o", "--output", default="-", help="Path to generated CMake preset"
    )
    argparser.add_argument(
        "-n",
        "--name",
        default="oe-toolchain",
        help="Name of the generated preset (default=%(default)s)",
    )
    argparser.add_argument(
        "-g",
        "--generator",
        default="Ninja",
        help="Generator for the preset (default=%(default)s)",
    )

    args = argparser.parse_args()
    return args


def main():
    args = parse_arguments()

    environment = resolve_environment_variables(environment_parse_file(args.input))
    preset = prepare_cmake_preset(args.name, args.generator, environment)
    write_cmake_preset(args.output, preset)


if __name__ == "__main__":
    main()
