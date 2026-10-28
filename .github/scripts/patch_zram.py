#!/usr/bin/env python3
"""
Patch Linux kernel zram driver (zram_drv.c) to enforce 4GB disksize
and ZSTD compression against vendor init / fstab overrides.
"""
import os
import re
import sys

TARGET_FILES = [
    "common/drivers/block/zram/zram_drv.c",
    "drivers/block/zram/zram_drv.c"
]

def patch_zram_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    patched = False

    # 1. Enforce ZSTD compression algorithm against vendor downgrades
    pattern_comp = r'(static\s+ssize_t\s+comp_algorithm_store\s*\([^)]+\)\s*\{[\s\S]*?struct\s+zram\s*\*zram\s*=\s*dev_to_zram\(dev\);)'
    if re.search(pattern_comp, content):
        if 'buf = "zstd";' not in content:
            replacement = (
                r'\1\n'
                r'#if defined(CONFIG_ZRAM_DEF_COMP_ZSTD) || IS_ENABLED(CONFIG_ZRAM_DEF_COMP_ZSTD)\n'
                r'\tbuf = "zstd";\n'
                r'#endif'
            )
            content = re.sub(pattern_comp, replacement, content, count=1)
            print(f"[+] Enforced ZSTD in {path}")
            patched = True
        else:
            print(f"[*] ZSTD already enforced in {path}")

    # 2. Enforce minimum 4GB disksize (4294967296 bytes)
    pattern_disk = r'(static\s+ssize_t\s+disksize_store\s*\([^)]+\)\s*\{[\s\S]*?disksize\s*=\s*memparse\(buf,\s*&end\);)'
    pattern_disk_alt = r'(static\s+ssize_t\s+disksize_store\s*\([^)]+\)\s*\{[\s\S]*?disksize\s*=\s*memparse\(buf,\s*NULL\);)'

    if 'if (disksize > 0 && disksize < 4ULL * 1024 * 1024 * 1024)' in content or 'if (disksize < 4ULL * 1024 * 1024 * 1024)' in content:
        print(f"[*] 4GB disksize already enforced in {path}")
    elif re.search(pattern_disk, content):
        replacement = (
            r'\1\n'
            r'\tif (disksize > 0 && disksize < 4ULL * 1024 * 1024 * 1024)\n'
            r'\t\tdisksize = 4ULL * 1024 * 1024 * 1024;'
        )
        content = re.sub(pattern_disk, replacement, content, count=1)
        print(f"[+] Enforced 4GB minimum disksize in {path}")
        patched = True
    elif re.search(pattern_disk_alt, content):
        replacement = (
            r'\1\n'
            r'\tif (disksize > 0 && disksize < 4ULL * 1024 * 1024 * 1024)\n'
            r'\t\tdisksize = 4ULL * 1024 * 1024 * 1024;'
        )
        content = re.sub(pattern_disk_alt, replacement, content, count=1)
        print(f"[+] Enforced 4GB minimum disksize (alt) in {path}")
        patched = True
    else:
        print(f"[!] Warning: disksize_store pattern not matched in {path}", file=sys.stderr)

    if patched:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return True

def main():
    found_any = False
    for p in TARGET_FILES:
        if patch_zram_file(p):
            found_any = True

    if not found_any:
        # Check current working directory or subdirectories
        for root, _, files in os.walk("."):
            if "zram_drv.c" in files:
                full_path = os.path.join(root, "zram_drv.c")
                if patch_zram_file(full_path):
                    found_any = True

    if not found_any:
        print("ERROR: Could not locate zram_drv.c to patch", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
