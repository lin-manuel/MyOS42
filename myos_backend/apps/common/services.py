from django.core.files.uploadedfile import UploadedFile


class FileSecurityService:
    @staticmethod
    def scan(uploaded_file: UploadedFile):
        return {
            "file_name": getattr(uploaded_file, "name", ""),
            "status": "clean",
            "engine": "stub",
        }
