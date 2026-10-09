from pathlib import Path
import shutil

# Original Dataset extracted from the ZIP
SOURCE_DATASET = Path(
    r"C:\Metal_Surface_Detection\Industrial_Metal_Surface_Dataset_COMPACT_FINAL\Dataset"
)

# Existing organized dataset
DEST_DATASET = Path(
    r"C:\Metal_Surface_Detection\Industrial_Metal_Surface_Dataset"
)


# ============================================================
# FUNCTION: COPY ALL FILES WITHOUT DELETING ANYTHING
# ============================================================

def copy_folder_contents(source_folder, destination_folder):
    destination_folder.mkdir(parents=True, exist_ok=True)

    copied = 0
    renamed = 0
    skipped = 0

    for source_file in sorted(source_folder.iterdir()):
        if not source_file.is_file():
            continue

        destination_file = destination_folder / source_file.name

        # If the filename already exists, create a new filename.
        if destination_file.exists():
            stem = source_file.stem
            suffix = source_file.suffix

            counter = 1

            while True:
                new_name = f"{stem}_merged_{counter}{suffix}"
                new_destination = destination_folder / new_name

                if not new_destination.exists():
                    destination_file = new_destination
                    renamed += 1
                    break

                counter += 1

        shutil.copy2(source_file, destination_file)
        copied += 1

    return copied, renamed, skipped


# ============================================================
# CHECK SOURCE
# ============================================================

if not SOURCE_DATASET.exists():
    print("ERROR: Source Dataset folder was not found.")
    print()
    print("Expected:")
    print(SOURCE_DATASET)
    print()
    print("Please change SOURCE_DATASET at the top of the script.")
    input("Press Enter to exit...")
    raise SystemExit


# ============================================================
# SOURCE FOLDERS
# ============================================================

source_defective = SOURCE_DATASET / "Defective"
source_good = SOURCE_DATASET / "Good"

if not source_defective.exists():
    print("ERROR: Dataset\\Defective folder was not found:")
    print(source_defective)
    input("Press Enter to exit...")
    raise SystemExit

if not source_good.exists():
    print("ERROR: Dataset\\Good folder was not found:")
    print(source_good)
    input("Press Enter to exit...")
    raise SystemExit


# ============================================================
# DESTINATION FOLDERS
# ============================================================

aluminium_defective = DEST_DATASET / "Aluminium" / "Defective"
aluminium_good = DEST_DATASET / "Aluminium" / "Good"


# ============================================================
# CREATE DESTINATION FOLDERS
# ============================================================

aluminium_defective.mkdir(parents=True, exist_ok=True)
aluminium_good.mkdir(parents=True, exist_ok=True)


# ============================================================
# MERGE DATASET/DEFECTIVE
# ============================================================

print("=" * 65)
print("MERGING Dataset/Defective")
print("=" * 65)

defective_copied, defective_renamed, _ = copy_folder_contents(
    source_defective,
    aluminium_defective
)

print(f"Images copied   : {defective_copied}")
print(f"Files renamed   : {defective_renamed}")
print(f"Destination     : {aluminium_defective}")
print()


# ============================================================
# MERGE DATASET/GOOD
# ============================================================

print("=" * 65)
print("MERGING Dataset/Good")
print("=" * 65)

good_copied, good_renamed, _ = copy_folder_contents(
    source_good,
    aluminium_good
)

print(f"Images copied   : {good_copied}")
print(f"Files renamed   : {good_renamed}")
print(f"Destination     : {aluminium_good}")
print()


# ============================================================
# FINAL COUNT
# ============================================================

def count_files(folder):
    return sum(1 for f in folder.iterdir() if f.is_file())


final_defective = count_files(aluminium_defective)
final_good = count_files(aluminium_good)

steel_folder = DEST_DATASET / "Steel" / "Defective"
iron_folder = DEST_DATASET / "Iron" / "Defective"

steel_count = count_files(steel_folder) if steel_folder.exists() else 0
iron_count = count_files(iron_folder) if iron_folder.exists() else 0

total = steel_count + final_defective + final_good + iron_count


# ============================================================
# FINAL REPORT
# ============================================================

print("=" * 65)
print("MERGE COMPLETED SUCCESSFULLY")
print("=" * 65)

print()
print("Final dataset:")
print(f"  Steel / Defective       : {steel_count}")
print(f"  Aluminium / Defective   : {final_defective}")
print(f"  Aluminium / Good        : {final_good}")
print(f"  Iron / Defective        : {iron_count}")
print("----------------------------------------")
print(f"  TOTAL                   : {total}")

print()
print("Dataset location:")
print(DEST_DATASET)

print()
print("IMPORTANT:")
print("No existing files were deleted.")
print("No existing files were moved.")
print("If a filename already existed, the new file was renamed")
print("using the pattern: filename_merged_1.jpg, etc.")

input("\nPress Enter to exit...")