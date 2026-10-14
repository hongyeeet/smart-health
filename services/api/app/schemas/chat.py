"""API shapes of the chat (screen I1). camelCase on the wire, like the other routers."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.medicines import Camel

MAX_TEXT = 500   # characters a person can send in one message

ReplyKind = Literal["answer", "urgent", "refused", "unavailable", "empty", "help"]


class SendIn(Camel):
    text: str = Field(min_length=1, max_length=2000)   # trimmed and cut to MAX_TEXT by the service
    conversation_id: str | None = None


class RouteIn(Camel):
    text: str = Field(min_length=1, max_length=2000)


class RouteOut(Camel):
    """What kind of request a message is, for the waiting message only: urgent, safety, quick, ideas, food, knowledge or personal."""
    route: Literal["urgent", "safety", "quick", "ideas", "food", "knowledge", "personal"]


class Source(Camel):
    label: str
    to: str          # a route id of the app, such as C2
    detail: str | None = None


class Action(Camel):
    kind: Literal["open", "doctor_question"]
    label: str
    to: str | None = None      # route id to open (kind open)
    text: str | None = None    # the person's own words to add to the doctor questions (kind doctor_question)


class ChatMessage(Camel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    kind: ReplyKind | None = None
    at: str


class SendOut(Camel):
    conversation_id: str
    message: ChatMessage
    reply: ChatMessage
    sources: list[Source]
    actions: list[Action]
    follow_ups: list[str]


class Conversation(Camel):
    id: str
    messages: list[ChatMessage]


class Starters(Camel):
    starters: list[str]


class QuestionIn(Camel):
    text: str = Field(min_length=1, max_length=500)


class QuestionOut(Camel):
    id: str
    text: str
