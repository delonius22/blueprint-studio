"""T-01: the graph seam works with two scripted fake models before any feature exists."""

from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from seam import GraphSeam


async def test_interview_model_answers_and_the_thread_keeps_history() -> None:
    interview = ScriptedChatModel.with_script(
        AIMessage("Who are the users?"), AIMessage("What read/write ratio?"), name="interview"
    )
    review = ScriptedChatModel.with_script(name="review")
    seam = GraphSeam(interview, review)

    await seam.send("Design a URL shortener")
    await seam.send("Mostly anonymous web users")

    assert [m.text for m in await seam.messages()] == [
        "Design a URL shortener",
        "Who are the users?",
        "Mostly anonymous web users",
        "What read/write ratio?",
    ]
    assert [type(m) for m in interview.calls[1].messages] == [
        SystemMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert review.calls == []


async def test_threads_are_independent() -> None:
    interview = ScriptedChatModel.with_script(AIMessage("a"), AIMessage("b"))
    seam = GraphSeam(interview, ScriptedChatModel.with_script())

    await seam.send("first", thread_id="s1")
    await seam.send("second", thread_id="s2")

    assert [m.text for m in await seam.messages("s1")] == ["first", "a"]
    assert [m.text for m in await seam.messages("s2")] == ["second", "b"]
