from pathlib import Path
from PIL import Image

# ============================================================
# METAL DEFECT DATASET CHECKER
# ============================================================

DATASET_DIR = Path(
    "dataset/Industrial_Metal_Surface_Dataset_COMPACT_FINAL"
)

# Exact CURRENT dataset structure
classes = {
    "steel_defective": DATASET_DIR / "steel" / "defective",
    "iron_defective": DATASET_DIR / "iron" / "Defective",
    "aluminium_good": DATASET_DIR / "aluminium" / "good",
    "aluminium_defective": DATASET_DIR / "aluminium" / "defective",
}

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

print("=" * 70)
print("        INDUSTRIAL METAL DEFECT DATASET CHECK")
print("=" * 70)

print("\nDataset location:")
print(DATASET_DIR.resolve())

print("\nExpected classes:")
for class_name in classes:
    print(f"  - {class_name}")

print("=" * 70)

total_images = 0
total_valid = 0
total_invalid = 0
total_other_files = 0


# ============================================================
# CHECK EACH CLASS
# ============================================================

for class_name, folder in classes.items():

    print("\n" + "-" * 70)
    print(f"Checking class: {class_name}")
    print(f"Folder: {folder.resolve()}")
    print("-" * 70)

    if not folder.exists():
        print("ERROR: Folder does not exist!")
        continue

    image_files = [
        path
        for path in folder.rglob("*")
        if path.is_file()
        and path.suffix.lower() in VALID_EXTENSIONS
    ]

    all_files = [
        path
        for path in folder.rglob("*")
        if path.is_file()
    ]

    other_files = len(all_files) - len(image_files)

    valid_count = 0
    invalid_count = 0

    for image_path in image_files:

        try:

            with Image.open(image_path) as image:
                image.verify()

            valid_count += 1

        except Exception as error:

            invalid_count += 1

            print(f"INVALID IMAGE: {image_path}")
            print(f"Reason: {error}")

    print(f"Total images : {len(image_files)}")
    print(f"Valid images : {valid_count}")
    print(f"Invalid      : {invalid_count}")

    if other_files > 0:
        print(f"Other files  : {other_files}")

    total_images += len(image_files)
    total_valid += valid_count
    total_invalid += invalid_count
    total_other_files += other_files


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("                     DATASET SUMMARY")
print("=" * 70)

print(f"Total images : {total_images}")
print(f"Valid images : {total_valid}")
print(f"Invalid      : {total_invalid}")
print(f"Other files  : {total_other_files}")

print("=" * 70)


# ============================================================
# FINAL RESULT
# ============================================================

if total_images == 0:

    print("ERROR: No images were found.")

elif total_invalid == 0:

    print("DATASET CHECK PASSED")
    print("All detected image files are valid.")

else:

    print("WARNING: INVALID IMAGES DETECTED")
    print("Review the invalid image paths above.")

print("=" * 70)


# ============================================================
# ACTUAL DATASET STRUCTURE
# ============================================================

print("\nCurrent dataset structure:")
print("""
Industrial_Metal_Surface_Dataset_COMPACT_FINAL/
│
├── steel/
│   └── defective/
│
├── iron/
│   └── Defective/
│
└── aluminium/
    ├── good/
    └── defective/
""")

print("Dataset checking completed.")