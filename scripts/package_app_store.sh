#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/RJ.app"
PKG_PATH="$ROOT_DIR/dist/RJ-mas.pkg"

APP_CERT="${APP_CERT:-3rd Party Mac Developer Application: YOUR TEAM NAME (TEAMID)}"
INSTALLER_CERT="${INSTALLER_CERT:-3rd Party Mac Developer Installer: YOUR TEAM NAME (TEAMID)}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app at: $APP_PATH"
  echo "Run scripts/build_macos_app.sh first."
  exit 1
fi

# A file-provider folder such as Documents can attach Finder metadata after signing.
# Build the upload package from a clean temporary copy so its sealed resources remain valid.
if [[ "$APP_CERT" == *"YOUR TEAM NAME"* || "$INSTALLER_CERT" == *"YOUR TEAM NAME"* ]]; then
  echo "Set APP_CERT and INSTALLER_CERT to your Mac App Store signing identities first."
  echo "Run: security find-identity -v"
  exit 1
fi

PACKAGE_STAGE_DIR="$(mktemp -d /tmp/raw-jpeg-converter-mas.XXXXXX)"
STAGED_APP_PATH="$PACKAGE_STAGE_DIR/RJ.app"
STAGED_PKG_PATH="$PACKAGE_STAGE_DIR/RJ-mas.pkg"
trap 'rm -R "$PACKAGE_STAGE_DIR"' EXIT

ditto --norsrc --noextattr "$APP_PATH" "$STAGED_APP_PATH"
APP_PATH="$STAGED_APP_PATH" SIGN_IDENTITY="$APP_CERT" ENTITLEMENTS="$ROOT_DIR/entitlements.mas.plist" \
  "$ROOT_DIR/scripts/sign_macos_app.sh"

productbuild --component "$STAGED_APP_PATH" /Applications \
  --sign "$INSTALLER_CERT" \
  "$STAGED_PKG_PATH"
pkgutil --check-signature "$STAGED_PKG_PATH"
ditto --norsrc --noextattr "$STAGED_PKG_PATH" "$PKG_PATH"
pkgutil --check-signature "$PKG_PATH"

echo "Built $PKG_PATH"
echo "Upload this package with Transporter or xcrun altool/notarytool as required by your App Store Connect workflow."
