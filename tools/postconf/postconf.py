#!/usr/bin/env python3

import os
import re

BUILD_DIRECTORY = os.environ["MESON_BUILD_ROOT"]


def backslash_to_forward_slash(file_string: str) -> str:
    return file_string.replace('\\\\', '/')


def fix_static_libs(file_string: str) -> str:
    """Replace single quotes around linked libraries with double quotes."""
    return file_string.replace("'lib", '"lib').replace(".a'", '.a"')


def nasm_to_asm(file_string: str) -> str:
    return file_string.replace('Nasm', 'ASM')


def bytecode_scripts_order_only_deps(file_string: str) -> str:
    """Express bytecode-script dependencies on generated headers as order-only."""
    return re.sub(
        r"build ([\w\/\.\-]+): (\w+) ([\w\/\.\-]+) \| ([\w\/\.\-]+\/make_script_bin\.sh) ((.*)(tools/enumproc/enumproc(\.exe)?)(.*))",
        r"build \1: \2 \3 | \4 \7 || \6\9",
        file_string,
    )


def main():
    build_ninja = f'{BUILD_DIRECTORY}/build.ninja'
    compile_commands = f'{BUILD_DIRECTORY}/compile_commands.json'

    with open(build_ninja, 'r') as f_in, open(compile_commands, 'r') as cc_in:
        build_ninja_str = f_in.read()
        compile_commands_str = cc_in.read()

    build_ninja_str = backslash_to_forward_slash(build_ninja_str)
    build_ninja_str = fix_static_libs(build_ninja_str)
    build_ninja_str = nasm_to_asm(build_ninja_str)
    build_ninja_str = bytecode_scripts_order_only_deps(build_ninja_str)

    compile_commands_str = backslash_to_forward_slash(compile_commands_str)

    with open(build_ninja, 'w') as f_out, open(compile_commands, 'w') as cc_out:
        f_out.write(build_ninja_str)
        cc_out.write(compile_commands_str)


if __name__ == '__main__':
    main()
