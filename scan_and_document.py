#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def proxmox_get(cfg: dict[str, Any], api_path: str) -> Any:
    base = cfg["proxmox_url"].rstrip("/")
    token_id = cfg["proxmox_token_id"]
    token_secret = cfg["proxmox_token_secret"]
    verify_tls = bool(cfg.get("verify_tls", False))
    headers = {"Authorization": f"PVEAPIToken={token_id}={token_secret}"}
    url = f"{base}/api2/json{api_path}"
    r = requests.get(url, headers=headers, timeout=20, verify=verify_tls)
    r.raise_for_status()
    return r.json()["data"]


def fmt_mb_to_gb(mb: int | float | None) -> str:
    if not mb:
        return "0 GB"
    return f"{mb / 1024:.1f} GB"


def write_markdown(cfg: dict[str, Any], nodes: list[dict[str, Any]], out_file: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append("# Proxmox Inventory")
    lines.append("")
    lines.append(f"_Generated: {now}_")
    lines.append("")

    total_items = 0
    for node in nodes:
        node_name = node["node"]
        lines.append(f"## Node: {node_name}")
        lines.append("")

        vms = proxmox_get(cfg, f"/nodes/{node_name}/qemu")
        lxcs = proxmox_get(cfg, f"/nodes/{node_name}/lxc")
        items = sorted(vms + lxcs, key=lambda x: (x.get("type", ""), x.get("vmid", 0)))
        total_items += len(items)

        if not items:
            lines.append("No VMs/LXCs found on this node.")
            lines.append("")
            continue

        lines.append("| Type | VMID | Name | Status | CPU | RAM | Disk |")
        lines.append("|---|---:|---|---|---:|---:|---:|")
        for it in items:
            typ = str(it.get("type", "unknown")).upper()
            vmid = it.get("vmid", "")
            name = it.get("name", "(no name)")
            status = it.get("status", "unknown")
            cpus = it.get("cpus", it.get("maxcpu", ""))
            ram_mb = (it.get("maxmem") or 0) / (1024 * 1024)
            disk_gb = (it.get("maxdisk") or 0) / (1024 * 1024 * 1024)
            lines.append(
                f"| {typ} | {vmid} | {name} | {status} | {cpus} | {fmt_mb_to_gb(ram_mb)} | {disk_gb:.1f} GB |"
            )

        lines.append("")

    lines.append(f"Total guests discovered: **{total_items}**")
    lines.append("")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cfg_path = Path("config.json")
    if not cfg_path.exists():
        raise SystemExit("Missing config.json. Create it first.")

    cfg = load_config(cfg_path)
    nodes = proxmox_get(cfg, "/nodes")
    out_file = Path(cfg.get("output_file", "output/proxmox_inventory.md"))
    write_markdown(cfg, nodes, out_file)
    print(f"Wrote: {out_file}")


if __name__ == "__main__":
    main()
