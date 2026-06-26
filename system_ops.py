import ctypes
import json
import os
import platform
import subprocess

from profiles import PROFILE_BY_ID, PROFILES
from registry_ops import apply_tweak, get_tweak_states
from services_ops import apply_service

STARTUP_BACKUP = os.path.join(
    os.environ.get("APPDATA", "."), "OnyProtect", "startup_backup.json"
)

STARTUP_ID_MAP = {}


def _startup_safe_id(raw_id):
    import hashlib
    safe = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
    STARTUP_ID_MAP[safe] = raw_id
    return safe


STARTUP_LOCATIONS = [
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
]


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_powershell(script, timeout=15):
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return False, "", str(exc)


def get_system_info():
    admin = _is_admin()
    os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
    arch = platform.machine()

    defender_on = None
    firewall_on = None
    uac_level = None
    secure_boot = None

    ok, out, _ = _run_powershell(
        "(Get-MpComputerStatus).RealTimeProtectionEnabled"
    )
    if ok and out:
        defender_on = out.lower() == "true"

    ok, out, _ = _run_powershell(
        "(Get-NetFirewallProfile -Profile Domain,Private,Public | "
        "Where-Object {$_.Enabled -eq $false}).Count -eq 0"
    )
    if ok and out:
        firewall_on = out.lower() == "true"

    ok, out, _ = _run_powershell(
        "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System').EnableLUA"
    )
    if ok and out.isdigit():
        uac_level = int(out)

    ok, out, _ = _run_powershell(
        "Confirm-SecureBootUEFI -ErrorAction SilentlyContinue"
    )
    if ok:
        secure_boot = out.lower() == "true"

    all_tweaks = get_tweak_states()
    enabled_count = sum(1 for t in all_tweaks if t.get("enabled"))
    total = len(all_tweaks)
    score = round((enabled_count / total) * 100) if total else 0

    return {
        "os": os_info,
        "arch": arch,
        "admin": admin,
        "defender": defender_on,
        "firewall": firewall_on,
        "uac": uac_level,
        "secure_boot": secure_boot,
        "hardening_score": score,
        "tweaks_enabled": enabled_count,
        "tweaks_total": total,
    }


def get_profiles():
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "info": p["info"],
            "level": p["level"],
            "registry_count": len(p["registry"]),
            "services_count": len(p["services"]),
        }
        for p in PROFILES
    ]


def create_restore_point(description="OnyProtect restore point"):
    if not _is_admin():
        return {
            "success": False,
            "message": "Run OnyProtect as Administrator to create restore points",
        }

    description = str(description or "").strip() or "OnyProtect restore point"
    description = description[:100]
    ps_description = description.replace("'", "''")

    ok, out, err = _run_powershell(
        (
            f"Checkpoint-Computer -Description '{ps_description}' "
            "-RestorePointType 'MODIFY_SETTINGS'"
        ),
        timeout=120,
    )
    if ok:
        return {
            "success": True,
            "message": f"Restore point created: {description}",
        }

    detail = err or out or "Restore point creation failed"
    if "System Restore" in detail or "disabled" in detail:
        detail = "System Protection may be disabled for this drive"
    elif "frequency" in detail.lower():
        detail = "Windows is limiting restore point creation frequency"

    return {"success": False, "message": detail}


def apply_profile(profile_id):
    profile = PROFILE_BY_ID.get(profile_id)
    if not profile:
        return {"success": False, "message": "Unknown profile"}

    applied = 0
    failed = []

    for tweak_id in profile["registry"]:
        result = apply_tweak(tweak_id, True)
        if result["success"]:
            applied += 1
        else:
            failed.append(f"{tweak_id}: {result['message']}")

    for service_id in profile["services"]:
        result = apply_service(service_id, True)
        if result["success"]:
            applied += 1
        else:
            failed.append(f"{service_id}: {result['message']}")

    total = len(profile["registry"]) + len(profile["services"])
    msg = f"{profile['name']}: {applied}/{total} applied"
    if failed:
        msg += f" ({len(failed)} failed — run as Administrator)"

    return {
        "success": applied > 0,
        "message": msg,
        "applied": applied,
        "total": total,
        "failed": failed[:5],
    }


def _load_startup_backup():
    if os.path.exists(STARTUP_BACKUP):
        try:
            with open(STARTUP_BACKUP, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_startup_backup(data):
    os.makedirs(os.path.dirname(STARTUP_BACKUP), exist_ok=True)
    with open(STARTUP_BACKUP, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_startup_items():
    import winreg

    items = []
    backup = _load_startup_backup()
    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}

    for hive_name, path in STARTUP_LOCATIONS:
        hive = hives[hive_name]
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        item_id = f"{hive_name}\\{path}\\{name}"
                        disabled = item_id in backup
                        items.append(
                            {
                                "id": _startup_safe_id(item_id),
                                "name": name,
                                "info": str(value)[:200],
                                "enabled": not disabled,
                                "available": True,
                            }
                        )
                        i += 1
                    except OSError:
                        break
        except OSError:
            continue

    startup_folder = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    if os.path.isdir(startup_folder):
        for fname in os.listdir(startup_folder):
            fpath = os.path.join(startup_folder, fname)
            if fname.endswith((".lnk", ".bat", ".cmd", ".exe", ".vbs")):
                item_id = f"FOLDER\\{fpath}"
                disabled = item_id in backup
                items.append(
                    {
                        "id": _startup_safe_id(item_id),
                        "name": fname,
                        "info": f"Startup folder: {fpath}",
                        "enabled": not disabled,
                        "available": True,
                    }
                )

    return items


def set_startup_item(safe_id, disable):
    import winreg

    item_id = STARTUP_ID_MAP.get(safe_id, safe_id)
    backup = _load_startup_backup()

    if disable:
        if item_id.startswith("FOLDER\\"):
            fpath = item_id[7:]
            disabled_path = fpath + ".onyprotect_disabled"
            try:
                if os.path.exists(fpath):
                    os.rename(fpath, disabled_path)
                    backup[item_id] = {"path": fpath, "disabled_path": disabled_path}
                    _save_startup_backup(backup)
                    return {"success": True, "message": f"Disabled {os.path.basename(fpath)}"}
            except OSError as exc:
                return {"success": False, "message": str(exc)}
            return {"success": False, "message": "File not found"}

        parts = item_id.split("\\", 2)
        if len(parts) < 3:
            return {"success": False, "message": "Invalid item ID"}

        hive_name, path, name = parts[0], parts[1], parts[2]
        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        hive = hives.get(hive_name)
        if not hive:
            return {"success": False, "message": "Invalid hive"}

        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS) as key:
                value, reg_type = winreg.QueryValueEx(key, name)
                winreg.DeleteValue(key, name)
                backup[item_id] = {
                    "hive": hive_name,
                    "path": path,
                    "name": name,
                    "value": value,
                    "type": reg_type,
                }
                _save_startup_backup(backup)
                return {"success": True, "message": f"Disabled {name}"}
        except OSError as exc:
            return {"success": False, "message": str(exc)}
    else:
        if item_id not in backup:
            return {"success": True, "message": "Already enabled"}

        entry = backup.pop(item_id)

        if item_id.startswith("FOLDER\\"):
            try:
                os.rename(entry["disabled_path"], entry["path"])
                _save_startup_backup(backup)
                return {"success": True, "message": "Restored startup item"}
            except OSError as exc:
                return {"success": False, "message": str(exc)}

        import winreg

        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        hive = hives[entry["hive"]]
        try:
            with winreg.CreateKey(hive, entry["path"]) as key:
                winreg.SetValueEx(
                    key, entry["name"], 0, entry["type"], entry["value"]
                )
            _save_startup_backup(backup)
            return {"success": True, "message": f"Restored {entry['name']}"}
        except OSError as exc:
            return {"success": False, "message": str(exc)}
