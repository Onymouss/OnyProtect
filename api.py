"""Python bridge for the web UI."""

import webbrowser

from downloads import DOWNLOADS, DOWNLOAD_BY_ID
from registry_ops import (
    apply_tweak,
    get_registry_backups,
    get_tweak_states,
    restore_original_tweak,
)
from services_ops import (
    apply_service,
    get_all_service_states,
    get_service_backups,
    restore_original_service,
)
from system_ops import (
    apply_profile,
    create_restore_point,
    get_profiles,
    get_startup_items,
    get_system_info,
    set_startup_item,
)


class Api:
    def get_version(self):
        return "0.3.0"

    def ping(self):
        return "ok"

    def get_registry_tweaks(self, category="security"):
        return get_tweak_states(category)

    def set_registry_tweak(self, tweak_id, enabled):
        return apply_tweak(tweak_id, bool(enabled))

    def get_services(self):
        return get_all_service_states()

    def set_service(self, service_id, enabled):
        return apply_service(service_id, bool(enabled))

    def get_startup_items(self):
        return get_startup_items()

    def set_startup_item(self, item_id, disable):
        return set_startup_item(item_id, bool(disable))

    def get_profiles(self):
        return get_profiles()

    def apply_profile(self, profile_id):
        return apply_profile(profile_id)

    def create_restore_point(self, description):
        return create_restore_point(description)

    def get_recovery_items(self):
        return get_registry_backups() + get_service_backups()

    def restore_recovery_item(self, item_type, item_id):
        if item_type == "registry":
            return restore_original_tweak(item_id)
        if item_type == "service":
            return restore_original_service(item_id)
        return {"success": False, "message": "Unknown recovery item"}

    def get_system_info(self):
        return get_system_info()

    def get_downloads(self):
        return [
            {
                "id": d["id"],
                "name": d["name"],
                "desc": d["desc"],
                "category": d["category"],
                "url": d["url"],
            }
            for d in DOWNLOADS
        ]

    def open_download(self, download_id):
        item = DOWNLOAD_BY_ID.get(download_id)
        if not item:
            return {"success": False, "message": "Unknown download"}
        try:
            webbrowser.open(item["url"])
            return {"success": True, "message": f"Opened {item['name']} in browser"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}
