# source tools/sdl_gpu_migration/env_devserver.sh
# Build/run environment for the SDL GPU migration on the devserver (docs/sdl_gpu_migration/PLAN.md).
SDL3_PREFIX=/data/repos/dp-wt/sdl3-deps/prefix
ENET_PREFIX=/data/repos/dp-wt/team-debug-headless-scratch/deps/prefix
export LIBRARY_PATH="$SDL3_PREFIX/lib:$SDL3_PREFIX/lib64:$ENET_PREFIX/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export CPATH="$SDL3_PREFIX/include:$ENET_PREFIX/include${CPATH:+:$CPATH}"
export PKG_CONFIG_PATH="$SDL3_PREFIX/lib/pkgconfig:$SDL3_PREFIX/lib64/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$SDL3_PREFIX/lib:$SDL3_PREFIX/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$SDL3_PREFIX/bin:$PATH"
export LP_NUM_THREADS=2
export SDL_VIDEO_DRIVER=offscreen
