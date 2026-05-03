# Context: [[nb:knowledge:adr-2]], [[nb:knowledge:adr-6]], [[nb:knowledge:adr-57]]
import os
import shutil
from datetime import datetime

import core_logic as core
import core_utils as utils
import constants
from core_memory_interface import get_memory_client


def purge_directives(dir_path: str, archive_path: str) -> int:
    """Archives expired directives from dir_path to archive_path."""
    if not os.path.exists(dir_path):
        core.log(f"Error: Directive directory {dir_path} not found.", "Purge")
        return 0

    os.makedirs(archive_path, exist_ok=True)
    purged_count = 0

    dir_files = [
        f
        for f in os.listdir(dir_path)
        if f.endswith((".txt", ".md")) and f != constants.README_FILE
    ]

    for df in dir_files:
        df_path = os.path.join(dir_path, df)
        if os.path.isdir(df_path):
            continue

        try:
            directive_content = core.read_file(df_path)
            if not directive_content:
                continue

            if utils.is_directive_expired(directive_content, df):
                dest_path = os.path.join(archive_path, df)
                if os.path.exists(dest_path):
                    timestamp = datetime.now().strftime(constants.ROTATION_TIMESTAMP_FORMAT)
                    name, ext = os.path.splitext(df)
                    dest_path = os.path.join(archive_path, f"{name}_{timestamp}{ext}")
                shutil.move(df_path, dest_path)
                core.log(f"Archived expired directive: {df}", "Purge")
                purged_count += 1
        except Exception as e:
            core.log(f"Error processing directive {df}: {e}", "Purge")
    return purged_count


def rotate_messages(msg_dir: str, archive_dir: str, limit: int = 50) -> bool:
    """Archives older messages from msg_dir to archive_dir."""
    if not os.path.exists(msg_dir):
        return False
    os.makedirs(archive_dir, exist_ok=True)
    msg_files = sorted(
        [
            f
            for f in os.listdir(msg_dir)
            if os.path.isfile(os.path.join(msg_dir, f)) and f != constants.HUMAN_INPUT_FILE
        ]
    )
    if len(msg_files) <= limit:
        return False
    to_archive = msg_files[:-limit]
    core.log(f"Archiving {len(to_archive)} messages.", "Rotate")
    for mf in to_archive:
        shutil.move(os.path.join(msg_dir, mf), os.path.join(archive_dir, mf))
    return True


def rotate_nb_notes(tag: str, limit: int = 5, preserve_ids: list = None) -> int:
    """Rotates old notes in knowledge base by tag."""
    client = get_memory_client()
    # Use ls instead of query for cleaner, tag-specific results
    notes = client.ls(tags=[tag])
    if len(notes) <= limit:
        return 0

    def sort_key(note):
        try:
            # Extract numeric part from path-based IDs like 'adr/1'
            id_str = note.id.split("/")[-1]
            return int(id_str)
        except (ValueError, TypeError, IndexError):
            return 0

    # Sort notes by ID numerically as a proxy for date (higher is newer)
    notes.sort(key=sort_key, reverse=True)

    to_delete = notes[limit:]
    deleted_count = 0
    preserve_ids = preserve_ids or []

    for note in to_delete:
        if note.id in preserve_ids:
            continue
        if client.delete(note.id):
            deleted_count += 1
            core.log(f"Deleted old nb note: {note.id} ({note.title})", "Rotate")

    return deleted_count


def perform_rotations(project_dir: str) -> None:
    """Executes all automated data purging and rotation tasks."""
    purge_directives(
        os.path.join(project_dir, constants.INSTRUCTIONS_DIR),
        os.path.join(project_dir, constants.ARCHIVE_INSTRUCTIONS_DIR),
    )

    # Memory and tasks are now handled by nb.
    rotate_nb_notes(constants.TAG_TASKS_BOARD, limit=3, preserve_ids=["198", "5"])
    rotate_nb_notes(constants.TAG_AUDIT, limit=3)
    rotate_nb_notes(constants.TAG_IDEA, limit=5)
    rotate_nb_notes(constants.TAG_HUMAN, limit=10)
    rotate_nb_notes(constants.TAG_ADR, limit=50)
    rotate_nb_notes(constants.TAG_RESEARCH, limit=20)
    rotate_nb_notes(constants.TAG_BENCHMARKS, limit=20)
    rotate_nb_notes(constants.STATUS_COMPLETED, limit=20)
    rotate_nb_notes(constants.TAG_MEMORY, limit=50)

    rotate_messages(
        os.path.join(project_dir, constants.COMMUNICATIONS_DIR),
        os.path.join(project_dir, constants.ARCHIVE_COMMUNICATIONS_DIR),
    )
