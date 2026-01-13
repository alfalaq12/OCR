"""
Service untuk handle koneksi ke MinIO (object storage).
Dipake buat ambil file dari bucket MinIO.
"""

from minio import Minio
from minio.error import S3Error
from app.config import settings
import io


class MinioService:
    """Handle semua operasi ke MinIO storage"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Minio:
        """Bikin koneksi ke MinIO kalo belum ada"""
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
        return self._client

    def ambil_file(self, bucket: str, nama_object: str) -> bytes:
        """Download file dari MinIO, return sebagai bytes"""
        try:
            response = self.client.get_object(bucket, nama_object)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            raise Exception(f"Gagal ambil file dari MinIO: {e}")

    def cek_file_ada(self, bucket: str, nama_object: str) -> bool:
        """Cek apakah file ada di bucket"""
        try:
            self.client.stat_object(bucket, nama_object)
            return True
        except S3Error:
            return False

    def cek_koneksi(self) -> bool:
        """Test koneksi ke MinIO"""
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False

    # alias biar compatible
    def get_object_bytes(self, bucket, object_key):
        return self.ambil_file(bucket, object_key)
    
    def check_object_exists(self, bucket, object_key):
        return self.cek_file_ada(bucket, object_key)
    
    def check_connection(self):
        return self.cek_koneksi()


# singleton instance
minio_service = MinioService()
