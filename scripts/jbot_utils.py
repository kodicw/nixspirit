import os
import re
import glob
from datetime import datetime
from typing import List, Dict, Optional

import jbot_core as core
from jbot_memory_interface import get_memory_client

# Context: [[nb:jbot:adr-210]], [[nb:jbot:adr-193]]


def update_note_stably(title: str, content: str, tags: List[str]) -> bool:
    """Updates an existing note if found by title and tags, otherwise adds a new one."""
    try:
        client = get_memory_client()
        notes = client.ls(tags=tags)

        target_id = None
        for n in notes:
            if n.title.lower() == title.lower():
                target_id = n.id
                break

        if target_id:
            return client.edit(target_id, content)
        else:
            return client.add(title, content, tags=tags) is not None
    except Exception as e:
        core.log(f"Error stably updating note '{title}': {e}", "Utils")
        return False


def get_recent_adrs(count: int = 5) -> List[Dict[str, str]]:
    """Retrieve the most recent ADRs from the nb knowledge base."""
    try:
        client = get_memory_client()
        notes = client.ls(tags=["type:adr"])

        def sort_key(note):
            try:
                # Extract numeric part from path-based IDs like 'adr/1'
                id_str = note.id.split("/")[-1]
                return int(id_str)
            except (ValueError, TypeError, IndexError):
                return 0

        notes.sort(key=sort_key, reverse=True)

        results = []
        for note in notes:
            results.append({"id": note.id, "title": note.title})
            if len(results) >= count:
                break
        return results
    except Exception as e:
        core.log(f"Error fetching ADRs from nb: {e}", "Utils")
        return []


def get_directive_expiration(
    content: str, filename: Optional[str] = None
) -> Optional[str]:
    """Extracts expiration date from content or filename."""
    # 1. Check content for "Expiration: YYYY-MM-DD"
    content_exp_match = re.search(
        r"Expiration:\s*(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE
    )
    if content_exp_match:
        return content_exp_match.group(1)

    # 2. Check filename for "YYYY-MM-DD"
    if filename:
        filename_exp_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        if filename_exp_match:
            return filename_exp_match.group(1)

    return None


def is_directive_expired(content: str, filename: Optional[str] = None) -> bool:
    """Checks if a directive is expired based on today's date."""
    exp_date = get_directive_expiration(content, filename)
    if not exp_date:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    return today > exp_date


def generate_dashboard(output_file: str = "INDEX.md", project_dir: str = ".") -> bool:
    """Generates a markdown dashboard summarizing the project status.

    Context: [[nb:jbot:adr-193]], [[nb:jbot:adr-200]], [[nb:jbot:adr-205]]
    """
    import jbot_infra as infra

    try:
        summary = infra.get_project_summary(project_dir)
        tasks_data = summary["tasks"]
    except Exception as e:
        core.log(f"Error fetching project summary for dashboard: {e}", "Utils")
        summary = {
            "vision": "Error fetching vision.",
            "team": {},
            "tasks": {
                "active": [],
                "backlog": [],
                "done_count": 0,
                "sections": {"active": [], "backlog": [], "completed": []},
            },
            "recent_messages": [],
            "adrs": [],
            "milestones": [],
            "metrics": None,
            "git_status": "Unknown",
            "nix_metadata": "Unknown",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        tasks_data = summary["tasks"]

    dashboard_content = "# JBot Dashboard\n\n"
    dashboard_content += f"*Last Updated: {summary['timestamp']}*\n\n"

    dashboard_content += "## 🎯 Strategic Vision\n"
    dashboard_content += f"> {summary['vision']}\n\n"

    dashboard_content += "## 👥 Team Roster\n"
    agents = summary["team"]
    if agents:
        dashboard_content += (
            "| Agent | Role | Description |\n|-------|------|-------------|\n"
        )
        for name, info in agents.items():
            dashboard_content += (
                f"| {name} | {info.get('role')} | {info.get('description')} |\n"
            )
        dashboard_content += "\n"

    dashboard_content += "## 🚀 Active Tasks\n"
    active_tasks = [t for t in tasks_data["active"] if "- [ ]" in t]
    if active_tasks:
        for task in active_tasks[:10]:
            match = re.search(r"\(Agent:\s*([^)]+)\)", task)
            agent_str = f" [{match.group(1)}]" if match else ""
            task_clean = re.sub(r"\s*\(Agent:\s*[^)]+\)", "", task)
            dashboard_content += f"{task_clean}{agent_str}\n"
        dashboard_content += "\n"
    else:
        dashboard_content += "No active tasks.\n\n"

    if tasks_data["backlog"]:
        dashboard_content += "## 📦 Backlog Highlights\n"
        for task in tasks_data["backlog"][:5]:
            dashboard_content += f"{task}\n"
        dashboard_content += "\n"

    completed_tasks = []
    for line in tasks_data["sections"]["completed"]:
        stripped = line.strip()
        if stripped.startswith("-"):
            completed_tasks.append(stripped)

    if completed_tasks:
        dashboard_content += "## ✅ Recently Completed\n"
        for task in completed_tasks[:5]:
            dashboard_content += f"{task}\n"
        dashboard_content += "\n"

    dashboard_content += "## 📜 Recent ADRs\n"
    if summary["adrs"]:
        for adr in summary["adrs"]:
            dashboard_content += f"- [[nb:{adr['id']}]] {adr['title']}\n"
        dashboard_content += "\n"
    else:
        dashboard_content += "No ADRs found.\n\n"

    dashboard_content += "## 💬 Recent Messages\n"
    if summary["recent_messages"]:
        for m in reversed(summary["recent_messages"]):
            headers = infra.parse_message_headers(m["content"])
            if m["filename"].startswith("nb:"):
                # Link to nb note
                note_id = m["filename"].replace("nb:", "")
                dashboard_content += f"- **[{headers['from']}]** {headers['subject']} ([[nb:{note_id}]])\n"
            else:
                # Legacy file link
                dashboard_content += f"- **[{headers['from']}]** {headers['subject']} ([{m['filename']}](.jbot/messages/{m['filename']}))\n"
        dashboard_content += "\n"
    else:
        dashboard_content += "No recent messages.\n\n"

    dashboard_content += "## 📊 Architectural Diagrams\n"
    mermaid_files = glob.glob(os.path.join(project_dir, "scripts/*.mermaid"))
    if mermaid_files:
        for mermaid_file in sorted(mermaid_files):
            title = (
                os.path.basename(mermaid_file)
                .replace(".mermaid", "")
                .replace("_", " ")
                .title()
            )
            content = core.read_file(mermaid_file)
            dashboard_content += f"### {title}\n"
            dashboard_content += "```mermaid\n"
            dashboard_content += content + "\n"
            dashboard_content += "```\n\n"

    dashboard_content += "## 📈 Status & Progress\n"
    dashboard_content += f"- **Tasks Completed:** {tasks_data['done_count']}\n"
    dashboard_content += f"- **Milestones Achieved:** {len(summary['milestones'])}\n\n"

    if summary["metrics"]:
        m = summary["metrics"]
        dashboard_content += "### 📊 Technical ROI (Engineering Metrics)\n"
        dashboard_content += (
            f"- **Engineering Velocity:** {m['velocity']:.2f} tasks/milestone\n"
        )
        dashboard_content += (
            f"- **Architectural Density:** {m['density']:.2f} ADRs/milestone\n"
        )
        dashboard_content += f"- **Knowledge Base Growth:** {m['kb_total']} records\n"
        dashboard_content += f"- **Completion Ratio:** {m['completion_ratio']:.1f}%\n\n"

    dashboard_content += "## ✅ Recent Milestones\n"
    if summary["milestones"]:
        for milestone in summary["milestones"]:
            dashboard_content += f"{milestone}\n"
        dashboard_content += "\n"

    with open(os.path.join(project_dir, output_file), "w") as f:
        f.write(dashboard_content)
    return True
