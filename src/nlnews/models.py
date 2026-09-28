from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Article(BaseModel):
    id: str
    source: str
    lang: str
    section: str
    weight: float
    url: str
    title: str
    summary: str
    published: datetime | None = None
    full_text: str | None = None


# --- Curation pass 1: pick stories from headlines ---------------------------------

class StoryPick(BaseModel):
    working_title: str = Field(description="Short English label for the story")
    section: str = Field(description="One of: amsterdam, national, politics, business, culture, sport, science, tech, offbeat, world")
    kind: Literal["hard", "light"] = Field(description="hard = consequential news; light = culture, pop culture, sport, science, or offbeat")
    article_ids: list[str] = Field(description="IDs of every article covering this story")
    rationale: str = Field(description="One sentence on why it made the cut")


class StorySelection(BaseModel):
    stories: list[StoryPick]


# --- Curation pass 2: written briefing ---------------------------------------------

class Story(BaseModel):
    headline: str
    section: str
    kind: Literal["hard", "light"] = Field(default="hard", description="Copied from the story's header")
    summary: str = Field(description="3-6 sentence English summary of what happened")
    context: str = Field(description="Background a newcomer to the Netherlands needs: who the people/parties/institutions are, why it matters")
    key_terms: list[str] = Field(description="Dutch names/terms worth hearing pronounced, e.g. 'Tweede Kamer (House of Representatives)'")
    sources: list[str] = Field(description="Source outlet names used")
    urls: list[str]
    open_questions: list[str] = Field(default=[], description="Facts a listener would want that the articles leave out, or where outlets disagree")
    findings: list["Finding"] = Field(default=[], description="Filled in by the research pass; leave empty")


class Finding(BaseModel):
    question: str
    answer: str = Field(description="What reliable sources say; empty if it couldn't be confirmed")
    sources: list[str] = Field(description="URLs that support the answer")


class ResearchedStory(BaseModel):
    summary: str = Field(description="The story's summary, revised with what the research found")
    context: str = Field(description="The story's context, revised only if the research changes it")
    findings: list[Finding] = Field(description="One per open question, answered or not")


class Event(BaseModel):
    name: str = Field(description="Plain English name of the event or exhibition")
    when: str = Field(description="Day(s) and time if known, e.g. 'Sunday 4 October, from 11:00'")
    where: str = Field(description="Venue and neighbourhood, e.g. 'Hotel de Goudfazant, Amsterdam-Noord'")
    price: str = Field(default="", description="e.g. 'free', 'from €10'; empty if the source doesn't say")
    blurb: str = Field(description="1-2 sentences on what it is and why a newcomer might go")
    note: str = Field(default="", description="Practical flag if any: 'free ticket required', 'mostly in Dutch', 'nearly sold out', 'final weekend'")
    source: str


class Agenda(BaseModel):
    window: str = Field(description="The days covered, e.g. 'Thursday 1 to Sunday 4 October' or 'Wednesday 30 September'")
    events: list[Event]


class Shortlist(BaseModel):
    ids: list[str] = Field(description="Bracketed IDs of the shortlisted events, best first")


class Briefing(BaseModel):
    date: str
    top_line: str = Field(description="One-sentence summary of the day's biggest news")
    stories: list[Story]
    agenda: Agenda | None = None  # "What's on in Amsterdam" picks, added after the briefing


# --- Episode script ----------------------------------------------------------------

class Line(BaseModel):
    speaker: str
    text: str
    style: str = Field(default="", description="Optional delivery note, e.g. 'wry', 'serious'")


class Segment(BaseModel):
    title: str
    lines: list[Line]


class EpisodeScript(BaseModel):
    episode_title: str
    description: str = Field(description="2-3 sentence podcast episode description")
    segments: list[Segment]
