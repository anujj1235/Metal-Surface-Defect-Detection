from pathlib import Path
from PIL import Image
import hashlib

DATASET = Path(r"C:\Metal_Surface_Detection\Industrial_Metal_Surface_Dataset")

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

total = 0
valid = 0
corrupt = 0
duplicates = 0
hashes = {}

print("=" * 70)
print("FINAL DATASET VERIFICATION")
print("=" * 70)

for metal_dir in sorted(DATASET.iterdir()):
    if not metal_dir.is_dir():
        continue

    print(f"\n{metal_dir.name}:")

    for condition_dir in sorted(metal_dir.iterdir()):
        if not condition_dir.is_dir():
            continue

        files = [
            f for f in condition_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
        ]

        folder_total = 0
        folder_valid = 0

        for file in files:
            total += 1
            folder_total += 1

            try:
                with Image.open(file) as img:
                    img.verify()

                with Image.open(file) as img:
                    img.load()

                valid += 1
                folder_valid += 1

                # Duplicate check
                h = hashlib.sha256(file.read_bytes()).hexdigest()

                if h in hashes:
                    duplicates += 1
                else:
                    hashes[h] = str(file)

            except Exception:
                corrupt += 1

        print(
            f"  {condition_dir.name:<12} "
            f"{folder_valid:>4} images"
        )

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Total image files : {total}")
print(f"Valid images      : {valid}")
print(f"Corrupt images    : {corrupt}")
print(f"Duplicate hashes  : {duplicates}")
print(f"Unique images     : {len(hashes)}")

print("=" * 70)

if corrupt == 0 and duplicates == 0:
    print("STATUS: DATASET IS CLEAN")
elif corrupt > 0:
    print("STATUS: CORRUPT IMAGES FOUND - DO NOT TRAIN YET")
elif duplicates > 0:
    print("STATUS: DUPLICATES STILL EXIST - DO NOT TRAIN YET")
else:
    print("STATUS: REVIEW REQUIRED")