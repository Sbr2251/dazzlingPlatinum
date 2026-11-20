# iOS build (iPhone, landscape)

GPU-only (Metal through SDL GPU) port of the Mac app. The OpenGL backend, glad and
ImGui's GL3 backend are compiled out on iOS; there is no `Renderer=gl` fallback.
Game data is read-only in the bundle (`game/`, laid out exactly as the
macOS app); everything written (save, configs, logs) goes to the app's writable
dir. Landscape only, full screen, status bar hidden. Saves can be shared through
the Files app (`UIFileSharingEnabled` + `LSSupportsOpeningDocumentsInPlace`).

## Build (on the Mac)

```sh
tools/ios/build.sh sim       # Simulator: build_ios_sim/"Dazzling Platinum.app" (ad-hoc signed)
tools/ios/build.sh device    # Device:     build_ios/"Dazzling Platinum.app" + build_ios/DazzlingPlatinum.ipa (unsigned)
```

Prerequisites: Xcode, Homebrew `ninja pkg-config arm-none-eabi-gcc python3`
(the macOS build's prerequisites cover the rest). First run builds the static
deps — SDL3 (the Homebrew `sdl3` version, else 3.4.16), zlib, libpng, enet —
into `~/Documents/pokeplatinum-ios-deps/{iphoneos,iphonesimulator}` via
`tools/ios/build_deps.sh`. Host tools (the game data generators) build for the
Mac with `meson/native_ios_host.ini`; the game cross-compiles with
`meson/cross_pcport_ios.ini` / `cross_pcport_ios_sim.ini` (`build_target=ios`).

## Simulator

```sh
tools/ios/sim_run.sh            # creates/boots dz-ios-build, installs, launches, screenshots
xcrun simctl shutdown <udid>    # when idle
```

## Device: sideload with Sideloadly

1. Take `build_ios/DazzlingPlatinum.ipa` (unsigned; do not unzip/re-sign by hand).
2. In Sideloadly: select the .ipa, your iPhone (USB/Wi-Fi) and your Apple ID,
   then Start. Sideloadly re-signs it with your free provisioning profile.
3. On the phone: Settings > General > VPN & Device Management > trust your
   developer certificate, then launch Dazzling Platinum (landscape).
Free profiles expire after 7 days; re-run Sideloadly to refresh (your save in
the app's Documents survives a refresh install over the top).

## Notes

- Bundle id `local.dazzlingplatinum.ios`, minimum iOS 17.0, arm64.
- iOS defaults are `ScreenLayout=wide` + `Renderer=gpu` (platform lane).
- The bundle layout is a flat `.app` with `game/` at the root (the platform
  path API probes `Resources/game`, then `game/`); iOS codesign rejects a
  top-level `Resources` directory, so do not move it.
- The game runs from the bundle data dir on iOS because `FS_OpenFile` opens
  game data relative to the working directory; writable files are routed to
  Documents by the platform path API.
- Sandoq VM quirk (not on real Macs): its simulator GPU reports no Metal GPU
  family, so SDL's `MTLGPUFamilyApple3` gate rejects it. For VM-only checks,
  that one check was relaxed in the VM's local SDL build; device/real-Mac
  builds pass the gate as-is.
- The Mac (`tools/macos/build.sh`) and Linux builds are unchanged.
