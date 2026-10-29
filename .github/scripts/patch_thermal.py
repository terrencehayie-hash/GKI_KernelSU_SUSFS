#!/usr/bin/env python3
"""
Patch Linux kernel to neutralize Xiaomi mi_thermald and enforce in-kernel
thermal management (prevent screen dimming, lock refresh rate, gaming-tuned cooling).
"""
import os
import re
import sys

EXEC_FILES = [
    "common/fs/exec.c",
    "fs/exec.c"
]

THERMAL_FILES = [
    "common/drivers/thermal/step_wise.c",
    "drivers/thermal/step_wise.c"
]

def patch_exec_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if 'strstr(bprm->filename, "mi_thermald")' in content:
        print(f"[*] mi_thermald block already present in {path}")
        return True

    # Pattern: in bprm_execve after local variable declarations (int retval;)
    pattern = r'(static\s+int\s+bprm_execve\s*\([^)]+\)\s*\{[\s\S]*?int\s+retval;)'
    if re.search(pattern, content):
        replacement = (
            r'\1\n'
            r'\t/* Block Xiaomi mi_thermald from aggressive throttling, screen dimming, and FPS capping */\n'
            r'\tif (bprm->filename && strstr(bprm->filename, "mi_thermald")) {\n'
            r'\t\tpr_info("thermal: blocked execution of %s (in-kernel thermal active)\\n", bprm->filename);\n'
            r'\t\treturn -ENOENT;\n'
            r'\t}'
        )
        content = re.sub(pattern, replacement, content, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Successfully blocked mi_thermald in {path}")
        return True

    print(f"[!] Warning: bprm_execve pattern not matched in {path}", file=sys.stderr)
    return False

def patch_thermal_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if 'Prevent thermal throttling from dimming display brightness' in content:
        print(f"[*] Display thermal dimming prevention already present in {path}")
        return True

    # Pattern: after instance->target = get_target_state(instance, trend, throttle);
    pattern = r'(\binstance->target\s*=\s*get_target_state\([^)]+\);)'
    if re.search(pattern, content):
        replacement = (
            r'\1\n'
            r'\t\t/* Prevent thermal throttling from dimming display brightness or backlight */\n'
            r'\t\tif (instance->cdev && instance->cdev->type &&\n'
            r'\t\t    (strstr(instance->cdev->type, "brightness") || strstr(instance->cdev->type, "backlight")))\n'
            r'\t\t\tinstance->target = 0;'
        )
        content = re.sub(pattern, replacement, content, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Successfully protected display from thermal dimming in {path}")
        return True

    print(f"[!] Warning: step_wise pattern not matched in {path}", file=sys.stderr)
    return False

def main():
    exec_patched = False
    for p in EXEC_FILES:
        if patch_exec_file(p):
            exec_patched = True

    if not exec_patched:
        for root, _, files in os.walk("."):
            if "exec.c" in files:
                full_path = os.path.join(root, "exec.c")
                if patch_exec_file(full_path):
                    exec_patched = True
                    break

    if not exec_patched:
        print("ERROR: Could not locate fs/exec.c to patch", file=sys.stderr)
        sys.exit(1)

    thermal_patched = False
    for p in THERMAL_FILES:
        if patch_thermal_file(p):
            thermal_patched = True

    if not thermal_patched:
        for root, _, files in os.walk("."):
            if "step_wise.c" in files:
                full_path = os.path.join(root, "step_wise.c")
                if patch_thermal_file(full_path):
                    thermal_patched = True
                    break

    if not thermal_patched:
        print("ERROR: Could not locate drivers/thermal/step_wise.c to patch", file=sys.stderr)
        sys.exit(1)

    print("[+] Kernel thermal optimization successfully applied!")

if __name__ == "__main__":
    main()
