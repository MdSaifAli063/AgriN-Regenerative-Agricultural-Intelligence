import datetime
import uuid
from typing import Dict, Tuple
from minio import Minio
from app.core.config import settings


class StorageService:
    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.secure = settings.MINIO_SECURE
        self.bucket = settings.MINIO_BUCKET_NAME
        # Alias used by the disease router
        self.MINIO_BUCKET = self.bucket

        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region="us-east-1",
            )
        except Exception:
            self.client = None


    def ensure_bucket_exists(self) -> bool:
        if not self.client:
            return False
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
            return True
        except Exception:
            return False

    def generate_presigned_upload(
        self, content_type: str, expires_in_seconds: int = 900
    ) -> Tuple[str, str, Dict[str, str]]:
        """
        Generates random UUID object key and presigned upload URL.
        Guarantees no user-supplied paths are used.
        """
        extension = "jpg"
        if "png" in content_type:
            extension = "png"
        elif "webp" in content_type:
            extension = "webp"

        object_key = f"uploads/{datetime.date.today().isoformat()}/{uuid.uuid4()}.{extension}"

        if not self.client or settings.DEMO_MODE:
            # Deterministic signed mock URL for offline/demo/test execution
            mock_url = f"http://{self.endpoint}/{self.bucket}/{object_key}?mock_token=presigned_demo"
            return mock_url, object_key, {"Content-Type": content_type}

        try:
            url = self.client.get_presigned_url(

                "PUT",
                self.bucket,
                object_key,
                expires=datetime.timedelta(seconds=expires_in_seconds),
            )
            return url, object_key, {"Content-Type": content_type}
        except Exception:
            mock_url = f"http://{self.endpoint}/{self.bucket}/{object_key}?mock_token=presigned_demo"
            return mock_url, object_key, {"Content-Type": content_type}

    def generate_presigned_download(self, object_key: str, expires_in_seconds: int = 3600) -> str:
        if not self.client:
            return f"http://{self.endpoint}/{self.bucket}/{object_key}"
        try:
            return self.client.get_presigned_url(
                "GET",
                self.bucket,
                object_key,
                expires=datetime.timedelta(seconds=expires_in_seconds),
            )
        except Exception:
            return f"http://{self.endpoint}/{self.bucket}/{object_key}"

    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: str = "image/png",
    ) -> str:
        """Uploads raw bytes to MinIO and returns a download URL or mock URL in demo mode."""
        if not self.client or settings.DEMO_MODE:
            return f"http://{self.endpoint}/{self.bucket}/{object_key}?mock_token=presigned_demo"
        try:
            from io import BytesIO
            self.ensure_bucket_exists()
            self.client.put_object(
                self.bucket,
                object_key,
                BytesIO(data),
                len(data),
                content_type=content_type,
            )
            return self.generate_presigned_download(object_key)
        except Exception:
            return f"http://{self.endpoint}/{self.bucket}/{object_key}?mock_token=presigned_demo"


    def put_object(
        self,
        key: str,
        data,
        content_type: str = "image/jpeg",
        length: int = -1,
    ) -> str:
        """PUT object into MinIO. Returns object URI. Falls back to demo URI."""
        if not self.client or settings.DEMO_MODE:
            return f"s3://{self.bucket}/{key}"
        try:
            self.ensure_bucket_exists()
            self.client.put_object(
                self.bucket, key, data, length, content_type=content_type
            )
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            return f"s3://{self.bucket}/{key}"  # best-effort

    def get_object_bytes(self, key: str) -> bytes:
        """GET object bytes from MinIO. Raises on failure."""
        if not self.client or settings.DEMO_MODE:
            raise FileNotFoundError(f"Demo mode: cannot fetch {key} from MinIO")
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, key: str) -> bool:
        """Deletes a single object from MinIO. Returns True on success or in demo mode."""
        if not self.client or settings.DEMO_MODE:
            return True
        try:
            self.client.remove_object(self.bucket, key)
            return True
        except Exception:
            return False

    def delete_objects(self, keys: list) -> int:
        """Deletes multiple objects from MinIO."""
        if not keys:
            return 0
        if not self.client or settings.DEMO_MODE:
            return len(keys)
        try:
            from minio.deleteobjects import DeleteObject
            delete_object_list = [DeleteObject(k) for k in keys]
            errors = self.client.remove_objects(self.bucket, delete_object_list)
            err_count = sum(1 for _ in errors)
            return len(keys) - err_count
        except Exception:
            return 0


storage_service = StorageService()

