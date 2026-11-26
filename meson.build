project('pokeplatinum', ['c', 'cpp', 'nasm'],
    version: '1.0',
    meson_version: '>=1.12.0',
    default_options : [
        'buildtype=plain',
        'warning_level=0'
    ]
)

fs = import('fs')
build_target = get_option('build_target')
is_macos = (build_target == 'linux')

############################################################
###                    INCLUDE PATHS                     ###
############################################################
public_includes = include_directories('include', 'asm')
toplevel_includes = include_directories('.')


############################################################
###                    COMPILER FLAGS                    ###
############################################################
shared_args = ['-DPOKEPLATINUM_GENERATED_ENUM', '-g']

if get_option('revision') == '0'
    shared_args += ['-DPOKEPLATINUM_REVISION=0']
else
    shared_args += ['-DPOKEPLATINUM_REVISION=1']
endif

if get_option('tracy_enable')
    shared_args += '-DTRACY_ENABLE'
endif

c_args = shared_args
cpp_args = shared_args

add_global_arguments(c_args, language: 'c', native: is_macos)
add_global_arguments(cpp_args, language: 'cpp', native: is_macos)

if get_option('build_variant') == 'asan'
    # build_variant=asan: ASan + UBSan for the whole build (game, simulator and host tools).
    # See docs/headless_protocol.md.
    add_global_arguments(['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-Wno-error=format-overflow'],
        language: ['c', 'cpp'], native: is_macos)
    add_global_link_arguments(['-fsanitize=address,undefined'],
        language: ['c', 'cpp'], native: is_macos)
endif

# SDL3 headers for the whole build: libntr's OS/FS libraries and the game's port code include <SDL3/SDL.h>,
# and only libntr's simulator library links SDL (see subprojects/libntr/libraries/sim/meson.build).
if is_macos
    sdl3_headers_dep = dependency('sdl3', native: true, required: false)
    if sdl3_headers_dep.found()
        sdl3_include_arg = '-I' + sdl3_headers_dep.get_variable(pkgconfig: 'includedir')
        add_global_arguments(sdl3_include_arg, language: ['c', 'cpp'], native: true)
        add_global_arguments(sdl3_include_arg, language: ['c', 'cpp'], native: false)
    endif
endif

pokeplatinum_args = [
    '-DGAME_VERSION=VERSION_PLATINUM',
    '-DGAME_LANGUAGE=LANGUAGE_ENGLISH',
    '-std=c99',
    # Deterministically zero-init uninitialized stack locals in dev and release builds
    # to prevent clang -O3 UB, and surface uninitialized-read diagnostics.
    '-ftrivial-auto-var-init=zero',
    '-Wuninitialized',
    '-Wsometimes-uninitialized',
]

# Build variant: see meson.options. PM_KEEP_ASSERTS is the assert switch:
# defined in dev and asan, absent in release. GF_ASSERT still evaluates its
# expression in release because game code relies on assertion side effects.
build_variant = get_option('build_variant')
if build_variant != 'release'
    pokeplatinum_args += '-DPM_KEEP_ASSERTS'
endif

if build_variant == 'release'
    # Optimize all game code with -O3 + aliasing-safe flags (DS/Nitro C code type-puns u8/u16/u32).
    # Do not define NDEBUG: SDK/game assertions may contain side effects.
    # Apple ld64 -dead_strip triggers a boot soft-reset loop, so omit it on Darwin.
    pokeplatinum_args += ['-O3', '-g0', '-fno-strict-aliasing', '-ffunction-sections', '-fdata-sections', '-DPM_RELEASE_BUILD']
    add_global_arguments(['-g0', '-DPM_RELEASE_BUILD'], language: ['c', 'cpp'], native: is_macos)
elif build_variant == 'asan'
    pokeplatinum_args += ['-O1']
endif

if get_option('logging_enabled')
    pokeplatinum_args += ['-DLOGGING_ENABLED']
endif

link_args = []
if host_machine.system() == 'darwin'
    # Keep libntr's simulated registers and memory in definition order (see tools/macos/gen_order.py).
    sim_vars_order = meson.global_build_root() / 'sim_vars.order'
    run_command(find_program('python3'), files('tools/macos/gen_order.py'),
        meson.global_source_root() / 'subprojects' / 'libntr' / 'libraries' / 'sim' / 'src' / 'sim_vars.c', sim_vars_order, check: true)
    link_args += ['-Wl,-order_file,' + sim_vars_order, '-lobjc', '-framework', 'Foundation']
    if build_target == 'ios'
        link_args += ['-framework', 'Metal', '-framework', 'MetalKit', '-framework', 'UIKit',
            '-framework', 'QuartzCore', '-framework', 'CoreGraphics', '-framework', 'CoreHaptics',
            '-framework', 'CoreMotion', '-framework', 'GameController', '-framework', 'AVFoundation',
            '-framework', 'AudioToolbox', '-framework', 'CoreAudio', '-framework', 'CoreMedia',
            '-framework', 'CoreVideo', '-framework', 'ImageIO', '-framework', 'MobileCoreServices',
            '-framework', 'Security', '-framework', 'SystemConfiguration', '-framework', 'CoreBluetooth',
            '-framework', 'OpenGLES']
    endif
endif

############################################################
###                     DEPENDENCIES                     ###
############################################################
libntr_prj = subproject('libntr',
    default_options: [
        'card_game_code=CPUE',
        'card_maker_code=01'
    ])

nitrosdk_dep = dependency('NitroSDK',
    default_options: {
        'mwrap_sdk': '2.0/sp1p2',
        'sp1p3_conditionals': true,
    }
)

nitrosystem_dep = dependency('NitroSystem',
    default_options: {
        'mwrap_sdk': '2.0/sp2',
    }
)

nitrowifi_dep = dependency('NitroWiFi',
    default_options: {
        'mwrap_sdk': '2.0/sp1p2',
        'sp1p3_conditionals': true,
    }
)

nitrodwc_dep = dependency('NitroDWC',
    default_options: {
        'mwrap_sdk': '2.0/sp2p2',
        'link_ppwlobby': true,
    }
)

libvct_dep = dependency('libvct')

############################################################
###                       CONSTS                         ###
############################################################
subdir('generated')


############################################################
###                        TOOLS                         ###
############################################################
subdir('tools')


############################################################
###                      SPEC FILES                      ###
############################################################
subdir('platinum.us')


############################################################
###                  INTERNAL LIBRARIES                  ###
############################################################
subdir('lib')


############################################################
###                     FILE SYSTEM                      ###
############################################################
subdir('res')

############################################################
###                     GAME BINARY                      ###
############################################################
subdir('src')

trainer_ai_ss = custom_target(
    'trainer_ai_script.ss',
    output: 'trainer_ai_script.ss',
    input: files('src/battle/trainer_ai/script.s'),
    command: [
        'gcc',
        '-D__ASSEMBLER__',
        '-I', meson.global_source_root() / 'asm',
        '-I', meson.global_build_root(),
        '-I', meson.global_source_root() / 'include',
        '-MD', '-MF', '@DEPFILE@',
        '-E', '-nostdinc', '-'
    ],
    depfile: '@BASENAME@.d',
    capture: true,
    feed: true
)

if build_target == 'ios'
    trainer_ai_o = custom_target(
        'trainer_ai_script.o',
        output: 'trainer_ai_script.o',
        input: trainer_ai_ss,
        command: [
            meson.global_source_root() / 'tools' / 'ios' / 'trainer_ai_ios.sh',
            '@INPUT@', '@OUTPUT@',
            enumproc_exe,
            meson.global_source_root() / 'asm',
            meson.global_build_root(),
        ],
    )
else
    # macOS: Apple's assembler cannot fold the script's label arithmetic; see tools/macos/trainer_ai_macho.sh
    trainer_ai_o = custom_target(
        'trainer_ai_script.o',
        output: 'trainer_ai_script.o',
        input: trainer_ai_ss,
        command: [
            meson.global_source_root() / 'tools' / 'macos' / 'trainer_ai_macho.sh',
            '@INPUT@', '@OUTPUT@',
            enumproc_exe,
            meson.global_source_root() / 'asm',
            meson.global_build_root(),
        ],
    )
endif

# Symbolic name tables for the headless protocol, generated from the build's own data.
headless_names = custom_target('headless_names',
    output: ['headless_names.h', 'headless_names.c'],
    input: [
        'generated/map_headers.txt',
        'generated/vars_flags.txt',
        'generated/items.txt',
        'generated/species.txt',
        'generated/moves.txt',
        'generated/abilities.txt',
        'generated/natures.txt',
    ],
    command: [
        find_program('python3'),
        files('tools/dazzling/gen_headless_names.py'),
        meson.global_source_root(),
        '@OUTDIR@',
    ],
    # LOCALID_* names come from every res/field/maps/*/events.json, which are not listed as inputs:
    # regenerate on every build so edited events never leave the headless protocol with stale names.
    build_always_stale: true,
)

pokeplatinum_port_c = files(
    'src/port/charcode_convert.c',
    'src/port/debug_field.c',
    'src/port/headless_game.c',
    'src/port/headless_battle.c',
    'src/port/savedata_upgrade.c',
    'src/port/sim_config_prj.c',
    'src/port/sim_wide.c',
    'src/port/hirestext.c',
    'src/port/sim_gui_prj.cpp',
    'src/port/vram_stats.c',
    'src/port/gui_memory.cpp',
    'src/port/gui_cheats.cpp',
    'src/port/gui_battle_engine.cpp',
    'src/port/gui_battlelab.cpp',
    'src/port/gui_configPrj.cpp',
    'src/port/gui_createitem.cpp',
    'src/port/gui_createitem_utils.c',
    'src/port/gui_createmon.cpp',
    'src/port/gui_createmon_utils.c',
    'src/port/gui_mapjump.cpp',
    'src/port/gui_mapjump_utils.c'
)

pokeplatinum_port_c += headless_names[1]

if is_macos
    pokeplatinum_port_c += files('src/port/sim_icon.cpp')
endif

main = executable('main',
    sources: [
        pokeplatinum_c,
        pokeplatinum_port_c,
        c_consts_generators,
        naix_headers,
        h_headers,
        embed_headers,
    ],
    objects: trainer_ai_o,
    c_args: pokeplatinum_args,
    c_pch: 'include/pch/global_pch.h',
    include_directories: [
        public_includes,
        libcrypto_public_includes,
        libgds_public_includes,
        libspl_public_includes,
        ppwlobby_public_includes,
    ],
    dependencies: [
        nitrosdk_dep,
        nitrosystem_dep,
        nitrowifi_dep,
        nitrodwc_dep,
        libvct_dep,
    ],
    link_with: [
        libspl,
        libcrypto_ov97,
        libcrypto_static,
        libgds,
        libdwcenc,
        libdwcppwlobby,
        libdwcilobby,
    ],
    link_args: link_args,
    native: is_macos
)

############################################################
###                  APP BUNDLE / DATA                   ###
############################################################
copy_files_script = files('tools/scripts/copy_pc_files.sh')

pokeplatinum_app = custom_target('pokeplatinum.us',
    output: 'pokeplatinum.us',
    input: [
        main,
        nitrofs_files,
    ],
    command: [
        copy_files_script,
        meson.global_build_root(),
        filesys_csv,
        'pokeplatinum',
        build_target == 'ios' ? '-ios' : '',
    ],
    build_by_default: true
)

############################################################
###                       POSTCONF                       ###
############################################################
meson.add_postconf_script(postconf_py)

# Battle Lab specs: copied next to the game so the debug GUI can list them.
custom_target('battle_specs_copy',
    output: 'battle_specs.stamp',
    command: ['sh', '-c', 'mkdir -p "@OUTDIR@/battle_specs" && cp "@SOURCE_ROOT@/tools/battle/specs/"*.json "@OUTDIR@/battle_specs/" && touch "@OUTPUT@"'],
    build_by_default: true,
)
