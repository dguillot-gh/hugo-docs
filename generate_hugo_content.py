#!/usr/bin/env python3
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
import requests

CFG = Path("/root/hugo-docs/config.json")
SITE = Path("/root/homelab-docs")
CONTENT = SITE / "content"

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower().strip()).strip("-") or "item"

def load_cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))

def pve_get(cfg, path):
    base = cfg["proxmox_url"].rstrip("/")
    h = {"Authorization": f'PVEAPIToken={cfg["proxmox_token_id"]}={cfg["proxmox_token_secret"]}'}
    r = requests.get(f"{base}/api2/json{path}", headers=h, timeout=30, verify=cfg.get("verify_tls", False))
    r.raise_for_status()
    return r.json()["data"]

def gb(v): return round((v or 0)/(1024**3), 2)
def pct(used,total): return round((used/total)*100,1) if total else 0.0

def write_node_page(nodes_dir: Path, node: str, status: dict, storage: list, now: str):
    mem = status.get("memory", {})
    rootfs = status.get("rootfs", {})
    cpuinfo = status.get("cpuinfo", {})
    loadavg = status.get("loadavg", [0,0,0])

    lines = [
        "---",
        f'title: "Node {node}"',
        f'node: "{node}"',
        f'updated: "{now}"',
        "---",
        "",
        f"# Node {node}",
        "",
        "## Health Snapshot",
        f"- CPU Usage: **{round((status.get('cpu',0)*100),1)}%**",
        f"- Load Avg (1/5/15): **{loadavg[0]} / {loadavg[1]} / {loadavg[2]}**",
        f"- Memory: **{gb(mem.get('used',0))} / {gb(mem.get('total',0))} GB** ({pct(mem.get('used',0), mem.get('total',0))}%)",
        f"- Root FS: **{gb(rootfs.get('used',0))} / {gb(rootfs.get('total',0))} GB** ({pct(rootfs.get('used',0), rootfs.get('total',0))}%)",
        "",
        "## Hardware",
        f"- CPU Model: **{cpuinfo.get('model','n/a')}**",
        f"- Cores / Sockets: **{cpuinfo.get('cores','?')} / {cpuinfo.get('sockets','?')}**",
        f"- Kernel: **{status.get('kversion','n/a')}**",
        "",
        "## Storage Pools",
        "| Name | Type | Total | Used | Free |",
        "|---|---|---:|---:|---:|",
    ]

    for s in storage:
        lines.append(
            f"| {s.get('storage','?')} | {s.get('type','?')} | {gb(s.get('total',0))} GB | {gb(s.get('used',0))} GB | {gb(s.get('avail',0))} GB |"
        )

    lines += [
        "",
        "## Debug",
        f"- [Raw node data](/nodes/{slug(node)}-raw/)",
    ]
    (nodes_dir / f"{slug(node)}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    raw = [
        "---",
        f'title: "Node {node} Raw Data"',
        "---",
        "## Status JSON",
        "```json",
        json.dumps(status, indent=2, sort_keys=True),
        "```",
        "",
        "## Storage JSON",
        "```json",
        json.dumps(storage, indent=2, sort_keys=True),
        "```",
    ]
    (nodes_dir / f"{slug(node)}-raw.md").write_text("\n".join(raw) + "\n", encoding="utf-8")

def main():
    cfg = load_cfg()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    nodes_dir = CONTENT / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    nodes = pve_get(cfg, "/nodes")
    idx = ["---",'title: "Nodes"',"---","# Nodes",""]

    for n in nodes:
        node = n["node"]
        status = pve_get(cfg, f"/nodes/{node}/status")
        storage = pve_get(cfg, f"/nodes/{node}/storage")
        write_node_page(nodes_dir, node, status, storage, now)
        idx.append(f"- [{node}](/nodes/{slug(node)}/)")

    (nodes_dir / "_index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print("Node pages regenerated.")

if __name__ == "__main__":
    main()
