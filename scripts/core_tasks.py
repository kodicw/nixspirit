# Context: [[nb:knowledge:adr-57]], [[nb:knowledge:adr-2]], [[nb:knowledge:adr-62]], [[nb:knowledge:adr-66]]
import re
from typing import Dict, Any, Optional, List

import core_logic as core
import constants
from core_memory_interface import get_memory_client


def _get_granular_tasks() -> List[Dict[str, Any]]:
    """Fetches all granular tasks from nb using status tags for efficiency."""
    client = get_memory_client()
    tasks_list = []

    # Fetch tasks by status to avoid listing everything
    for status_suffix in ["active", "backlog", "completed", "proposal"]:
        status_tag = f"status:{status_suffix}"
        notes = client.ls(tags=[constants.TAG_TASK, status_tag])

        for note in notes:
            # Exclude notes that are clearly not individual tasks
            if (
                "ADR:" in note.title
                or "Task Board" in note.title
                or "Vision" in note.title
            ):
                continue

            # Fetch full content (cached in NbClient if called multiple times)
            content = client.show(note.id)
            if not content:
                continue

            agent_match = re.search(r"Agent:\s*([^)\n]+)", content)
            agent = agent_match.group(1).strip() if agent_match else None

            tasks_list.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "content": content,
                    "status": status_suffix,
                    "agent": agent,
                }
            )

    def sort_key(t):
        try:
            return int(t["id"].split("/")[-1])
        except (ValueError, TypeError, IndexError):
            return 0

    tasks_list.sort(key=sort_key, reverse=True)
    return tasks_list


def parse_tasks() -> Dict[str, Any]:
    """Parses granular tasks from knowledge base.

    Context: [[nb:knowledge:57]] - Per-Task Note Model
    """
    # 1. Fetch Strategic Vision
    import core_infra as infra

    vision = infra.get_vision()

    data = {
        "active": [],
        "proposal": [],
        "done_count": 0,
        "backlog": [],
        "vision": vision,
        "sections": {
            "header": [],
            "vision": [f"## Strategic Vision\n> {vision}\n"] if vision else [],
            "proposal": ["## Proposed Tasks\n"],
            "active": ["## Active Tasks\n"],
            "backlog": ["## Backlog\n"],
            "completed": ["## ✅ Completed Tasks\n"],
        },
    }

    # 2. Fetch Granular Tasks
    tasks_list = _get_granular_tasks()

    for t in tasks_list:
        agent_str = f" (Agent: {t['agent']})" if t["agent"] else ""
        task_line = f"- [ ] **{t['title']}**{agent_str}"

        if t["status"] == "active":
            data["active"].append(task_line)
            data["sections"]["active"].append(task_line + "\n")
        elif t["status"] == "proposal":
            data["proposal"].append(task_line)
            data["sections"]["proposal"].append(task_line + "\n")
        elif t["status"] == "backlog":
            data["backlog"].append(task_line)
            data["sections"]["backlog"].append(task_line + "\n")
        elif t["status"] == "completed":
            data["done_count"] += 1
            completed_line = f"- [x] **{t['title']}**{agent_str}"
            data["sections"]["completed"].append(completed_line + "\n")

    # 3. Fallback to old Authoritative Task Board if granular tasks are empty
    if not tasks_list:
        import core_infra as infra

        old_tasks = infra.get_note_content(constants.TAG_TASKS_BOARD)
        if old_tasks:
            # Re-use simplified old parsing logic for migration/compatibility
            lines = old_tasks.splitlines(keepends=True)
            current_section = "header"
            re_active = re.compile(r"^##.*active", re.IGNORECASE)
            re_backlog = re.compile(r"^##.*backlog", re.IGNORECASE)
            re_completed = re.compile(r"^##.*(completed|done)", re.IGNORECASE)

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("##"):
                    if re_active.search(stripped):
                        current_section = "active"
                    elif re_backlog.search(stripped):
                        current_section = "backlog"
                    elif re_completed.search(stripped):
                        current_section = "completed"

                if current_section == "active" and re.match(
                    r"^\s*-\s*\[\s*\]", stripped
                ):
                    data["active"].append(stripped)
                elif current_section == "backlog" and re.match(
                    r"^\s*-\s*\[\s*\]", stripped
                ):
                    data["backlog"].append(stripped)
                elif current_section == "completed" and stripped.startswith("-"):
                    data["done_count"] += 1
                elif re.search(r"-\s*\[[xX]\]", stripped):
                    data["done_count"] += 1

    return data


def add_task(
    task_text: str,
    agent: Optional[str] = None,
    backlog: bool = False,
    proposal: bool = False,
) -> bool:
    """Adds a new granular task as an nb note."""
    client = get_memory_client()

    status_tag = constants.STATUS_ACTIVE
    if backlog:
        status_tag = constants.STATUS_BACKLOG
    elif proposal:
        status_tag = constants.STATUS_PROPOSAL

    content = f"Status: {status_tag}\n"
    if agent:
        content += f"Agent: {agent}\n"
    content += f"\nDescription: {task_text}\n"

    tags = ["type:task", status_tag]
    if agent:
        tags.append(f"agent:{agent}")

    new_id = client.add(title=task_text, content=content, tags=tags)
    return new_id is not None


def update_task(
    task_text_search: str,
    new_text: Optional[str] = None,
    agent: Optional[str] = None,
    move_to: Optional[str] = None,
) -> bool:
    """Updates a granular task in nb."""
    client = get_memory_client()
    tasks_list = _get_granular_tasks()

    target_task = None
    for t in tasks_list:
        if task_text_search.lower() in t["title"].lower():
            target_task = t
            break

    if not target_task:
        core.log(f"Granular task matching '{task_text_search}' not found.", "Tasks")
        return False

    # Update content
    new_title = new_text if new_text else target_task["title"]
    final_agent = agent if agent else target_task["agent"]
    final_status = target_task["status"]
    if move_to:
        final_status = move_to  # active, backlog, or proposal

    status_tag = f"status:{final_status}"
    content = f"Status: {status_tag}\n"
    if final_agent:
        content += f"Agent: {final_agent}\n"
    content += f"\nDescription: {new_title}\n"

    tags = ["type:task", status_tag]
    if final_agent:
        tags.append(f"agent:{final_agent}")

    return client.edit(target_task["id"], content=content, title=new_title, tags=tags)


def complete_task(task_text_search: str) -> bool:
    """Marks a granular task as completed."""
    client = get_memory_client()
    tasks_list = _get_granular_tasks()

    target_task = None
    for t in tasks_list:
        if task_text_search.lower() in t["title"].lower():
            target_task = t
            break

    if not target_task:
        core.log(
            f"Granular task matching '{task_text_search}' not found for completion.",
            "Tasks",
        )
        return False

    status_tag = constants.STATUS_COMPLETED
    content = target_task["content"]
    content = re.sub(r"status:(active|backlog)", status_tag, content)

    tags = ["type:task", status_tag]
    if target_task["agent"]:
        tags.append(f"agent:{target_task['agent']}")

    return client.edit(target_task["id"], content=content, tags=tags)


def get_task_board_markdown() -> str:
    """Returns the aggregated task board as a markdown string.

    Context: [[nb:knowledge:adr-2]]
    """
    data = parse_tasks()
    output = []

    if data["vision"]:
        output.append("## Strategic Vision")
        output.append(f"> {data['vision']}\n")

    output.append("## Proposed Tasks")
    if data["proposal"]:
        output.extend([t.strip() for t in data["proposal"]])
    else:
        output.append("No proposed tasks.")
    output.append("")

    output.append("## Active Tasks")
    if data["active"]:
        output.extend([t.strip() for t in data["active"]])
    else:
        output.append("No active tasks.")
    output.append("")

    output.append("## Backlog")
    if data["backlog"]:
        output.extend([t.strip() for t in data["backlog"]])
    else:
        output.append("No backlog items.")
    output.append("")

    # Completed tasks are optional in the agent context to save tokens,
    # but let's include a summary or a few recent ones.
    output.append("## Recently Completed")
    completed = [
        t.strip() for t in data["sections"]["completed"] if t.strip().startswith("-")
    ]
    if completed:
        output.extend(completed[:5])
    else:
        output.append("No recently completed tasks.")

    return "\n".join(output)
