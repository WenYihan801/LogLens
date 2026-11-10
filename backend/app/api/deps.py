from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db

DB = Annotated[Session, Depends(get_db)]
PageNo = Annotated[int, Query(ge=1, description="1-based page number")]
PageSize = Annotated[int, Query(ge=1, le=200, description="Items per page (max 200)")]
