from typing import TypedDict, List, Dict

class StudyState(TypedDict):
    subjects: List[str]
    exam_date: str
    hours_per_day: float
    plan: List[Dict]
