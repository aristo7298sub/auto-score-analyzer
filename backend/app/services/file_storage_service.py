"""
文件存储服务 - 支持本地文件系统和 Azure Blob Storage
"""
import os
import io
from typing import BinaryIO, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

from app.core.config import settings

# 根据配置动态导入
if settings.STORAGE_TYPE == "azure":
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, BlobSasPermissions
    from azure.core.exceptions import ResourceNotFoundError


class FileStorageService:
    """统一的文件存储服务，支持本地和 Azure Blob Storage"""
    
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        
        if self.storage_type == "azure":
            self._init_azure_storage()
        else:
            self._init_local_storage()
    
    def _init_azure_storage(self):
        """初始化 Azure Blob Storage"""
        if not settings.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("Azure Storage 连接字符串未配置")
        
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        
        # 确保容器存在
        self._ensure_containers_exist()
    
    def _init_local_storage(self):
        """初始化本地文件存储"""
        self.local_base_path = Path(".")
        
        # 确保本地目录存在
        for dir_path in [
            settings.LOCAL_UPLOADS_DIR,
            settings.LOCAL_EXPORTS_DIR,
            settings.LOCAL_CHARTS_DIR,
            settings.LOCAL_DATA_DIR
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def _ensure_containers_exist(self):
        """确保 Azure Blob 容器存在"""
        containers = [
            settings.AZURE_STORAGE_UPLOADS_CONTAINER,
            settings.AZURE_STORAGE_EXPORTS_CONTAINER,
            settings.AZURE_STORAGE_CHARTS_CONTAINER
        ]
        
        for container_name in containers:
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                if not container_client.exists():
                    container_client.create_container()
                    print(f"✅ 创建容器: {container_name}")
            except Exception as e:
                print(f"⚠️ 容器 {container_name} 检查失败: {e}")
    
    def _get_container_name(self, file_type: str) -> str:
        """根据文件类型获取容器名称"""
        container_map = {
            "upload": settings.AZURE_STORAGE_UPLOADS_CONTAINER,
            "export": settings.AZURE_STORAGE_EXPORTS_CONTAINER,
            "chart": settings.AZURE_STORAGE_CHARTS_CONTAINER,
        }
        return container_map.get(file_type, settings.AZURE_STORAGE_UPLOADS_CONTAINER)
    
    def _get_local_dir(self, file_type: str) -> str:
        """根据文件类型获取本地目录"""
        dir_map = {
            "upload": settings.LOCAL_UPLOADS_DIR,
            "export": settings.LOCAL_EXPORTS_DIR,
            "chart": settings.LOCAL_CHARTS_DIR,
        }
        return dir_map.get(file_type, settings.LOCAL_UPLOADS_DIR)
    
    async def save_file(
        self, 
        file_content: bytes, 
        filename: str, 
        file_type: str = "upload",
        content_type: Optional[str] = None
    ) -> str:
        """
        保存文件
        
        Args:
            file_content: 文件二进制内容
            filename: 文件名
            file_type: 文件类型 (upload/export/chart)
            content_type: MIME 类型
        
        Returns:
            文件的访问路径或 URL
        """
        if self.storage_type == "azure":
            return await self._save_to_azure(file_content, filename, file_type, content_type)
        else:
            return await self._save_to_local(file_content, filename, file_type)
    
    async def _save_to_azure(
        self, 
        file_content: bytes, 
        filename: str, 
        file_type: str,
        content_type: Optional[str]
    ) -> str:
        """保存文件到 Azure Blob Storage"""
        container_name = self._get_container_name(file_type)
        
        # 添加时间戳前缀避免重名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{timestamp}_{filename}"
        
        blob_client = self.blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # 上传文件
        from azure.storage.blob import ContentSettings
        
        content_settings = ContentSettings(content_type=content_type) if content_type else None
        
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings
        )
        
        # 返回 Blob URL
        return blob_client.url
    
    async def _save_to_local(
        self, 
        file_content: bytes, 
        filename: str, 
        file_type: str
    ) -> str:
        """保存文件到本地文件系统"""
        local_dir = self._get_local_dir(file_type)
        
        # 添加时间戳前缀避免重名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        
        file_path = Path(local_dir) / safe_filename
        
        # 写入文件
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 返回相对路径
        return str(file_path)
    
    async def read_file(self, file_path: str, file_type: str = "upload") -> bytes:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径（本地）或 blob 名称（Azure）
            file_type: 文件类型
        
        Returns:
            文件二进制内容
        """
        if self.storage_type == "azure":
            return await self._read_from_azure(file_path, file_type)
        else:
            return await self._read_from_local(file_path)
    
    async def _read_from_azure(self, blob_name: str, file_type: str) -> bytes:
        """从 Azure Blob Storage 读取文件"""
        container_name = self._get_container_name(file_type)
        
        blob_client = self.blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        try:
            downloader = blob_client.download_blob()
            return downloader.readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"文件不存在: {blob_name}")
    
    async def _read_from_local(self, file_path: str) -> bytes:
        """从本地文件系统读取文件"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(path, "rb") as f:
            return f.read()
    
    async def delete_file(self, file_path: str, file_type: str = "upload") -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径（本地）或 blob 名称（Azure）
            file_type: 文件类型
        
        Returns:
            是否删除成功
        """
        if self.storage_type == "azure":
            return await self._delete_from_azure(file_path, file_type)
        else:
            return await self._delete_from_local(file_path)
    
    async def _delete_from_azure(self, blob_name: str, file_type: str) -> bool:
        """从 Azure Blob Storage 删除文件"""
        container_name = self._get_container_name(file_type)
        
        blob_client = self.blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        try:
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
    
    async def _delete_from_local(self, file_path: str) -> bool:
        """从本地文件系统删除文件"""
        path = Path(file_path)
        
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def list_files(self, file_type: str = "upload", prefix: str = "") -> List[str]:
        """
        列出文件
        
        Args:
            file_type: 文件类型
            prefix: 文件名前缀过滤
        
        Returns:
            文件路径列表
        """
        if self.storage_type == "azure":
            return await self._list_azure_blobs(file_type, prefix)
        else:
            return await self._list_local_files(file_type, prefix)
    
    async def _list_azure_blobs(self, file_type: str, prefix: str) -> List[str]:
        """列出 Azure Blob Storage 中的文件"""
        container_name = self._get_container_name(file_type)
        
        container_client = self.blob_service_client.get_container_client(container_name)
        
        blob_list = []
        for blob in container_client.list_blobs(name_starts_with=prefix):
            blob_list.append(blob.name)
        
        return blob_list
    
    async def _list_local_files(self, file_type: str, prefix: str) -> List[str]:
        """列出本地文件系统中的文件"""
        local_dir = Path(self._get_local_dir(file_type))
        
        if not local_dir.exists():
            return []
        
        files = []
        for file_path in local_dir.glob(f"{prefix}*"):
            if file_path.is_file():
                files.append(str(file_path))
        
        return files
    
    def generate_download_url(
        self, 
        file_path: str, 
        file_type: str = "export",
        expiry_hours: int = 24
    ) -> str:
        """
        生成临时下载 URL（仅 Azure）
        
        Args:
            file_path: Blob 名称
            file_type: 文件类型
            expiry_hours: 过期时间（小时）
        
        Returns:
            临时下载 URL
        """
        if self.storage_type != "azure":
            # 本地模式返回相对路径
            return f"/files/{file_type}/{Path(file_path).name}"
        
        container_name = self._get_container_name(file_type)
        blob_name = Path(file_path).name
        
        # 生成 SAS token
        sas_token = generate_blob_sas(
            account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
            container_name=container_name,
            blob_name=blob_name,
            account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        blob_url = f"{settings.AZURE_STORAGE_BLOB_ENDPOINT}{container_name}/{blob_name}?{sas_token}"
        return blob_url


# 全局实例
file_storage = FileStorageService()
