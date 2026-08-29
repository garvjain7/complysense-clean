"""MongoDB storage probe for ComplySense.

Run from the repository root:
    python -m backend.check_mongodb_storage

The probe verifies:
1. MongoDB connection via ping.
2. Metadata document write/read/delete in MONGODB_DOCUMENTS_COLLECTION.
3. Control library document write/read/delete in MONGODB_CONTROL_LIBRARY_COLLECTION.
4. Evidence file byte upload/read/delete via MongoDB GridFS bucket `evidence_files`.

It cleans up all probe records before exiting.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATHS = (ROOT_DIR / ".env", Path(__file__).resolve().parent / ".env")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        for path in ENV_PATHS:
            _load_env_file(path)
        return

    for path in ENV_PATHS:
        if path.exists():
            load_dotenv(path, override=False)


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required. Define it in .env or the shell environment.")
    return value


async def main() -> int:
    load_env()

    mongodb_uri = required_env("MONGODB_URI")
    database_name = os.environ.get("MONGODB_DATABASE", "complysense")
    documents_collection = os.environ.get("MONGODB_DOCUMENTS_COLLECTION", "documents")
    control_collection = os.environ.get("MONGODB_CONTROL_LIBRARY_COLLECTION", "control_library")

    client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=10000)
    database = client[database_name]
    probe_id = f"mongodb-storage-probe-{uuid4()}"
    now = datetime.now(UTC)

    document_id: ObjectId | None = None
    control_id: ObjectId | None = None
    gridfs_id: ObjectId | None = None

    try:
        ping = await database.command("ping")
        print(f"[ok] MongoDB ping: {ping}")

        document_result = await database[documents_collection].insert_one(
            {
                "institution_id": "probe",
                "source_type": "storage_probe",
                "source_id": probe_id,
                "metadata": {"probe_id": probe_id, "purpose": "documents collection write/read check"},
                "extracted_text": "ComplySense MongoDB documents collection probe.",
                "created_at": now,
                "updated_at": now,
            }
        )
        document_id = document_result.inserted_id
        document = await database[documents_collection].find_one({"_id": document_id})
        if not document or document.get("source_id") != probe_id:
            raise RuntimeError("Documents collection probe write/read failed.")
        print(f"[ok] Documents collection write/read: {documents_collection} _id={document_id}")

        control_result = await database[control_collection].insert_one(
            {
                "control_id": probe_id,
                "framework_name": "storage_probe",
                "title": "MongoDB control library probe",
                "created_at": now,
                "updated_at": now,
            }
        )
        control_id = control_result.inserted_id
        control = await database[control_collection].find_one({"_id": control_id})
        if not control or control.get("control_id") != probe_id:
            raise RuntimeError("Control library probe write/read failed.")
        print(f"[ok] Control library write/read: {control_collection} _id={control_id}")

        bucket = AsyncIOMotorGridFSBucket(database, bucket_name="evidence_files")
        payload = b"ComplySense MongoDB GridFS evidence probe.\n"
        gridfs_id = await bucket.upload_from_stream(
            f"{probe_id}.txt",
            payload,
            metadata={
                "probe_id": probe_id,
                "institution_id": "probe",
                "content_type": "text/plain",
            },
        )
        stream = await bucket.open_download_stream(gridfs_id)
        downloaded = await stream.read()
        if downloaded != payload:
            raise RuntimeError("GridFS evidence upload/download content mismatch.")
        print(f"[ok] GridFS evidence upload/read: evidence_files _id={gridfs_id}")

        return 0
    finally:
        cleanup_errors: list[str] = []
        if document_id is not None:
            result = await database[documents_collection].delete_one({"_id": document_id})
            if result.deleted_count != 1:
                cleanup_errors.append(f"documents _id={document_id}")
        if control_id is not None:
            result = await database[control_collection].delete_one({"_id": control_id})
            if result.deleted_count != 1:
                cleanup_errors.append(f"control_library _id={control_id}")
        if gridfs_id is not None:
            try:
                await AsyncIOMotorGridFSBucket(database, bucket_name="evidence_files").delete(gridfs_id)
            except Exception as exc:  # noqa: BLE001 - report cleanup failure explicitly
                cleanup_errors.append(f"gridfs _id={gridfs_id}: {exc}")

        client.close()

        if cleanup_errors:
            print(f"[warn] Cleanup incomplete: {', '.join(cleanup_errors)}")
        else:
            print("[ok] Probe cleanup complete.")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
