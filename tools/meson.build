# Native asset-pipeline tools for macOS/iOS builds
subdir('nitroarc') # libnitroarc
subdir('enumproc') # libenum
subdir('dataproc') # Requires libnitroarc and libenum
subdir('msgenc')   # Requires libdataproc

subdir('jsoncnv')
subdir('nitrobtx')
subdir('nitrogfx')
subdir('nitrosfx')
subdir('ordergen')
subdir('postconf')
subdir('scripts')

copy_exe = find_program('cp')

# ARM binutils (used by the field/battle script and move-animation bytecode assemblers)
arm_none_eabi_gcc_exe = find_program('arm-none-eabi-gcc', native: true)
arm_none_eabi_objcopy_exe = find_program('arm-none-eabi-objcopy', native: true)
