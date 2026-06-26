# OnyProtect

OnyProtect is a Windows hardening and OPSEC desktop suite for reviewing and applying security focused system settings. It provides a native desktop interface for registry tweaks, service hardening, startup controls, restore point creation, recovery, and one click hardening profiles.

## Features

| Module | Description |
|--------|-------------|
| Dashboard | Live security posture, hardening score, Defender, firewall, UAC, and Secure Boot status |
| Profiles | One-click Baseline, OPSEC, Maximum OPSEC, Privacy, and Audit profiles |
| Registry | Hardening tweaks for LSA, authentication, RDP, USB, RunAsPPL, and privacy |
| Network | SMB, NTLM, LLMNR, WPAD, CredSSP, and signing requirements |
| Firewall | Windows Firewall policies, logging, and inbound blocking |
| DNS | DNS over HTTPS, leak prevention, and secure resolution settings |
| Privacy | Telemetry, app permissions, tracking, and Edge policies |
| Audit | Process creation logging, credential validation, and log retention |
| Accounts | Lockout policy, password rules, and logon hardening |
| Explorer | File extensions, hidden files, autoplay, and Explorer behavior |
| Services | OPSEC-focused service controls, including telemetry and remote access services |
| Startup | View and disable Run key and startup folder entries |
| Restore Point | Create a Windows restore point before making changes |
| Recovery | Restore original registry and service states saved by OnyProtect |
| Download | Curated privacy and security tool links |

## Requirements

- Windows 10 or 11
- Python 3.10+
- Administrator rights for HKLM registry tweaks, service changes, and restore point creation
- Windows System Protection enabled to create restore points

## Install

```powershell
git clone https://github.com/OnyMouss/OnyProtect.git
cd OnyProtect
pip install -r requirements.txt
python main.py
```

## Usage

1. Launch OnyProtect as Administrator for full functionality.
2. Create a restore point from the Restore Point tab.
3. Check Dashboard for the current hardening score.
4. Apply a Profile for quick deployment, or configure individual tabs.
5. Use Recovery to restore original registry and service states saved by OnyProtect.

## Profiles

| Profile | Risk | Use Case |
|---------|------|----------|
| Baseline | Low | Safe defaults for most workstations |
| Operational Security | Medium | Field laptops and daily OPSEC |
| Maximum OPSEC | High | High-risk environments; may break RDP, USB storage, printing, or app workflows |
| Privacy Focused | Medium | Telemetry and tracking reduction without aggressive network lockdown |
| Audit & Compliance | Medium | Forensic logging and compliance readiness |

## Project Structure

```text
OnyProtect/
  main.py              # Webview launcher
  api.py               # Python to JavaScript bridge
  registry_tweaks.py   # Registry tweak definitions
  registry_ops.py      # Registry read/write and backup recovery
  services_tweaks.py   # Service definitions
  services_ops.py      # Service management and backup recovery
  profiles.py          # Hardening profiles
  system_ops.py        # Dashboard, startup, restore points, profiles
  downloads.py         # App catalog
  web/                 # UI
```
---

## 👥 Credits & Acknowledgements
Developed by [@onymouss](https://www.github.com/Onymouss)

---

## ⚠️ Disclaimer
OnyProtect modifies system-level Windows settings. Review each tweak before applying it. Some changes, especially USB storage disablement, RDP disablement, firewall lockdown, and service hardening, can break workflows. Always test first and keep a known-good recovery path. and This tool is for educational and security research purposes only. It should not be used as a replacement for professional antivirus software. also I used AI to clean up some of my code.

---
## Star ⭐ this repo if you find it useful!
