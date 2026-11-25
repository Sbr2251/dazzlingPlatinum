# Public includes
ppwlobby_public_includes = include_directories('include')

# macOS/iOS clang: libc++ requires C++14 for PPW_Allocator; -fpermissive for legacy code.
ppwlobby_c_args = ['-fpermissive']
ppwlobby_cpp_only_args = ['-std=c++14']

# Libraries
ppwlobby_libs = []
subdir('libraries')
