from pathlib import Path
from PIL import Image
import hashlib
import csv

# ============================================================
# DATASET
# ============================================================

DATASET = Path(
    r"C:\Metal_Surface_Detection\Industrial_Metal_Surface_Dataset"
)

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp"
}

# ============================================================
# HASH FUNCTION
# ============================================================

def get_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# CHECK DATASET
# ============================================================

if not DATASET.exists():
    print("ERROR: Dataset folder not found:")
    print(DATASET)
    raise SystemExit


# ============================================================
# FIND ALL IMAGES
# ============================================================

image_files = sorted(
    [
        f
        for f in DATASET.rglob("*")
        if f.is_file()
        and f.suffix.lower() in IMAGE_EXTENSIONS
    ],
    key=lambda x: str(x).lower()
)

print("=" * 75)
print("DUPLICATE IMAGE REMOVAL")
print("=" * 75)

print()
print(f"Images before removal: {len(image_files)}")
print()


# ============================================================
# FIND DUPLICATES
# ============================================================

hash_to_file = {}
duplicates = []

for index, image_file in enumerate(image_files, start=1):

    try:
        file_hash = get_sha256(image_file)

    except Exception as e:
        print(f"[ERROR] Could not hash:")
        print(image_file)
        print(e)
        continue

    if file_hash in hash_to_file:

        original = hash_to_file[file_hash]

        duplicates.append(
            {
                "duplicate": image_file,
                "original": original,
                "hash": file_hash
            }
        )

    else:

        hash_to_file[file_hash] = image_file


# ============================================================
# SHOW DUPLICATES
# ============================================================

print("=" * 75)
print("DUPLICATES FOUND")
print("=" * 75)

print(
    f"Unique images found : {len(hash_to_file)}"
)

print(
    f"Duplicate files     : {len(duplicates)}"
)

print()

for item in duplicates:

    print("KEEP:")
    print(f"  {item['original']}")

    print("REMOVE:")
    print(f"  {item['duplicate']}")

    print("-" * 75)


# ============================================================
# CONFIRMATION
# ============================================================

if not duplicates:

    print("No duplicates found.")
    raise SystemExit


print()
print("=" * 75)
print("IMPORTANT")
print("=" * 75)

print(
    f"This script will remove {len(duplicates)} duplicate files."
)

print(
    f"Remaining images will be {len(hash_to_file)}."
)

print()
print("Only duplicate files inside the organized dataset")
print("will be removed.")
print("The original ZIP/source dataset will NOT be touched.")
print()

answer = input(
    "Type YES to permanently remove these duplicates: "
).strip()

if answer != "YES":

    print()
    print("Cancelled. No files were deleted.")
    raise SystemExit


# ============================================================
# REMOVE DUPLICATES
# ============================================================

removed = 0

removal_report = []

for item in duplicates:

    duplicate_file = item["duplicate"]

    try:

        relative_duplicate = duplicate_file.relative_to(DATASET)
        relative_original = item["original"].relative_to(DATASET)

        duplicate_file.unlink()

        removed += 1

        removal_report.append(
            {
                "removed_file": str(relative_duplicate),
                "kept_file": str(relative_original),
                "sha256": item["hash"]
            }
        )

    except Exception as e:

        print()
        print("[ERROR] Could not remove:")
        print(duplicate_file)
        print(e)


# ============================================================
# FINAL COUNT
# ============================================================

remaining_files = [
    f
    for f in DATASET.rglob("*")
    if f.is_file()
    and f.suffix.lower() in IMAGE_EXTENSIONS
]


# ============================================================
# COUNT BY METAL / CONDITION
# ============================================================

categories = {
    "Steel / Defective":
        DATASET / "Steel" / "Defective",

    "Aluminium / Defective":
        DATASET / "Aluminium" / "Defective",

    "Aluminium / Good":
        DATASET / "Aluminium" / "Good",

    "Copper / Defective":
        DATASET / "Copper" / "Defective",

    "Copper / Good":
        DATASET / "Copper" / "Good",

    "Iron / Defective":
        DATASET / "Iron" / "Defective",
}


print()
print("=" * 75)
print("FINAL DATASET COUNT")
print("=" * 75)

metal_totals = {}

for category, folder in categories.items():

    if folder.exists():

        count = sum(
            1
            for f in folder.iterdir()
            if f.is_file()
            and f.suffix.lower() in IMAGE_EXTENSIONS
        )

    else:

        count = 0

    print(
        f"{category:<25}: {count:>5}"
    )


# Metal totals
steel = sum(
    1
    for f in (DATASET / "Steel").rglob("*")
    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
) if (DATASET / "Steel").exists() else 0

aluminium = sum(
    1
    for f in (DATASET / "Aluminium").rglob("*")
    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
) if (DATASET / "Aluminium").exists() else 0

copper = sum(
    1
    for f in (DATASET / "Copper").rglob("*")
    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
) if (DATASET / "Copper").exists() else 0

iron = sum(
    1
    for f in (DATASET / "Iron").rglob("*")
    if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
) if (DATASET / "Iron").exists() else 0

print()
print("-" * 75)

print(f"{'Steel total':<25}: {steel:>5}")
print(f"{'Aluminium total':<25}: {aluminium:>5}")
print(f"{'Copper total':<25}: {copper:>5}")
print(f"{'Iron total':<25}: {iron:>5}")

print("-" * 75)

print(
    f"{'FINAL UNIQUE TOTAL':<25}: {len(remaining_files):>5}"
)


# ============================================================
# SAVE REMOVAL REPORT
# ============================================================

report_path = DATASET / "duplicate_removal_report.csv"

with open(
    report_path,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    writer = csv.DictWriter(
        csvfile,
        fieldnames=[
            "removed_file",
            "kept_file",
            "sha256"
        ]
    )

    writer.writeheader()
    writer.writerows(removal_report)


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 75)
print("DUPLICATE REMOVAL COMPLETED")
print("=" * 75)

print()
print(f"Original image count : {len(image_files)}")
print(f"Duplicates removed   : {removed}")
print(f"Final unique images  : {len(remaining_files)}")

print()
print("Removal report:")
print(report_path)

print()
print("The original source ZIP/dataset was NOT modified.")
print()