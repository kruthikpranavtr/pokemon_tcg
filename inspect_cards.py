import zipfile
import csv
import io
import json

zip_path = r"c:\Users\S.MANOJ\Desktop\New folder\pokemon_tcg_cards_split.zip"

with zipfile.ZipFile(zip_path, 'r') as z:
    for name in z.namelist():
        print(f"--- File: {name} ---")
        text = z.read(name).decode('utf-8', errors='replace')
        rows = list(csv.DictReader(io.StringIO(text)))
        print(f"Row count: {len(rows)}")
        if rows:
            for r in rows[:2]:
                print(r)

