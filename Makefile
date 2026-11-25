.PHONY: all macos macos-release macos-asan ios ios-sim static-checks test clean distclean

all: macos

macos:
	tools/macos/build.sh dev

macos-release:
	tools/macos/build.sh release

macos-asan:
	tools/macos/build.sh asan

ios:
	tools/ios/build.sh device

ios-sim:
	tools/ios/build.sh sim

static-checks:
	python3 tools/dazzling/test/static_checks.py

test: macos
	python3 tools/dazzling/test/run.py -j 2

clean:
	rm -rf build_macos build_macos_release build_macos_asan build_ios build_ios_sim

distclean: clean
	rm -rf subprojects/meson-1.12.0
