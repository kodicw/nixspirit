import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import jbot_core as core
import jbot_tasks as tasks
import jbot_rotation
import jbot_utils as utils
from jbot_memory_interface import get_memory_client


# --- Team & Registry ---
def get_team_registry(project_dir: str = ".") -> Dict[str, Any]:
    """Load the team registry from .jbot/agents.json."""
    agents_path = os.path.join(project_dir, ".jbot/agents.json")
    return core.load_json(agents_path, default={})


# --- Messages ---
def send_message(
    project_dir: str, agent_name: str, body: str, subject: str = "No Subject"
) -> bool:
    """Sends a message by writing it to the .jbot/outbox directory."""
    outbox_dir = os.path.join(project_dir, ".jbot", "outbox")
    os.makedirs(outbox_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    microsecond = datetime.now().strftime("%f")
    filename = f"{timestamp}_{microsecond}_{agent_name}.txt"
    file_path = os.path.join(outbox_dir, filename)

    message_content = f"To: all\nFrom: {agent_name}\nSubject: {subject}\n\n{body}\n"
    return core.write_file(file_path, message_content)


def get_recent_messages(
    msgs_dir: Optional[str] = None,
    count: int = 5,
    include_human: bool = False,
    project_dir: str = ".",
) -> List[Dict[str, str]]:
    """
    Retrieve the most recent messages from nb knowledge base.
    Also includes human.txt from msgs_dir if enabled for legacy feedback.
    """
    results = []

    # 1. Fetch from nb (Text-First Purity)
    try:
        notebook = core.get_notebook_name(project_dir)
        client = get_memory_client(notebook=notebook)
        # ls returns notes, we want newest first for 'recent'
        notes = client.ls(tags=["type:message"], limit=count)

        def sort_key(note):
            try:
                # Extract numeric part from path-based IDs like 'adr/1'
                id_str = note.id.split("/")[-1]
                return int(id_str)
            except (ValueError, TypeError, IndexError):
                return 0

        # Sort by ID descending to ensure we have the most recent
        notes.sort(key=sort_key, reverse=True)

        for note in notes[:count]:
            content = client.show(note.id)
            if content:
                results.append({"filename": f"nb:{note.id}", "content": content})
    except Exception as e:
        core.log(f"Error fetching messages from nb: {e}", "Infra")

    # 2. Fetch human.txt (Legacy/Human-in-the-loop direct feedback)
    if (
        include_human
        and msgs_dir
        and os.path.exists(os.path.join(msgs_dir, "human.txt"))
    ):
        try:
            content = core.read_file(os.path.join(msgs_dir, "human.txt"))
            if content:
                # We put human input at the end (or beginning? usually end is more 'recent')
                results.append({"filename": "human.txt", "content": content})
        except Exception:
            pass

    return results


def parse_message_headers(content: str) -> Dict[str, str]:
    """Parses From and Subject headers from message content."""
    lines = content.split("\n")
    from_line = next(
        (line for line in lines if line.strip().startswith("From:")), "From: unknown"
    )
    subject_line = next(
        (line for line in lines if line.strip().startswith("Subject:")), "Subject: none"
    )
    return {
        "from": from_line.replace("From:", "").strip(),
        "subject": subject_line.replace("Subject:", "").strip(),
    }


def get_vision(project_dir: str = ".") -> str:
    """Retrieves the project vision from nb or .project_goal."""
    # 1. Try nb note with type:vision
    vision_note = get_note_content("type:vision", project_dir=project_dir)
    if vision_note:
        # Match vision text in Strategic Vision note
        # Support both "> Vision" and "## Strategic Vision\nVision" formats
        vision_match = re.search(
            r"## Strategic Vision\s*\n*>\s*(.*)", vision_note, re.MULTILINE
        )
        if vision_match:
            return vision_match.group(1).strip()

        # Fallback to lines after the header
        lines = vision_note.splitlines()
        for i, line in enumerate(lines):
            if "## Strategic Vision" in line and i + 1 < len(lines):
                next_line = lines[i + 1].lstrip("> ").strip()
                if next_line:
                    return next_line

        # Fallback to direct content if no header match
        lines = [
            line.lstrip("> ").strip()
            for line in vision_note.splitlines()
            if line.strip() and not line.startswith("##")
        ]
        if lines:
            return lines[0]

    # 2. Try .project_goal file
    goal_path = core.find_file_upwards(".project_goal", project_dir)
    if goal_path and os.path.exists(goal_path):
        return core.read_file(goal_path).strip()

    return "No current vision defined."


def get_note_content(query: str, project_dir: str = ".") -> Optional[str]:
    """Retrieves the full content of the first nb note matching the query."""

    try:
        notebook = core.get_notebook_name(project_dir)
        client = get_memory_client(notebook=notebook)
        note_id = None

        if query.startswith("type:") or query.startswith("#"):
            tag = query.replace("type:", "").replace("#", "")
            # Use ls for tag queries as it is more precise than q
            notes = client.ls(tags=[tag])
            if notes:

                def sort_key(note):
                    try:
                        # Extract numeric part from path-based IDs like 'adr/1'
                        id_str = note.id.split("/")[-1]
                        return int(id_str)
                    except (ValueError, TypeError, IndexError):
                        return 0

                # Sort by ID descending to get the newest by default
                notes.sort(key=sort_key, reverse=True)
                # Prefer notes with "Authoritative" or "Board" in title for tasks
                if tag == "tasks":
                    for n in notes:
                        if (
                            "authoritative" in n.title.lower()
                            or "board" in n.title.lower()
                        ):
                            note_id = n.id
                            core.log(f"Found task board: {n.title} ({n.id})", "Infra")
                            break
                if not note_id:
                    note_id = notes[0].id

        if not note_id:
            # 1. Search for the ID using 'nb jbot:q' which is the most reliable search for text
            notes = client.query(query)
            if notes:
                note_id = notes[0].id

        # 2. Fallback to title search if search failed
        if not note_id and query == "type:prompt":
            notes = client.query("Authoritative System Prompt")
            if notes:
                note_id = notes[0].id

        # 3. Get the actual content using the ID
        if note_id:
            return client.show(note_id)

        return None
    except Exception as e:
        core.log(f"Error fetching note '{query}' from nb: {e}", "Infra")
        return None


# --- Memory & Logs ---
def get_recent_logs(count: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent entries from the nb knowledge base."""
    try:
        # Get list of memory notes
        client = get_memory_client()
        notes = client.ls(tags=["memory"], limit=count)

        entries = []
        for note in notes:
            # Regex to extract agent and summary from title
            match = re.search(r"Memory: \[(.*?)\] - (.*)", note.title)
            if match:
                agent = match.group(1)
                summary = match.group(2)
                entries.append({"agent": agent, "content": {"summary": summary}})
        return entries
    except Exception as e:
        core.log(f"Error fetching logs from nb: {e}", "Infra")
        return []


# --- Directives ---
def parse_directives(dir_path: str) -> List[Dict[str, str]]:
    """Parse directives and filter out expired ones."""
    if not os.path.exists(dir_path):
        return []

    dir_files = sorted(
        [
            f
            for f in os.listdir(dir_path)
            if f.endswith((".txt", ".md")) and f != "README.md"
        ]
    )

    valid_directives = []

    for df in dir_files:
        try:
            df_path = os.path.join(dir_path, df)
            content = core.read_file(df_path)
            if content and not utils.is_directive_expired(content, df):
                valid_directives.append({"filename": df, "content": content})
        except Exception:
            pass
    return valid_directives


# --- Project Summary ---
def get_project_summary(project_dir: str = ".") -> Dict[str, Any]:
    """
    Aggregates all relevant project status information into a single structure.
    Useful for both CLI status display and dashboard generation.

    Context: [[nb:jbot:adr-210]], [[nb:jbot:adr-193]]
    """
    try:
        tasks_data = tasks.parse_tasks()
    except Exception as e:
        core.log(f"Error parsing tasks for summary: {e}", "Infra")
        tasks_data = {
            "active": [],
            "done_count": 0,
            "backlog": [],
            "vision": "",
            "sections": {
                "active": [],
                "backlog": [],
                "completed": [],
            },
        }

    msgs_dir = os.path.join(project_dir, ".jbot/messages")

    # Fetch ADRs
    adrs = utils.get_recent_adrs(5)

    # Fetch Milestones (from CHANGELOG.md)
    changelog_path = core.find_file_upwards("CHANGELOG.md", project_dir)
    milestones = []
    milestone_count = 0
    if changelog_path and os.path.exists(changelog_path):
        with open(changelog_path, "r") as f:
            lines = f.readlines()
            milestones = [
                line.strip() for line in lines if line.strip().startswith("- **")
            ][:5]
            milestone_count = sum(
                1 for line in lines if line.strip().startswith("- **")
            )

    # Calculate ROI Metrics
    try:
        client = get_memory_client()
        all_notes = client.ls()
        adr_notes = client.ls(tags=["type:adr"])
        kb_total = len(all_notes)
        adr_total = len(adr_notes)

        velocity = (
            tasks_data["done_count"] / milestone_count if milestone_count > 0 else 0
        )
        density = adr_total / milestone_count if milestone_count > 0 else adr_total
        total_tasks = (
            len(tasks_data["active"])
            + len(tasks_data["backlog"])
            + tasks_data["done_count"]
        )
        completion_ratio = (
            (tasks_data["done_count"] / total_tasks * 100) if total_tasks > 0 else 0
        )
        metrics = {
            "velocity": velocity,
            "density": density,
            "kb_total": kb_total,
            "completion_ratio": completion_ratio,
        }
    except Exception as e:
        core.log(f"Error calculating Technical ROI: {e}", "Infra")
        metrics = None

    return {
        "vision": get_vision(project_dir),
        "team": get_team_registry(project_dir),
        "tasks": tasks_data,
        "recent_messages": get_recent_messages(
            msgs_dir, 5, project_dir=project_dir, include_human=True
        ),
        "adrs": adrs,
        "milestones": milestones,
        "metrics": metrics,
        "git_status": core.get_git_status(project_dir),
        "nix_metadata": core.get_nix_metadata(project_dir),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# --- Maintenance ---
def initialize_infrastructure(project_dir: str) -> None:
    """Ensures all required JBot infrastructure directories exist."""
    infra_dirs = [
        ".jbot/queues",
        ".jbot/messages",
        ".jbot/directives",
        ".jbot/outbox",
        ".jbot/messages/archive",
        ".jbot/directives/archive",
    ]
    for d in infra_dirs:
        os.makedirs(os.path.join(project_dir, d), exist_ok=True)


def consolidate_messages(project_dir: str) -> None:
    """Consolidates messages from agent outboxes into the nb knowledge base."""
    outbox_dir = os.path.join(project_dir, ".jbot/outbox")

    if not os.path.exists(outbox_dir):
        return

    # Ensure NB environment variables for identity are respected
    env = os.environ.copy()
    if "NB_USER_NAME" not in env:
        env["NB_USER_NAME"] = "JBot System"
    if "NB_USER_EMAIL" not in env:
        env["NB_USER_EMAIL"] = "system@internal.jbot"

    notebook = core.get_notebook_name(project_dir)
    client = get_memory_client(notebook=notebook, env=env)

    for msg_file in os.listdir(outbox_dir):
        if msg_file.endswith(".txt"):
            file_path = os.path.join(outbox_dir, msg_file)
            try:
                content = core.read_file(file_path)
                if not content:
                    continue

                # Parse headers for a better title
                headers = parse_message_headers(content)
                title = f"Message: [{headers['from']}] {headers['subject']}"

                # Push to nb
                client.add(
                    title=title,
                    content=content,
                    tags=["type:message", f"from:{headers['from']}"],
                )

                # Delete outbox file (finalized in nb)
                os.remove(file_path)
                core.log(f"Consolidated message to nb: {msg_file}", "Maintenance")
            except Exception as e:
                core.log(f"Error consolidating message {msg_file}: {e}", "Maintenance")


def consolidate_memory(project_dir: str) -> None:
    """Aggregates agent memory queues into the nb knowledge base."""
    queues_dir = os.path.join(project_dir, ".jbot/queues")

    if not os.path.exists(queues_dir):
        return

    # Ensure NB environment variables for identity are respected
    env = os.environ.copy()
    if "NB_USER_NAME" not in env:
        env["NB_USER_NAME"] = "JBot System"
    if "NB_USER_EMAIL" not in env:
        env["NB_USER_EMAIL"] = "system@internal.jbot"

    client = get_memory_client(env=env)

    for q_file in os.listdir(queues_dir):
        if q_file.endswith(".json"):
            q_path = os.path.join(queues_dir, q_file)
            agent_name = q_file[:-5]
            try:
                content = core.load_json(q_path)
                summary = content.get("summary", "No summary")
                # Truncate summary for title to prevent 'File name too long'
                short_summary = (summary[:80] + "..") if len(summary) > 80 else summary
                title = f"Memory: [{agent_name}] - {short_summary}"
                tags = ["memory", f"agent:{agent_name}"]

                client.add(title=title, content=json.dumps(content), tags=tags)

                os.remove(q_path)
                core.log(f"Consolidated memory for {agent_name} into nb", "Maintenance")
            except Exception as e:
                core.log(
                    f"Error consolidating memory for {agent_name} to nb: {e}",
                    "Maintenance",
                )


def run_maintenance(project_dir: str) -> bool:
    """Performs all automated infrastructure maintenance tasks."""
    core.ensure_single_user(project_dir)
    core.log("Starting infrastructure maintenance...", "Maintenance")
    try:
        initialize_infrastructure(project_dir)
        consolidate_messages(project_dir)
        consolidate_memory(project_dir)
        jbot_rotation.perform_rotations(project_dir)
        utils.generate_dashboard(project_dir=project_dir)
        core.log("Maintenance complete.", "Maintenance")
        return True
    except Exception as e:
        core.log(f"Maintenance failed: {e}", "Maintenance")
        return False


def discover_projects(root_dir: str) -> List[str]:
    """Scans a root directory for JBot projects (directories containing .jbot/agents.json)."""
    projects = []
    if not os.path.isdir(root_dir):
        return projects

    for item in os.listdir(root_dir):
        path = os.path.join(root_dir, item)
        if os.path.isdir(path):
            if os.path.exists(os.path.join(path, ".jbot", "agents.json")):
                projects.append(path)
    return projects
