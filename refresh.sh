#!/usr/bin/env bash
set -e
cd /root/hugo-docs
source .venv/bin/activate
python3 generate_hugo_content.py
cd /root/homelab-docs
hugo
