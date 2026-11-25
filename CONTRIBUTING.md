# Contributing to Dazzling Platinum (macOS & iOS)

## Platform Scope

Dazzling Platinum targets **macOS (Apple Silicon)** and **iOS (arm64)** via **SDL3 + Metal**. NDS ROM compilation and matching decompilation constraints no longer apply.

## Coding Guidelines

1. **64-bit clang C99 cleanliness:**
   - Include the header for every function you call (clang rejects implicit declarations).
   - Never store a pointer in a `u32`; use `uPtr` / `uintptr_t` for pointer arithmetic and alignment.
   - Never pass `NULL` for an integer parameter.
2. **Adding source files:**
   - Game C files: add directly to `src/meson.build`.
   - Port/simulator bridge files: add to `pokeplatinum_port_c` in `meson.build`.
   - Simulator (`libntr`) changes: edit inside `subprojects/libntr`, regenerate `tools/macos/patches/libntr.patch` (`git -C subprojects/libntr add -N . && git -C subprojects/libntr diff HEAD > tools/macos/patches/libntr.patch`), and verify it applies cleanly against the pinned revision in `tools/macos/patches/REVISIONS`.
3. **Text encoding:**
   - Always use straight ASCII apostrophes (`'` U+0027) in all JSON/text/code files; never use curly quotes.
4. **Formatting:**
   - Follow `.clang-format` and `.editorconfig`.

## Verification Checklist Before Merging

1. Run static content checks (no build required):
   ```sh
   python3 tools/dazzling/test/static_checks.py
   ```
2. Build the macOS app cleanly:
   ```sh
   tools/macos/build.sh release
   ```
3. Run the headless scenario & visual regression suite:
   ```sh
   python3 tools/dazzling/test/run.py -j 2
   ```
4. For iOS changes, also verify `tools/ios/build.sh sim` (and `tools/ios/build.sh device` when targeting hardware).
