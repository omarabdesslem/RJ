#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${APP_PATH:-$ROOT_DIR/dist/RJ.app}"
DMG_PATH="${DMG_PATH:-$ROOT_DIR/dist/RJ.dmg}"
DEVELOPER_ID_APP="${DEVELOPER_ID_APP:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app at: $APP_PATH"
  echo "Run scripts/build_macos_app.sh first."
  exit 1
fi

STAGE_DIR="$(mktemp -d /tmp/rj-dmg.XXXXXX)"
VOLUME_DIR="$STAGE_DIR/RJ"
STAGED_APP_PATH="$VOLUME_DIR/RJ.app"
STAGED_DMG_PATH="$STAGE_DIR/RJ.dmg"
trap 'rm -R "$STAGE_DIR"' EXIT

mkdir "$VOLUME_DIR"
ditto --norsrc --noextattr "$APP_PATH" "$STAGED_APP_PATH"

if [[ -n "$DEVELOPER_ID_APP" ]]; then
  APP_PATH="$STAGED_APP_PATH" SIGN_IDENTITY="$DEVELOPER_ID_APP" ENTITLEMENTS="$ROOT_DIR/app/entitlements.mas.plist" \
    "$ROOT_DIR/scripts/sign_macos_app.sh"
fi

codesign --verify --deep --strict --verbose=2 "$STAGED_APP_PATH"
ln -s /Applications "$VOLUME_DIR/Applications"

hdiutil create -quiet -volname "RJ" -srcfolder "$VOLUME_DIR" -format UDZO -ov "$STAGED_DMG_PATH"
hdiutil verify "$STAGED_DMG_PATH"

if [[ -n "$DEVELOPER_ID_APP" ]]; then
  codesign --force --timestamp --sign "$DEVELOPER_ID_APP" "$STAGED_DMG_PATH"
  codesign --verify --verbose=2 "$STAGED_DMG_PATH"
fi

ditto --norsrc --noextattr "$STAGED_DMG_PATH" "$DMG_PATH"
hdiutil verify "$DMG_PATH"

if [[ -n "$NOTARY_PROFILE" ]]; then
  if [[ -z "$DEVELOPER_ID_APP" ]]; then
    echo "NOTARY_PROFILE requires DEVELOPER_ID_APP."
    exit 1
  fi
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
  xcrun stapler validate "$DMG_PATH"
else
  echo "DMG created without notarization. For public distribution, rerun with DEVELOPER_ID_APP and NOTARY_PROFILE."
fi

echo "Built $DMG_PATH"
