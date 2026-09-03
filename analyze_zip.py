import zipfile
import csv
import io
import json
import os

zip_path = r"c:\Users\S.MANOJ\Desktop\New folder\pokemon_tcg_cards_split.zip"

print(f"Opening zip: {zip_path}")
with zipfile.ZipFile(zip_path, 'r') as z:
    for name in z.namelist():
        print(f"\n==================== {name} ====================")
        raw_bytes = z.read(name)
        text = raw_bytes.decode('utf-8', errors='replace')
        reader = list(csv.DictReader(io.StringIO(text)))
        print(f"Total Rows: {len(reader)}")
        if reader:
            print("Fields:", list(reader[0].keys()))
            for i, r in enumerate(reader[:3]):
                print(f"Sample {i+1}:")
                for k, v in r.items():
                    if v:
                        print(f"  {k}: {v}")

print("\nDone analysis!")
