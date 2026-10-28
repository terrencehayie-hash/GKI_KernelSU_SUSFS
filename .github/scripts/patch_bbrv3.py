#!/usr/bin/env python3
"""
Safely adjust net/ipv4/sysctl_net_ipv4.c for 5.15 LTS (5.15.220+)
so that the BBRv3 backport patch applies cleanly without context rejects.
"""
import os
import sys

TARGET_PATHS = [
    "net/ipv4/sysctl_net_ipv4.c",
    "common/net/ipv4/sysctl_net_ipv4.c"
]

def patch_sysctl(path: str) -> bool:
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    target_needle = "static int tcp_min_rcvbuf = 4096;\n\n"
    anchor = "static u32 u32_max_div_HZ = UINT_MAX / HZ;"

    if target_needle in content and anchor in content:
        # Move tcp_min_rcvbuf above u32_max_div_HZ to align context with BBRv3 patch
        content = content.replace(target_needle, "")
        content = content.replace(anchor, f"static int tcp_min_rcvbuf = 4096;\n{anchor}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Successfully adjusted {path} for 5.15 LTS BBRv3 patch")
        return True
    elif "static int tcp_min_rcvbuf = 4096;" not in content:
        print(f"[*] Older 5.15 detected: tcp_min_rcvbuf not present in {path}, no adjustment needed")
        return True
    else:
        print(f"[*] {path} already adjusted or matches expected structure")
        return True

def main():
    found = False
    for p in TARGET_PATHS:
        if patch_sysctl(p):
            found = True
            break

    if not found:
        # Check recursively in case directory structure differs
        for root, _, files in os.walk("."):
            if "sysctl_net_ipv4.c" in files:
                full_path = os.path.join(root, "sysctl_net_ipv4.c")
                if patch_sysctl(full_path):
                    found = True
                    break

    if not found:
        print("ERROR: Could not locate sysctl_net_ipv4.c to adjust for BBRv3", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
