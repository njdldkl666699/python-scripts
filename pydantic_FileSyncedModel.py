import hashlib
import threading
import time
from pathlib import Path
from typing import override

from loguru import logger
from pydantic import BaseModel, Field
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class Ptr[T]:
    """指针类，用于持有可变对象的引用"""

    def __init__(self, v: T):
        self.v = v


def md5(p: Path):
    return hashlib.md5(p.read_bytes()).hexdigest()


def md5_str(s: str):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


class FileSyncedModel(BaseModel):
    """
    支持从文件加载、显式保存到文件的模型。

    用法：
    >>> # 从文件加载（文件不存在时用默认值并保存）
        model = MyModel.from_file(Path("config.json"))
        # 修改字段
        model.name = "new_name"
        # 显式保存到文件
        model.save()
    """

    file_path: Path | None = Field(default=None, exclude=True)
    """绑定的文件路径，用于保存和哈希计算"""

    file_hash: str = Field(default="", exclude=True)
    """文件的 MD5 哈希，用于检测外部变更"""

    @classmethod
    def from_file(cls, file_path: Path):
        """从 JSON 文件加载模型，文件不存在时使用默认值并保存"""
        if not file_path.exists():
            logger.warning(f"模型文件 {file_path} 不存在，使用默认值并保存到文件")
            model = cls(file_path=file_path)
            model.save()  # 保存默认模型到文件
            return model

        model = cls.model_validate_json(file_path.read_text(encoding="utf-8"))
        # 设置文件信息并更新哈希（避免后续监听误判）
        model.file_path = file_path
        model.file_hash = md5(file_path)
        return model

    def save(self):
        """将当前模型保存为 JSON 文件。"""
        p = self.file_path
        if p is None:
            raise ValueError("未指定保存路径，请设置 file_path 字段")

        config_json = self.model_dump_json(indent=2, ensure_ascii=False)
        self.file_hash = md5_str(config_json)  # 更新哈希以反映当前内容

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(config_json, encoding="utf-8")


class ModelReloadHandler[M: FileSyncedModel](FileSystemEventHandler):
    """监听模型文件的修改事件，自动重新加载模型并更新指针"""

    def __init__(self, model_ptr: Ptr[M]):
        super().__init__()
        self._model_ptr = model_ptr

    @override
    def on_modified(self, event):
        try:
            if event.is_directory:
                return

            src_path = event.src_path
            if not isinstance(src_path, str):
                src_path = src_path.decode()  # pyright: ignore[reportAttributeAccessIssue]

            model = self._model_ptr.v
            file_path = model.file_path
            if file_path is None or file_path.resolve() != Path(src_path).resolve():
                return

            new_hash = md5(file_path)
            if new_hash == model.file_hash:
                return

            logger.info(f"模型文件 {file_path} 已修改，重新加载模型")
            new_model = model.from_file(file_path)
            logger.debug(f"新模型内容: {new_model}")
            self._model_ptr.v = new_model
        except Exception as e:
            logger.exception(f"重新加载模型失败: {e}")


observer = Observer()


def watch_file(file_path: Path, handler: ModelReloadHandler):
    """监控指定的文件，当文件被修改时触发事件处理器"""
    logger.debug(f"开始监控模型文件 {file_path}")
    observer.schedule(handler, str(file_path.parent))


def watch_observer():
    """测试代码，用于验证 watchdog 是否正常工作"""
    while True:
        if not observer.is_alive():
            logger.error("文件监控线程已停止")
            break
        time.sleep(5)


class ExampleModel(FileSyncedModel):
    name: str = "default_name"
    value: int = 42


example_model_file_path = Path("example_model.json")
"""示例模型的文件路径"""

example_model_ptr = Ptr(ExampleModel.from_file(example_model_file_path))
"""示例模型的指针，用于持有当前加载的模型实例"""

example_model_handler = ModelReloadHandler(example_model_ptr)
"""示例模型的文件修改事件处理器"""

# 配置对这个文件的监控
watch_file(example_model_file_path, example_model_handler)


if __name__ == "__main__":
    try:
        observer.start()
        threading.Thread(target=watch_observer, daemon=True).start()
        logger.info("模型文件监控已启动")
        observer.join()  # 阻塞主线程，直到监控线程结束
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止模型文件监控")
    finally:
        observer.stop()
        logger.info("模型文件监控已停止")
