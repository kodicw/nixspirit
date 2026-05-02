# Context: [[nb:jbot:adr-57]]
import os
import subprocess
import re
import json
import time
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import jbot_core as core

from jbot_memory_interface import MemoryInterface, MemoryNote


class NbClient(MemoryInterface):
    """
    A standalone Python client for interacting with the `nb` CLI knowledge base.
    Features:
    - In-memory and persistent file-based caching for ID-to-filename mapping.
    - Hybrid retrieval: prioritizes direct filesystem reads for 100x speedup.
    - Threaded batch retrieval for parallel nb show calls.
    - Automatic identity and environment management for non-interactive use.
    """

    _cache = {}
    _id_to_filename = {}
    _notebook_path_cache = {}
    _persistent_cache_file = ".jbot/nb_cache.json"

    @classmethod
    def clear_cache(cls):
        """Clears all caches and persistent cache file."""
        cls._cache.clear()
        cls._id_to_filename.clear()
        cls._notebook_path_cache.clear()
        if os.path.exists(cls._persistent_cache_file):
            try:
                os.remove(cls._persistent_cache_file)
            except Exception:
                pass

    def __init__(
        self, notebook: Optional[str] = None, env: Optional[Dict[str, str]] = None
    ):
        self.env = env or os.environ.copy()
        self.notebook = notebook or core.get_notebook_name()

        # Ensure non-interactive behavior
        self.env["EDITOR"] = "cat"
        self.env["PAGER"] = "cat"
        self.env["NB_PAGER"] = "cat"

        # Mock 'less' if missing
        tmp_bin = "/tmp/jbot_bin"
        less_path = os.path.join(tmp_bin, "less")
        if not os.path.exists(less_path):
            os.makedirs(tmp_bin, exist_ok=True)
            with open(less_path, "w") as f:
                f.write(
                    '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "less 1"; else cat "$@"; fi\n'
                )
            os.chmod(less_path, 0o755)

        if tmp_bin not in self.env.get("PATH", ""):
            self.env["PATH"] = f"{tmp_bin}:{self.env.get('PATH', '')}"

        # Resolve and cache the physical notebook path
        self.notebook_path = self._resolve_notebook_path()
        self._load_persistent_cache()

    def _resolve_notebook_path(self) -> Optional[str]:
        """Resolves the absolute physical path of the current notebook."""
        if self.notebook in NbClient._notebook_path_cache:
            return NbClient._notebook_path_cache[self.notebook]

        try:
            # 1. Try NB_NOTEBOOK_PATH env var
            if "NB_NOTEBOOK_PATH" in self.env:
                path = self.env["NB_NOTEBOOK_PATH"]
                NbClient._notebook_path_cache[self.notebook] = path
                return path

            # 2. Use git rev-parse (most reliable since nb notebooks are git repos)
            result = self._run([f"{self.notebook}:git", "rev-parse", "--show-toplevel"])
            if result.returncode == 0:
                path = result.stdout.strip()
                if path:
                    NbClient._notebook_path_cache[self.notebook] = path
                    return path

            # 3. Fallback to notebooks list
            result = self._run(["notebooks", "list", "--path"])
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    if line.endswith(f"/{self.notebook}"):
                        NbClient._notebook_path_cache[self.notebook] = line
                        return line
        except Exception:
            pass
        return None

    def _load_persistent_cache(self):
        """Loads ID-to-filename mapping from file."""
        if os.path.exists(self._persistent_cache_file):
            try:
                with open(self._persistent_cache_file, "r") as f:
                    data = json.load(f)
                    id_to_file = data.get("id_to_filename", {})
                    for k, v in id_to_file.items():
                        if k not in NbClient._id_to_filename:
                            NbClient._id_to_filename[k] = v
                    notes = data.get("notes", {})
                    for k, v in notes.items():
                        if k not in NbClient._cache:
                            NbClient._cache[k] = v
            except Exception as e:
                core.log(f"Failed to load persistent cache: {e}", "NbClient")

    def _save_persistent_cache(self):
        """Saves current ID-to-filename mapping to file."""
        try:
            os.makedirs(os.path.dirname(self._persistent_cache_file), exist_ok=True)
            with open(self._persistent_cache_file, "w") as f:
                json.dump(
                    {
                        "id_to_filename": NbClient._id_to_filename,
                        "notes": {
                            k: v for k, v in NbClient._cache.items() if len(v) < 2000
                        },
                        "timestamp": time.time(),
                    },
                    f,
                )
        except Exception as e:
            core.log(f"Failed to save persistent cache: {e}", "NbClient")

    def _run(self, args: List[str]) -> subprocess.CompletedProcess:
        """Helper to run nb commands."""
        nb_bin = self.env.get("NB_BIN", "nb")
        return subprocess.run(
            [nb_bin, "--no-color"] + args,
            capture_output=True,
            text=True,
            env=self.env,
        )

    def add(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> Optional[str]:
        """
        Add a new note to the notebook.
        """
        args = [f"{self.notebook}:add", "--title", title, "--content", content]
        if tags:
            args.extend(["--tags", ",".join(tags)])
        if overwrite:
            args.extend(["--overwrite", "--force"])

        result = self._run(args)
        if result.returncode == 0 and result.stdout:
            match = re.search(r"Added:\s*\[(?:[^\]]*:)?([^\]]+)\]", result.stdout)
            if match:
                note_id = match.group(1)
                cache_key = f"{self.notebook}:{note_id}"
                NbClient._cache[cache_key] = content.strip()
                self._save_persistent_cache()
                return note_id
        return None

    def show(self, note_id: str) -> Optional[str]:
        """
        Get the full content of a note by ID, using hybrid retrieval.
        """
        cache_key = f"{self.notebook}:{note_id}"
        if cache_key in NbClient._cache:
            return NbClient._cache[cache_key]

        # 1. Direct FS read if possible
        if self.notebook_path and note_id in NbClient._id_to_filename:
            filename = NbClient._id_to_filename[note_id]
            file_path = os.path.join(self.notebook_path, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        content = f.read().strip()
                        NbClient._cache[cache_key] = content
                        return content
                except Exception:
                    pass

        # 2. Fallback to nb show
        result = self._run([f"{self.notebook}:show", note_id, "--print"])
        if result.returncode == 0:
            content = result.stdout.strip()
            NbClient._cache[cache_key] = content
            return content
        return None

    def show_batch(self, note_ids: List[str]) -> Dict[str, str]:
        """
        Retrieve content for multiple notes in parallel.
        """
        results = {}
        to_fetch = []
        for nid in note_ids:
            cache_key = f"{self.notebook}:{nid}"
            if cache_key in NbClient._cache:
                results[nid] = NbClient._cache[cache_key]
            else:
                to_fetch.append(nid)
        if to_fetch:
            with ThreadPoolExecutor(max_workers=min(len(to_fetch), 10)) as executor:
                future_to_id = {
                    executor.submit(self.show, nid): nid for nid in to_fetch
                }
                for future in future_to_id:
                    nid = future_to_id[future]
                    content = future.result()
                    if content:
                        results[nid] = content
        return results

    def query(self, query: str) -> List[MemoryNote]:
        return self.search(query=query)

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryNote]:
        args = [f"{self.notebook}:search", "--list"]
        if tags:
            tag_query = ",".join([t.lstrip("#") for t in tags])
            args.extend(["--tag", tag_query])
        if query:
            args.append(query)
        elif not tags:
            return self._ls_with_filenames(limit=limit)

        result = self._run(args)
        if result.returncode != 0:
            return []
        notes = self._parse_ls_output(result.stdout)
        if limit is not None:
            notes = notes[:limit]
        return notes

    def _ls_with_filenames(self, limit: Optional[int] = None) -> List[MemoryNote]:
        args = [f"{self.notebook}:ls", "--filenames", "-a"]
        if limit is not None:
            args.append(f"--{limit}")
        result = self._run(args)
        if result.returncode != 0:
            return []
        notes = self._parse_ls_output(result.stdout)
        if limit is not None:
            notes = notes[:limit]
        return notes

    def edit(
        self,
        note_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        overwrite: bool = True,
    ) -> bool:
        args = [f"{self.notebook}:edit", note_id]
        if content is not None:
            args.extend(["--content", content])
        if title is not None:
            args.extend(["--title", title])
        if tags is not None:
            args.extend(["--tags", ",".join(tags)])
        if overwrite:
            args.append("--overwrite")

        result = self._run(args)
        if result.returncode == 0:
            if content is not None:
                NbClient._cache[f"{self.notebook}:{note_id}"] = content.strip()
            if title is not None and note_id in NbClient._id_to_filename:
                del NbClient._id_to_filename[note_id]
            self._save_persistent_cache()
            return True
        return False

    def ls(
        self, tags: Optional[List[str]] = None, limit: Optional[int] = None
    ) -> List[MemoryNote]:
        return self.search(tags=tags, limit=limit)

    def _parse_ls_output(self, output: str) -> List[MemoryNote]:
        notes = []
        mapping_changed = False
        for line in output.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("-") or line.startswith("="):
                continue
            match = re.search(r"\[(?:[^\]]*:)?([^\]]+)\]\s+(.*)", line)
            if match:
                note_id = match.group(1)
                title_metadata = match.group(2).strip()
                filename = None
                if " · " in title_metadata:
                    parts = title_metadata.split(" · ", 1)
                    filename = parts[0].strip()
                    title = parts[1].strip()
                elif title_metadata.endswith(".md"):
                    filename = title_metadata
                    title = title_metadata
                else:
                    title = title_metadata

                title = re.sub(r"^[🔖🔒📂🌄📄📹🔉📖✔️✅📌]\s*", "", title)
                title = re.sub(r"\s+\[.*?\]$", "", title)
                if filename:
                    if NbClient._id_to_filename.get(note_id) != filename:
                        NbClient._id_to_filename[note_id] = filename
                        mapping_changed = True
                notes.append(
                    MemoryNote(id=note_id, title=title, tags=[], filename=filename)
                )
        if mapping_changed:
            self._save_persistent_cache()
        return notes

    def delete(self, note_id: str) -> bool:
        result = self._run([f"{self.notebook}:delete", note_id, "--force"])
        if result.returncode == 0:
            cache_key = f"{self.notebook}:{note_id}"
            if cache_key in NbClient._cache:
                del NbClient._cache[cache_key]
            if note_id in NbClient._id_to_filename:
                del NbClient._id_to_filename[note_id]
            self._save_persistent_cache()
            return True
        return False
