#!/bin/sh
# Install or update wwss for the current user. Application configuration is untouched.
set -eu

fail() { printf 'wwss install: %s\n' "$*" >&2; exit 1; }

download() {
    curl --fail --silent --show-error --location --retry 2 \
        --connect-timeout 15 --max-time 300 "$1" --output "$2"
}

add_path_to_profile() {
    profile=$1
    marker='# >>> wwss PATH >>>'
    if [ -f "$profile" ] && grep -Fqx "$marker" "$profile"; then
        return
    fi
    mkdir -p "$(dirname "$profile")"
    cat >> "$profile" <<'WWSS_PATH'

# >>> wwss PATH >>>
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
# <<< wwss PATH <<<
WWSS_PATH
}

main() {
    version=latest
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --version)
                [ "$#" -ge 2 ] || fail '--version requires a release tag'
                version=$2
                shift 2
                ;;
            --help)
                printf 'Usage: sh install.sh [--version v0.1.0]\n'
                return
                ;;
            *) fail "Unknown option: $1" ;;
        esac
    done

    [ -n "${HOME:-}" ] || fail 'HOME is not set'
    for tool in curl tar awk mktemp; do
        command -v "$tool" >/dev/null 2>&1 || fail "Required command missing: $tool"
    done
    case "$(uname -s)" in
        Linux) goos=linux ;;
        Darwin) goos=darwin ;;
        *) fail 'This installer supports Linux and macOS. Use install.ps1 on Windows.' ;;
    esac
    case "$(uname -m)" in
        x86_64|amd64) arch=amd64 ;;
        aarch64|arm64) arch=arm64 ;;
        *) fail 'A 64-bit x86-64 or ARM64 operating system is required' ;;
    esac
    # Select native Apple Silicon even when this shell is running under Rosetta.
    if [ "$goos" = darwin ] && [ "$(sysctl -n hw.optional.arm64 2>/dev/null || true)" = 1 ]; then
        arch=arm64
    fi
    if command -v getconf >/dev/null 2>&1 && [ "$(getconf LONG_BIT 2>/dev/null || true)" = 32 ]; then
        fail 'A 32-bit userland is unsupported; install a 64-bit operating system'
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        hash_tool=sha256sum
    elif command -v shasum >/dev/null 2>&1; then
        hash_tool=shasum
    else
        fail 'SHA-256 verification requires sha256sum or shasum'
    fi

    release_root=${WWSS_RELEASE_BASE_URL:-https://github.com/gavsidhu/wwss/releases}
    release_root=${release_root%/}
    if [ "$version" = latest ]; then
        manifest_url=$release_root/latest/download/checksums.txt
    else
        version=${version#v}
        case "$version" in ''|*[!0-9A-Za-z.+-]*) fail 'Invalid release version' ;; esac
        manifest_url=$release_root/download/v$version/checksums.txt
    fi

    scratch=$(mktemp -d)
    staged_binary=
    trap 'rm -rf "$scratch"; if [ -n "$staged_binary" ]; then rm -f "$staged_binary"; fi' EXIT
    trap 'exit 1' HUP INT TERM
    printf 'Finding wwss for %s/%s...\n' "$goos" "$arch"
    download "$manifest_url" "$scratch/checksums.txt" || fail 'Could not download checksums. A published release is required.'
    asset=$(awk -v suffix="_${goos}_${arch}.tar.gz" \
        'NF == 2 && $2 ~ /^wwss_/ && substr($2, length($2) - length(suffix) + 1) == suffix { print $2 }' \
        "$scratch/checksums.txt")
    # Reject multiple matches and unsafe names before constructing a URL or path.
    case "$asset" in ''|*[!0-9A-Za-z._+-]*) fail 'Missing or ambiguous archive in checksums.txt' ;; esac
    asset_version=${asset#wwss_}
    asset_version=${asset_version%_${goos}_${arch}.tar.gz}
    case "$asset_version" in ''|*[!0-9A-Za-z.+-]*) fail 'Invalid archive version' ;; esac
    if [ "$version" != latest ] && [ "$asset_version" != "$version" ]; then
        fail 'The manifest version does not match the requested release'
    fi
    # Pin the archive URL to the manifest's version, even if latest changes now.
    download "$release_root/download/v$asset_version/$asset" "$scratch/$asset"
    expected=$(awk -v name="$asset" '$2 == name { print tolower($1) }' "$scratch/checksums.txt")
    [ "${#expected}" -eq 64 ] || fail 'Invalid SHA-256 checksum'
    case "$expected" in *[!0-9a-f]*) fail 'Invalid SHA-256 checksum' ;; esac
    if [ "$hash_tool" = sha256sum ]; then
        actual=$(sha256sum "$scratch/$asset" | awk '{ print $1 }')
    else
        actual=$(shasum -a 256 "$scratch/$asset" | awk '{ print $1 }')
    fi
    [ "$actual" = "$expected" ] || fail 'Checksum mismatch; existing installation was not changed'

    mkdir "$scratch/payload"
    tar -xzf "$scratch/$asset" -C "$scratch/payload" \
        wwss LICENSE THIRD_PARTY_NOTICES README.md docs/KNOWN_ISSUES.md docs/RELEASING.md
    chmod 0755 "$scratch/payload/wwss"
    "$scratch/payload/wwss" --help >/dev/null || fail 'The downloaded binary cannot run on this operating system'

    bin_dir=$HOME/.local/bin
    data_dir=$HOME/.local/share/wwss
    mkdir -p "$bin_dir" "$data_dir/docs"
    staged_binary=$(mktemp "$bin_dir/.wwss-install.XXXXXX")
    cp "$scratch/payload/wwss" "$staged_binary"
    chmod 0755 "$staged_binary"
    for file in LICENSE THIRD_PARTY_NOTICES README.md; do
        cp "$scratch/payload/$file" "$data_dir/$file"
    done
    cp "$scratch/payload/docs/KNOWN_ISSUES.md" "$scratch/payload/docs/RELEASING.md" "$data_dir/docs/"
    mv -f "$staged_binary" "$bin_dir/wwss"
    staged_binary=
    printf 'v%s\n' "$asset_version" > "$data_dir/version.txt"

    case "${SHELL:-/bin/sh}" in
        */zsh)
            add_path_to_profile "${ZDOTDIR:-$HOME}/.zshrc"
            ;;
        */bash)
            add_path_to_profile "$HOME/.bashrc"
            if [ -f "$HOME/.bash_profile" ]; then
                add_path_to_profile "$HOME/.bash_profile"
            elif [ -f "$HOME/.bash_login" ]; then
                add_path_to_profile "$HOME/.bash_login"
            else
                add_path_to_profile "$HOME/.profile"
            fi
            ;;
        *) add_path_to_profile "$HOME/.profile" ;;
    esac
    printf 'Installed wwss v%s at %s/wwss\n' "$asset_version" "$bin_dir"
    printf 'Saved devices were preserved. Run: export PATH="$HOME/.local/bin:$PATH"\n'
    printf 'Then run: wwss --help\n'
}

main "$@"
