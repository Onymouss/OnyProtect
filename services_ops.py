import csv
import io
import json
import os
import subprocess

from services_tweaks import SERVICE_BY_ID, SERVICE_TWEAKS

START_TYPE_DISABLED = "DISABLED"

_SERVICE_CACHE = None

SERVICE_BACKUP = os.path.join(
    os.environ.get("APPDATA", "."), "OnyProtect", "service_backup.json"
)


def _load_backup():
    if os.path.exists(SERVICE_BACKUP):
        try:
            with open(SERVICE_BACKUP, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_backup(data):
    os.makedirs(os.path.dirname(SERVICE_BACKUP), exist_ok=True)
    with open(SERVICE_BACKUP, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _service_names_list():
    return ",".join(f"'{s['service']}'" for s in SERVICE_TWEAKS)


def _load_service_cache():
    global _SERVICE_CACHE
    if _SERVICE_CACHE is not None:
        return _SERVICE_CACHE

    cache = {}
    names = _service_names_list()
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Service -Name @({names}) -ErrorAction SilentlyContinue | "
                "Select-Object Name,StartType | ConvertTo-Csv -NoTypeInformation",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0 and result.stdout.strip():
            reader = csv.reader(io.StringIO(result.stdout.strip()))
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    cache[row[0].strip().lower()] = row[1].strip().lower()
    except (subprocess.SubprocessError, OSError):
        pass

    _SERVICE_CACHE = cache
    return cache


def _run_sc(args):
    result = subprocess.run(
        f"sc {args}",
        capture_output=True,
        text=True,
        shell=True,
    )
    return result.returncode, result.stdout + result.stderr


def _service_exists(service_name):
    cache = _load_service_cache()
    if cache:
        return service_name.lower() in cache
    code, _ = _run_sc(f"qc {service_name}")
    return code == 0


def is_service_hardened(service_def):
    cache = _load_service_cache()
    name = service_def["service"]
    mode = cache.get(name.lower())
    if mode is None:
        return False
    return mode == "disabled"


def apply_service(service_id, harden):
    global _SERVICE_CACHE
    _SERVICE_CACHE = None

    service_def = SERVICE_BY_ID.get(service_id)
    if not service_def:
        return {"success": False, "message": f"Unknown service: {service_id}"}

    name = service_def["service"]
    if not _service_exists(name):
        return {"success": False, "message": f"Service not found on this system: {name}"}

    backup = _load_backup()
    cache = _load_service_cache()
    if service_id not in backup:
        backup[service_id] = {
            "service": name,
            "start_type": cache.get(name.lower(), service_def.get("default_start", "manual")),
        }
        _save_backup(backup)

    if harden:
        _run_sc(f"stop {name}")
        code, output = _run_sc(f'config {name} start= disabled')
    else:
        default = service_def.get("default_start", "demand")
        code, output = _run_sc(f"config {name} start= {default}")
        if code == 0 and default in ("auto", "demand"):
            _run_sc(f"start {name}")

    if code != 0:
        if "Access is denied" in output or "5" in output:
            return {
                "success": False,
                "message": "Access denied — run OnyProtect as Administrator",
            }
        return {"success": False, "message": output.strip() or "Service command failed"}

    action = "disabled" if harden else "restored"
    return {"success": True, "message": f"{service_def['name']} {action}"}


def restore_original_service(service_id):
    global _SERVICE_CACHE
    _SERVICE_CACHE = None

    service_def = SERVICE_BY_ID.get(service_id)
    if not service_def:
        return {"success": False, "message": f"Unknown service: {service_id}"}

    backup = _load_backup()
    entry = backup.get(service_id)
    if not entry:
        return {"success": False, "message": "No backup found for this service"}

    name = entry["service"]
    if not _service_exists(name):
        return {"success": False, "message": f"Service not found on this system: {name}"}

    start_type = entry.get("start_type") or service_def.get("default_start", "manual")
    if start_type == "automatic":
        start_type = "auto"
    elif start_type == "manual":
        start_type = "demand"

    code, output = _run_sc(f"config {name} start= {start_type}")
    if code != 0:
        if "Access is denied" in output or "5" in output:
            return {
                "success": False,
                "message": "Access denied - run OnyProtect as Administrator",
            }
        return {"success": False, "message": output.strip() or "Service restore failed"}

    backup.pop(service_id, None)
    _save_backup(backup)
    return {"success": True, "message": f"Restored original service state for {service_def['name']}"}


def get_all_service_states():
    _load_service_cache()
    results = []
    for service_def in SERVICE_TWEAKS:
        exists = _service_exists(service_def["service"])
        try:
            hardened = is_service_hardened(service_def) if exists else False
            info = service_def["info"]
            if not exists:
                info = f"{info} (not installed on this system)"

            results.append(
                {
                    "id": service_def["id"],
                    "name": service_def["name"],
                    "info": info,
                    "enabled": hardened,
                    "available": exists,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "id": service_def["id"],
                    "name": service_def["name"],
                    "info": service_def["info"],
                    "enabled": False,
                    "available": False,
                    "error": str(exc),
                }
            )
    return results


def get_service_backups():
    backup = _load_backup()
    results = []
    for service_id in sorted(backup):
        service_def = SERVICE_BY_ID.get(service_id)
        entry = backup[service_id]
        results.append(
            {
                "id": service_id,
                "name": service_def["name"] if service_def else service_id,
                "type": "service",
                "detail": f"{entry['service']} start type: {entry.get('start_type', 'unknown')}",
            }
        )
    return results
