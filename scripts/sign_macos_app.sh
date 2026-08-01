#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${APP_PATH:-$ROOT_DIR/dist/RJ.app}"
SIGN_IDENTITY="${SIGN_IDENTITY:--}"
ENTITLEMENTS="${ENTITLEMENTS:-$ROOT_DIR/entitlements.mas.plist}"

clear_finder_info() {
  while IFS= read -r file; do
    temp_file="${file}.xattr-clean"
    ditto --norsrc --noextattr "$file" "$temp_file"
    chmod --reference="$file" "$temp_file" 2>/dev/null || chmod "$(stat -f "%Lp" "$file")" "$temp_file"
    mv "$temp_file" "$file"
  done < <(find "$APP_PATH" -type f \( -xattrname com.apple.FinderInfo -o -xattrname com.apple.provenance -o -xattrname "com.apple.fileprovider.fpfs#P" \) -print)

  for attr in com.apple.FinderInfo com.apple.provenance "com.apple.fileprovider.fpfs#P"; do
    while IFS= read -r item; do
      SetFile -a b "$item" 2>/dev/null || true
      xattr -d "$attr" "$item" 2>/dev/null || true
    done < <(find -H "$APP_PATH" -xattrname "$attr" -print)
  done

  for item in \
    "$APP_PATH" \
    "$APP_PATH/Contents/MacOS/RJ" \
    "$APP_PATH/Contents/Resources/Python.framework" \
    "$APP_PATH/Contents/Frameworks/Python.framework"; do
    if [[ -e "$item" ]]; then
      SetFile -a b "$item" 2>/dev/null || true
      xattr -d com.apple.FinderInfo "$item" 2>/dev/null || true
      xattr -d com.apple.provenance "$item" 2>/dev/null || true
      xattr -d "com.apple.fileprovider.fpfs#P" "$item" 2>/dev/null || true
    fi
  done
}

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app at: $APP_PATH"
  exit 1
fi

ORIGINAL_APP_PATH="$APP_PATH"
STAGED_APP_PATH="/tmp/raw-jpeg-converter-sign-$$.app"
rm -R "$STAGED_APP_PATH" 2>/dev/null || true
ditto --norsrc --noextattr "$ORIGINAL_APP_PATH" "$STAGED_APP_PATH"
APP_PATH="$STAGED_APP_PATH"

xattr -cr "$APP_PATH"
clean_app="${APP_PATH}.xattr-clean"
rm -R "$clean_app" 2>/dev/null || true
ditto --norsrc --noextattr "$APP_PATH" "$clean_app"
rm -R "$APP_PATH"
mv "$clean_app" "$APP_PATH"
clear_finder_info

if [[ "$SIGN_IDENTITY" == "-" ]]; then
  SIGN_OPTIONS=(--force --options runtime --sign "$SIGN_IDENTITY")
else
  SIGN_OPTIONS=(--force --options runtime --timestamp --sign "$SIGN_IDENTITY")
fi

while IFS= read -r binary; do
  codesign "${SIGN_OPTIONS[@]}" "$binary"
done < <(find "$APP_PATH/Contents/Frameworks" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \))

if [[ -d "$APP_PATH/Contents/Frameworks/Python.framework" ]]; then
  codesign "${SIGN_OPTIONS[@]}" \
    "$APP_PATH/Contents/Frameworks/Python.framework/Versions/Current"
fi

clear_finder_info
executable="$APP_PATH/Contents/MacOS/RJ"
if [[ "$SIGN_IDENTITY" != "-" ]]; then
  temp_executable="${executable}.xattr-clean"
  ditto --norsrc --noextattr "$executable" "$temp_executable"
  chmod "$(stat -f "%Lp" "$executable")" "$temp_executable"
  mv "$temp_executable" "$executable"
  codesign "${SIGN_OPTIONS[@]}" "$executable"
fi
clear_finder_info
if [[ "$SIGN_IDENTITY" == "-" ]]; then
  codesign --force --sign "$SIGN_IDENTITY" "$APP_PATH"
else
  codesign --force --options runtime --timestamp --entitlements "$ENTITLEMENTS" --sign "$SIGN_IDENTITY" "$APP_PATH"
fi
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

rm -R "$ORIGINAL_APP_PATH"
ditto --norsrc --noextattr "$APP_PATH" "$ORIGINAL_APP_PATH"
rm -R "$APP_PATH"
