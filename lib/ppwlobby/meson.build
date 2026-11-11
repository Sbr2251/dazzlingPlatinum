# Public includes
ppwlobby_public_includes = include_directories('include')

ppwlobby_c_args = []

if(build_target == 'arm')
    ppwlobby_c_args = [
        '-wrap:sdk', '2.0/sp2p3',
        '-nothumb'
    ]
elif(build_target == 'prospero')
    ppwlobby_c_args = [
        '-fpermissive'
    ]
elif(host_machine.system() == 'darwin')
    # macOS: clang rejects -std=c++03 on the C files these flags also reach, and libc++'s C++03 map cannot construct
    # through PPW_Allocator (it builds the const key in place); C++14 compiles the same code
    ppwlobby_c_args = [
        '-fpermissive',
    ]
    ppwlobby_cpp_only_args = [
        '-std=c++14',
    ]
else
    ppwlobby_c_args = [
        '-fpermissive',
        '-std=c++03'
    ]
endif
if not is_variable('ppwlobby_cpp_only_args')
    ppwlobby_cpp_only_args = []
endif

# Libraries
ppwlobby_libs = []
subdir('libraries')
