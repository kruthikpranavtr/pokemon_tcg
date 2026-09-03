import os
import zipfile
import csv
import io
import json

print("=== CHECKING FILES IN PARENT & WORKSPACE ===")
cwd = os.getcwd()
parent = os.path.dirname(cwd)
print(f"CWD: {cwd}")
print(f"Parent: {parent}")

try:
    for root, dirs, files in os.walk(parent):
        for f in files:
            if f.endswith(('.zip', '.csv', '.json', '.parquet', '.tsv')):
                full_p = os.path.join(root, f)
                sz = os.path.getsize(full_p)
                print(f"File: {full_p} ({sz} bytes)")
except Exception as e:
    print(f"Walk error: {e}")
