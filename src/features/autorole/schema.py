from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AutoRoleSchema(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    guild_id: int
    role_id: int
