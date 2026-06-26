import json
import os
import winreg

from registry_tweaks import REGISTRY_TWEAKS, TWEAK_BY_ID

HIVES = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
}

REG_TYPES = {
    "dword": winreg.REG_DWORD,
    "sz": winreg.REG_SZ,
}

REGISTRY_BACKUP = os.path.join(
    os.environ.get("APPDATA", "."), "OnyProtect", "registry_backup.json"
)


def _load_backup():
    if os.path.exists(REGISTRY_BACKUP):
        try:
            with open(REGISTRY_BACKUP, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_backup(data):
    os.makedirs(os.path.dirname(REGISTRY_BACKUP), exist_ok=True)
    with open(REGISTRY_BACKUP, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _read_value(hive, path, name):
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, name)
            if reg_type == winreg.REG_DWORD:
                return int(value)
            return str(value)
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _write_value(hive, path, name, value_type, value):
    reg_type = REG_TYPES[value_type]
    with winreg.CreateKey(hive, path) as key:
        winreg.SetValueEx(key, name, 0, reg_type, value)


def _delete_value(hive, path, name):
    with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, name)


def _backup_tweak(tweak):
    backup = _load_backup()
    if tweak["id"] in backup:
        return

    hive = HIVES[tweak["hive"]]
    current = _read_value(hive, tweak["path"], tweak["value"])
    backup[tweak["id"]] = {
        "hive": tweak["hive"],
        "path": tweak["path"],
        "value": tweak["value"],
        "value_type": tweak["value_type"],
        "existed": current is not None,
        "original": current,
    }
    _save_backup(backup)


def is_tweak_enabled(tweak):
    hive = HIVES[tweak["hive"]]
    current = _read_value(hive, tweak["path"], tweak["value"])
    target = tweak["on"]

    if current is None:
        return False

    if tweak["value_type"] == "dword":
        return int(current) == int(target)

    return str(current).lower() == str(target).lower()


def apply_tweak(tweak_id, enable):
    tweak = TWEAK_BY_ID.get(tweak_id)
    if not tweak:
        return {"success": False, "message": f"Unknown tweak: {tweak_id}"}

    hive = HIVES[tweak["hive"]]
    value = tweak["on"] if enable else tweak["off"]

    if tweak["value_type"] == "dword":
        value = int(value)

    try:
        _backup_tweak(tweak)
        _write_value(hive, tweak["path"], tweak["value"], tweak["value_type"], value)
        state = "enabled" if enable else "disabled"
        return {"success": True, "message": f"{tweak['name']} {state}"}
    except PermissionError:
        return {
            "success": False,
            "message": "Access denied — run OnyProtect as Administrator for HKLM tweaks",
        }
    except OSError as exc:
        return {"success": False, "message": str(exc)}


def get_tweak_states(category=None):
    results = []
    for tweak in REGISTRY_TWEAKS:
        if category and tweak.get("category") != category:
            continue
        try:
            enabled = is_tweak_enabled(tweak)
            results.append(
                {
                    "id": tweak["id"],
                    "name": tweak["name"],
                    "info": tweak["info"],
                    "enabled": enabled,
                    "category": tweak.get("category", "security"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "id": tweak["id"],
                    "name": tweak["name"],
                    "info": tweak["info"],
                    "enabled": False,
                    "category": tweak.get("category", "security"),
                    "error": str(exc),
                }
            )
    return results


def get_all_tweak_states():
    return get_tweak_states(None)


def restore_original_tweak(tweak_id):
    backup = _load_backup()
    entry = backup.get(tweak_id)
    if not entry:
        return {"success": False, "message": "No backup found for this tweak"}

    hive = HIVES[entry["hive"]]
    try:
        if entry["existed"]:
            value = entry["original"]
            if entry["value_type"] == "dword":
                value = int(value)
            _write_value(
                hive,
                entry["path"],
                entry["value"],
                entry["value_type"],
                value,
            )
        else:
            _delete_value(hive, entry["path"], entry["value"])

        backup.pop(tweak_id, None)
        _save_backup(backup)
        return {"success": True, "message": f"Restored original value for {tweak_id}"}
    except PermissionError:
        return {
            "success": False,
            "message": "Access denied - run OnyProtect as Administrator",
        }
    except FileNotFoundError:
        backup.pop(tweak_id, None)
        _save_backup(backup)
        return {"success": True, "message": f"Original missing value restored for {tweak_id}"}
    except OSError as exc:
        return {"success": False, "message": str(exc)}


def get_registry_backups():
    backup = _load_backup()
    results = []
    for tweak_id in sorted(backup):
        tweak = TWEAK_BY_ID.get(tweak_id)
        entry = backup[tweak_id]
        results.append(
            {
                "id": tweak_id,
                "name": tweak["name"] if tweak else tweak_id,
                "type": "registry",
                "detail": f"{entry['hive']}\\{entry['path']}\\{entry['value']}",
            }
        )
    return results

