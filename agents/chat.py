"""
Chat agent.
Owner: Person 3

Answers questions using the memory store.
Uses run_memory_session for persistence.
"""

from core import run_memory_session, log_event


def chat(question: str) -> str:
    """Answer a question using institutional memory."""
    if not question or not question.strip():
        return "Please ask a question."

    log_event("chat", "answer", "running", f"question={question[:50]}")
    try:
        # Use memory session for knowledge search + context
        prompt = f"""You are a helpful assistant with access to institutional memory.
Answer the following question based on the information in memory, including team policies, recent decisions, and documented processes.

Question: {question}

Provide a clear, concise answer. If you don't have information to answer, say so."""

        response = run_memory_session(prompt, title=f"Chat: {question[:50]}")
        log_event("chat", "answer", "done")
        return response

    except Exception as e:
        log_event("chat", "answer", "error", str(e))
        raise
