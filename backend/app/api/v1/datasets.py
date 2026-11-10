import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status

from app.api.deps import DB
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import RateLimiter, client_key
from app.schemas.dataset import (
    DatasetDetail,
    DatasetOut,
    DetectionRunResult,
    SampleInfo,
    UploadResult,
)
from app.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])
upload_limiter = RateLimiter(get_settings().upload_rate_limit_per_minute)


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: DB):
    return dataset_service.list_datasets(db)


@router.get("/samples", response_model=list[SampleInfo])
def list_samples():
    return dataset_service.list_samples()


@router.post("/samples/{key}", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
def load_sample(key: str, db: DB, request: Request):
    upload_limiter.check(client_key(request))
    return dataset_service.import_sample(db, key)


@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
async def upload(
    request: Request,
    db: DB,
    file: Annotated[UploadFile, File(description=".log or .txt, max 5 MB")],
    source_type: Annotated[Literal["NGINX", "SSH", "AUTO"], Form()] = "AUTO",
    name: Annotated[str | None, Form(max_length=150)] = None,
):
    upload_limiter.check(client_key(request))
    max_bytes = get_settings().max_upload_bytes
    # Read at most max+1 bytes so an oversized upload is rejected without
    # buffering arbitrarily large bodies in memory.
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AppError(
            413,
            "FILE_TOO_LARGE",
            f"The file exceeds the {max_bytes / 1024 / 1024:.0f} MB limit. Split it and upload smaller parts.",
        )
    return dataset_service.import_dataset(
        db, filename=file.filename, data=data, source_type=source_type, name=name
    )


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: uuid.UUID, db: DB):
    return dataset_service.dataset_detail(db, dataset_id)


@router.post("/{dataset_id}/detect", response_model=DetectionRunResult)
def rerun_detection(dataset_id: uuid.UUID, db: DB):
    return dataset_service.rerun_detection(db, dataset_id)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: uuid.UUID, db: DB):
    dataset_service.delete_dataset(db, dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
