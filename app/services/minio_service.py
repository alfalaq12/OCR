from minio import Minio
from minio.error import S3Error
from app.config import settings
import io


class MinioService:
    """Service for MinIO object storage operations"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Minio:
        """Get or create MinIO client"""
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
        return self._client

    def get_object_bytes(self, bucket: str, object_key: str) -> bytes:
        """Download object from MinIO and return as bytes"""
        try:
            response = self.client.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise Exception(f"Failed to get object from MinIO: {e}")

    def check_object_exists(self, bucket: str, object_key: str) -> bool:
        """Check if object exists in bucket"""
        try:
            self.client.stat_object(bucket, object_key)
            return True
        except S3Error:
            return False

    def check_connection(self) -> bool:
        """Check if MinIO is accessible"""
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False


# Singleton instance
minio_service = MinioService()
