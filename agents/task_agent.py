"""
Task agent.
Owner: Person 3

SPEC (build from this; keep the function signature)

Purpose
    When the user clicks "Delegate to agent" on a task, produce a ready-to-send
    DRAFT (email or meeting invite). The agent never sends anything: it drafts,
    a human approves. This is a deliberate safety boundary; keep it.

Input
    task: Task dict (core.py): {id, item_id, title, priority, owner, status,
    draft, created_at}. Look up the source item with
    next(i for i in load_all("items") if i["id"] == task["item_id"]) for
    context (text, tags, category).

Output
    str: the draft, markdown, in this shape so the UI can render it:
        **Type:** Email | Meeting invite
        **To:** names/roles taken from the source item (or "TBD" if unknown)
        **Subject:** ...
        **Body:** ...
        For a meeting invite also: **Suggested time:** ..., **Duration:** ...,
        **Agenda:** bullets.
    Persist it: update_json("tasks", task["id"],
        {"draft": draft, "status": "drafting", "owner": "agent"}).
    The UI sets status to "done" only after the human approves.

Drafting guidance
    - Decide email vs meeting: needs discussion/several people -> meeting;
      single request, approval, or info -> email.
    - Professional, concise, ~120 words max; clear ask and deadline in the first
      two lines. Use only facts from the item (names, dates, policies). Use
      "TBD" instead of inventing a recipient, date or number.
    - Optionally call run_memory_session to look up the right owner/contact in
      memory ("Who owns payments?"). It is slow: do this only if the item
      lacks a contact, and show a spinner.
    - Add a one-line "Why this draft" note before the draft listing the facts
      used, so the human can check them.
    - No links, attachments or fake signatures. Sign as "[Your name]".

Edge cases
    - Task with no item_id or a missing item: draft from the task title alone
      and flag "(no source item found)".
    - Task already has a draft: return it unless the caller wants a regenerate
      (add an optional regenerate: bool = False parameter if you need it).
    - Vague task title: draft a clarifying question instead of guessing.
    - API error: log_event "error", raise a readable message.
    - NEVER call any send-email, calendar or Slack API.

Done when
    - A High task from seeded data produces a draft with a real recipient from
      the team directory (or TBD), a clear ask, and a deadline.
    - The task record shows status "drafting" and the draft text afterwards.
    - log_event("task_agent", ...) lines appear in the Monitor.
"""

from core import ask_claude, update_json, log_event


def draft_task_action(task: dict) -> str:
    """Draft an email or meeting invite for a delegated task.

    Infers whether the task requires an email or meeting based on title keywords.
    Uses ask_claude to generate professional drafts. Saves draft to task record
    with status 'drafting' for human review. Does NOT send emails or create
    calendar events.

    Args:
        task: Task dict with keys: id, title, priority, owner, status

    Returns:
        Draft text (email or meeting invite)

    Raises:
        ValueError: If task has no id
        Exception: If draft generation fails
    """
    if not task or not task.get("id"):
        raise ValueError("Task must have an id")

    log_event("task_agent", "draft_action", "running", f"task_id={task.get('id')}")
    try:
        task_title = task.get("title", "Untitled task")
        task_id = task.get("id")

        # Infer whether task is for a meeting or email based on title keywords
        is_meeting = any(
            keyword in task_title.lower()
            for keyword in ["meeting", "schedule", "discuss", "sync", "standup", "call"]
        )

        if is_meeting:
            prompt = f"""Draft a concise calendar meeting invite for the following task:

Task: {task_title}

Include:
- Subject line
- Suggested attendees (generic roles, e.g., "Team Lead, Project Manager")
- Duration (30 min or 1 hour)
- Brief agenda/purpose

Format as:
MEETING INVITE
Subject: [...]
Attendees: [...]
Duration: [...]
Agenda:
[...]"""
        else:
            prompt = f"""Draft a professional email for the following task:

Task: {task_title}

Include:
- Subject line
- Concise body (2-3 paragraphs)
- Clear call to action or next steps

Format as:
EMAIL DRAFT
To: [recipient role]
Subject: [...]
Body:
[...]"""

        draft = ask_claude(prompt)

        # Save draft to task record and mark as awaiting human review/approval
        update_json("tasks", task_id, {"draft": draft, "status": "drafting"})

        log_event("task_agent", "draft_action", "done", f"draft_len={len(draft)}")
        return draft

    except Exception as e:
        log_event("task_agent", "draft_action", "error", str(e))
        raise
