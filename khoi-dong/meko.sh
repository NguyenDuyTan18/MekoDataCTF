#!/usr/bin/env bash
# Bo bat/tat MekoDataCTF tren Linux. Dung: ./meko.sh <lenh>  (xem: ./meko.sh --help)
cd "$(dirname "$0")"
exec python3 meko.py "$@"
