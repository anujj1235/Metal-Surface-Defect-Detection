from pathlib import Path
import hashlib
import shutil
import csv

SOURCE = Path("Industrial_Metal_Surface_Dataset_COMPACT_FINAL")
OUTPUT = Path("Industrial_Metal_Surface_Dataset")

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp",
    ".tif", ".tiff", ".webp"
}

STEEL_FOLDERS = [
    SOURCE / "D" / "1",
    SOURCE / "D" / "8",
    SOURCE / "D" / "9",
    SOURCE / "D" / "10",
]

ALUMINIUM_DEFECTIVE = SOURCE / "Dataset" / "Defective"
ALUMINIUM_GOOD = SOURCE / "Dataset" / "Good"

IRON_DEFECTIVE = SOURCE / "iron" / "Defective"


def image_files(folder):
    if not folder.exists():
        return []

    return sorted(
        x for x in folder.iterdir()
        if x.is_file() and x.suffix.lower() in IMAGE_EXTENSIONS
    )


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def copy_unique(
    source_file,
    destination_dir,
    used_hashes,
    report,
    material,
    condition
):
    file_hash = sha256(source_file)

    if file_hash in used_hashes:
        report.append([
            str(source_file),
            material,
            condition,
            "DUPLICATE_SKIPPED",
            ""
        ])
        return False

    used_hashes.add(file_hash)

    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / source_file.name

    if destination.exists():
        stem = source_file.stem
        suffix = source_file.suffix
        counter = 1

        while destination.exists():
            destination = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(source_file, destination)

    report.append([
        str(source_file),
        material,
        condition,
        "COPIED",
        str(destination)
    ])

    return True


def copy_all(
    source_file,
    destination_dir,
    report,
    material,
    condition
):
    """
    Used for Iron because the user has verified the Iron labels.
    Every Iron image is preserved.
    """

    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / source_file.name

    if destination.exists():
        stem = source_file.stem
        suffix = source_file.suffix
        counter = 1

        while destination.exists():
            destination = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(source_file, destination)

    report.append([
        str(source_file),
        material,
        condition,
        "COPIED",
        str(destination)
    ])

    return True


def main():

    if not SOURCE.exists():
        print("ERROR: Source dataset not found:")
        print(SOURCE.resolve())
        return

    print("=" * 60)
    print("FINAL METAL DATASET ORGANIZATION")
    print("=" * 60)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    steel_output = OUTPUT / "Steel" / "Defective"
    aluminium_defective_output = OUTPUT / "Aluminium" / "Defective"
    aluminium_good_output = OUTPUT / "Aluminium" / "Good"
    iron_output = OUTPUT / "Iron" / "Defective"

    used_hashes = set()
    report = []

    # =========================================================
    # STEEL
    # =========================================================

    print("\nProcessing Steel / Defective...")

    steel_found = 0
    steel_copied = 0

    for folder in STEEL_FOLDERS:

        files = image_files(folder)

        print(
            f"  {folder.relative_to(SOURCE)} "
            f"-> {len(files)} images"
        )

        steel_found += len(files)

        for file in files:

            if copy_unique(
                file,
                steel_output,
                used_hashes,
                report,
                "Steel",
                "Defective"
            ):
                steel_copied += 1

    # =========================================================
    # ALUMINIUM DEFECTIVE
    # =========================================================

    print("\nProcessing Aluminium / Defective...")

    aluminium_defective_files = image_files(
        ALUMINIUM_DEFECTIVE
    )

    print(
        f"  Dataset/Defective "
        f"-> {len(aluminium_defective_files)} images"
    )

    aluminium_defective_copied = 0

    for file in aluminium_defective_files:

        if copy_unique(
            file,
            aluminium_defective_output,
            used_hashes,
            report,
            "Aluminium",
            "Defective"
        ):
            aluminium_defective_copied += 1

    # =========================================================
    # ALUMINIUM GOOD
    # =========================================================

    print("\nProcessing Aluminium / Good...")

    aluminium_good_files = image_files(
        ALUMINIUM_GOOD
    )

    print(
        f"  Dataset/Good "
        f"-> {len(aluminium_good_files)} images"
    )

    aluminium_good_copied = 0

    for file in aluminium_good_files:

        if copy_unique(
            file,
            aluminium_good_output,
            used_hashes,
            report,
            "Aluminium",
            "Good"
        ):
            aluminium_good_copied += 1

    # =========================================================
    # IRON
    # =========================================================

    print("\nProcessing Iron / Defective...")

    iron_files = image_files(IRON_DEFECTIVE)

    print(
        f"  iron/Defective "
        f"-> {len(iron_files)} images"
    )

    iron_copied = 0

    for file in iron_files:

        # IMPORTANT:
        # Iron images are preserved even if identical content
        # exists elsewhere in the dataset.
        if copy_all(
            file,
            iron_output,
            report,
            "Iron",
            "Defective"
        ):
            iron_copied += 1

    # =========================================================
    # REPORT
    # =========================================================

    report_file = OUTPUT / "organization_report.csv"

    with open(
        report_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "source_file",
            "material",
            "condition",
            "status",
            "destination_file"
        ])

        writer.writerows(report)

    # =========================================================
    # FINAL COUNTS
    # =========================================================

    final_steel = len(image_files(steel_output))
    final_aluminium_defective = len(
        image_files(aluminium_defective_output)
    )
    final_aluminium_good = len(
        image_files(aluminium_good_output)
    )
    final_iron = len(image_files(iron_output))

    total = (
        final_steel
        + final_aluminium_defective
        + final_aluminium_good
        + final_iron
    )

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    print(f"Steel images found:              {steel_found}")
    print(f"Steel unique images copied:      {steel_copied}")

    print()
    print(
        f"Aluminium defective found:       "
        f"{len(aluminium_defective_files)}"
    )
    print(
        f"Aluminium defective copied:      "
        f"{aluminium_defective_copied}"
    )

    print()
    print(
        f"Aluminium good found:            "
        f"{len(aluminium_good_files)}"
    )
    print(
        f"Aluminium good copied:           "
        f"{aluminium_good_copied}"
    )

    print()
    print(f"Iron defective found:            {len(iron_files)}")
    print(f"Iron defective copied:            {iron_copied}")

    print("\nFinal dataset:")

    print(
        f"  Steel / Defective:       "
        f"{final_steel}"
    )

    print(
        f"  Aluminium / Defective:   "
        f"{final_aluminium_defective}"
    )

    print(
        f"  Aluminium / Good:        "
        f"{final_aluminium_good}"
    )

    print(
        f"  Iron / Defective:        "
        f"{final_iron}"
    )

    print()
    print(f"TOTAL UNIQUE/INCLUDED IMAGES: {total}")

    print("\nIron dataset: INCLUDED")
    print("Reason: User verified the Iron labels.")

    print("\nOrganization report:")
    print(report_file.resolve())

    print("\nOutput dataset:")
    print(OUTPUT.resolve())

    print("\nDone.")


if __name__ == "__main__":
    main()