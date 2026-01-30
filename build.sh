#!/usr/bin/env bash
set -e

git clone --depth=1 https://github.com/osfans/MCPDict.git
(cd MCPDict/tools/ && python make.py)
mv MCPDict/app/src/main/assets/databases/mcpdict.db .
rm -rf MCPDict/
python update_db.py
mv mcpdict.db ../server/
