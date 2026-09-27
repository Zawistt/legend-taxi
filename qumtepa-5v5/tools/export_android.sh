#!/usr/bin/env bash
# Android APK: godot/ loyihasidan arm64 APK (Godot 4.3 Android shabloni, gradle'siz), keyin imzolash.
# Kerak: Godot 4.3 eksport shablonlari (~/.local/share/godot/export_templates/4.3.stable/android_release.apk),
#        Java 17+, uber-apk-signer.jar (GitHub: patrickfav/uber-apk-signer) — Android SDK shart emas.
# Ishlatish: GODOT=/yo'l/godot SIGNER=/yo'l/uber-apk-signer.jar ./export_android.sh [chiqish.apk]
set -euo pipefail
cd "$(dirname "$0")/../godot"
GODOT="${GODOT:-godot}"
SIGNER="${SIGNER:-uber-apk-signer.jar}"
OUT="$(realpath -m "${1:-../qumtepa.apk}")"
KS="${KS:-$HOME/.local/share/godot/keystores/debug.keystore}"
cat > export_presets.cfg <<CFG
[preset.0]

name="Android"
platform="Android"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter="*.json"
exclude_filter="tests/*, tools/*, textures/*, characters/ct_hero*, characters/t_operator*, characters/ct_soldier*, characters/*_arms*, characters/t_arms*, main_greybox.tscn, map/qumtepa5v5_greybox*"
export_path="$OUT.unsigned.apk"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
gradle_build/use_gradle_build=false
gradle_build/export_format=0
gradle_build/min_sdk=""
gradle_build/target_sdk=""
architectures/armeabi-v7a=false
architectures/arm64-v8a=true
architectures/x86=false
architectures/x86_64=false
version/code=13
version/name="0.13"
package/unique_name="uz.qumtepa.game"
package/name="Qumtepa"
package/signed=false
package/app_category=2
package/retain_data_on_uninstall=false
package/exclude_from_recents=false
package/show_in_android_tv=false
package/show_in_app_library=true
package/show_as_launcher_app=false
launcher_icons/main_192x192=""
graphics/opengl_debug=false
xr_features/xr_mode=0
screen/immersive_mode=true
screen/support_small=true
screen/support_normal=true
screen/support_large=true
screen/support_xlarge=true
user_data_backup/allow=false
command_line/extra_args=""
apk_expansion/enable=false
permissions/custom_permissions=PackedStringArray()
permissions/internet=false
permissions/vibrate=true
CFG
rm -f "$OUT.unsigned.apk" "$OUT"
# telefon uchun yengilroq resurslar (faqat eksport vaqtida; keyin asl sozlamalar qaytariladi):
#   qahramon teksturalari — 1024 px, lossy (WebP) siqish; ovozlar — QOA siqish (~5 marta kichik)
BK="$(mktemp -d)"
MOB=()
for f in characters/*.jpg.import $(find . -name "*.wav.import" -not -path "./.godot/*"); do
  [ -f "$f" ] || continue
  mkdir -p "$BK/$(dirname "$f")"; cp "$f" "$BK/$f"; MOB+=("$f")
  case "$f" in
    *.jpg.import) sed -i 's/^compress\/mode=0/compress\/mode=1/; s/^process\/size_limit=0/process\/size_limit=1024/' "$f" ;;
    *.wav.import) sed -i 's/^compress\/mode=0/compress\/mode=2/' "$f" ;;
  esac
  grep -o '"res://.godot/imported/[^"]*"' "$f" | tr -d '"' | sed 's|res://||' | xargs -r rm -f
done
"$GODOT" --headless --import >/dev/null 2>&1 || true
"$GODOT" --headless --export-release "Android" "$OUT.unsigned.apk" 2>&1 | grep -v "^$" | tail -4
for f in "${MOB[@]}"; do
  cp "$BK/$f" "$f"
  grep -o '"res://.godot/imported/[^"]*"' "$f" | tr -d '"' | sed 's|res://||' | xargs -r rm -f
done
rm -rf "$BK"
"$GODOT" --headless --import >/dev/null 2>&1 || true
ls -la "$OUT.unsigned.apk"
# imzolash (v1+v2+v3) va zipalign — Godot debug kaliti bilan
TMP="$(mktemp -d)"
java -jar "$SIGNER" -a "$OUT.unsigned.apk" -o "$TMP" --ks "$KS" --ksAlias androiddebugkey --ksPass android --ksKeyPass android --allowResign 2>&1 | tail -6
mv "$TMP"/*.apk "$OUT"
rm -rf "$TMP" "$OUT.unsigned.apk"
java -jar "$SIGNER" -a "$OUT" --onlyVerify 2>&1 | grep -iE "verif|signature|scheme" | head -6
ls -la "$OUT"
