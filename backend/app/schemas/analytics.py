from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    today_reminders: int
    dead_letter_reminders: int
    upcoming_reminders: int
    delivery_rate: float | None
    avg_retry_count: float
    queue_size: int
    worker_healthy: bool
