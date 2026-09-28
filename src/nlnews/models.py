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


class Briefing(BaseModel):
    date: str
    top_line: str = Field(description="One-sentence summary of the day's biggest news")
    stories: list[Story]


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
