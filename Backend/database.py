# ============================================================
# INDUSTRIAL METAL SURFACE DEFECT DETECTION
# DATABASE SERVICE
# ============================================================

import sqlite3
from pathlib import Path
from datetime import datetime
import json


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent

DATABASE_PATH = (
    BASE_DIR / "metal_vision.db"
)


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    """
    Create a SQLite database connection.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database():
    """
    Create the inspections table if it does not exist.

    Also performs a lightweight migration for databases
    created by earlier versions of the project.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Create table
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                inspection_id TEXT UNIQUE,

                file_name TEXT,

                metal_type TEXT,

                defect_type TEXT,

                confidence REAL,

                status TEXT,

                severity TEXT,

                defect_location TEXT,

                image_path TEXT,

                gradcam_path TEXT,

                created_at TEXT,

                defect_coverage REAL DEFAULT 0,

                recommendation TEXT,

                reuse_guidance TEXT
            )
            """
        )

        connection.commit()

        # ----------------------------------------------------
        # Existing columns
        # ----------------------------------------------------

        cursor.execute(
            "PRAGMA table_info(inspections)"
        )

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        # ----------------------------------------------------
        # Migration helper
        # ----------------------------------------------------

        required_columns = {

            "inspection_id":
                "TEXT",

            "file_name":
                "TEXT",

            "metal_type":
                "TEXT",

            "defect_type":
                "TEXT",

            "confidence":
                "REAL",

            "status":
                "TEXT",

            "severity":
                "TEXT",

            "defect_location":
                "TEXT",

            "image_path":
                "TEXT",

            "gradcam_path":
                "TEXT",

            "created_at":
                "TEXT",

            "defect_coverage":
                "REAL DEFAULT 0",

            "recommendation":
                "TEXT",

            "reuse_guidance":
                "TEXT"
        }

        for column_name, column_type in (
            required_columns.items()
        ):

            if column_name not in existing_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE inspections
                    ADD COLUMN {column_name}
                    {column_type}
                    """
                )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# SAVE INSPECTION
# ============================================================

def save_inspection(
    inspection_id,
    file_name,
    metal_type,
    defect_type,
    confidence,
    status,
    severity=None,
    defect_location=None,
    image_path=None,
    gradcam_path=None,
    defect_coverage=0.0,
    recommendation=None,
    reuse_guidance=None
):
    """
    Save an inspection result.

    Newer fields are optional so that this function remains
    compatible with older code.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Convert defect location to JSON
        # ----------------------------------------------------

        if defect_location is None:

            defect_location_json = json.dumps(
                {
                    "detected": False,
                    "coverage_percent": 0.0,
                    "boxes": []
                }
            )

        elif isinstance(
            defect_location,
            str
        ):

            defect_location_json = (
                defect_location
            )

        else:

            defect_location_json = json.dumps(
                defect_location
            )

        # ----------------------------------------------------
        # Created time
        # ----------------------------------------------------

        created_at = datetime.now().isoformat(
            timespec="seconds"
        )

        # ----------------------------------------------------
        # Insert / update
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO inspections (
                inspection_id,
                file_name,
                metal_type,
                defect_type,
                confidence,
                status,
                severity,
                defect_location,
                image_path,
                gradcam_path,
                created_at,
                defect_coverage,
                recommendation,
                reuse_guidance
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(inspection_id)
            DO UPDATE SET
                file_name = excluded.file_name,
                metal_type = excluded.metal_type,
                defect_type = excluded.defect_type,
                confidence = excluded.confidence,
                status = excluded.status,
                severity = excluded.severity,
                defect_location = excluded.defect_location,
                image_path = excluded.image_path,
                gradcam_path = excluded.gradcam_path,
                created_at = excluded.created_at,
                defect_coverage = excluded.defect_coverage,
                recommendation = excluded.recommendation,
                reuse_guidance = excluded.reuse_guidance
            """,
            (
                inspection_id,
                file_name,
                metal_type,
                defect_type,
                float(confidence or 0),
                status,
                severity,
                defect_location_json,
                image_path,
                gradcam_path,
                created_at,
                float(
                    defect_coverage or 0
                ),
                recommendation,
                reuse_guidance
            )
        )

        connection.commit()

        return inspection_id

    finally:

        connection.close()


# ============================================================
# CONVERT DATABASE ROW
# ============================================================

def _row_to_dict(
    row
):
    """
    Convert a SQLite row to a JSON-friendly dictionary.
    """

    if row is None:
        return None

    result = dict(row)

    # --------------------------------------------------------
    # Decode defect location
    # --------------------------------------------------------

    defect_location = result.get(
        "defect_location"
    )

    if isinstance(
        defect_location,
        str
    ):

        try:

            result[
                "defect_location"
            ] = json.loads(
                defect_location
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):

            result[
                "defect_location"
            ] = {
                "detected": False,
                "coverage_percent": (
                    result.get(
                        "defect_coverage",
                        0
                    ) or 0
                ),
                "boxes": []
            }

    elif defect_location is None:

        result[
            "defect_location"
        ] = {
            "detected": False,
            "coverage_percent": (
                result.get(
                    "defect_coverage",
                    0
                ) or 0
            ),
            "boxes": []
        }

    # --------------------------------------------------------
    # Make sure defect coverage exists
    # --------------------------------------------------------

    if result.get(
        "defect_coverage"
    ) is None:

        try:

            result[
                "defect_coverage"
            ] = float(
                result[
                    "defect_location"
                ].get(
                    "coverage_percent",
                    0
                )
            )

        except Exception:

            result[
                "defect_coverage"
            ] = 0.0

    # --------------------------------------------------------
    # Good confidence must be 100%
    # --------------------------------------------------------

    if str(
        result.get(
            "status",
            ""
        )
    ).upper() == "GOOD":

        result[
            "confidence"
        ] = 100.0

    return result


# ============================================================
# GET ALL INSPECTIONS
# ============================================================

def get_all_inspections():
    """
    Return all inspection records, newest first.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM inspections
            ORDER BY
                id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            _row_to_dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# GET SINGLE INSPECTION
# ============================================================

def get_single_inspection(
    inspection_id
):
    """
    Return one inspection by inspection ID.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM inspections
            WHERE inspection_id = ?
            LIMIT 1
            """,
            (
                inspection_id,
            )
        )

        row = cursor.fetchone()

        return _row_to_dict(
            row
        )

    finally:

        connection.close()


# ============================================================
# DELETE INSPECTION
# ============================================================

def delete_inspection(
    inspection_id
):
    """
    Delete one inspection record.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM inspections
            WHERE inspection_id = ?
            """,
            (
                inspection_id,
            )
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# ============================================================
# CLEAR ALL INSPECTIONS
# ============================================================

def clear_inspections():
    """
    Delete all inspection records.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM inspections"
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# INITIALIZE WHEN RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "Metal Vision AI - Database"
    )

    print(
        "=========================================="
    )

    print(
        f"Database path: {DATABASE_PATH}"
    )

    init_database()

    print(
        "Database initialized successfully."
    )