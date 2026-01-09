from typing import Any, Dict, List, Optional
import msgpack


class BaseStructure:
    """
    Base class for all structures.
    Holds raw data and provides msgpack encode/decode helpers.
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self.validate()

    def validate(self) -> None:
        """Override in subclasses to enforce structure."""

    def to_dict(self) -> Dict[str, Any]:
        return self._data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(data)

    def encode_msgpack(self) -> bytes:
        return msgpack.packb(self._data, use_bin_type=True)

    @classmethod
    def decode_msgpack(cls, payload: bytes):
        data = msgpack.unpackb(payload, raw=False)
        return cls.from_dict(data)

    @staticmethod
    def encode_list(items: List["BaseStructure"]) -> bytes:
        return msgpack.packb(
            [item.to_dict() for item in items],
            use_bin_type=True,
        )

    @classmethod
    def decode_list(cls, payload: bytes) -> List["BaseStructure"]:
        data = msgpack.unpackb(payload, raw=False)
        return [cls.from_dict(item) for item in data]


class Task(BaseStructure):
    """
    Task Structure
    {
        "task_uuid": "1234",
        "implant_uuid": 9999,
        "task": {
            "name": "cmd",
            "args": {
            "cli": "whoami"
            }
        }
    }

    """

    def validate(self) -> None:
        if "task_uuid" not in self._data:
            raise ValueError("Task missing 'task_uuid'")
        if "implant_uuid" not in self._data:
            raise ValueError("Task missing 'implant_uuid'")
        if "task" not in self._data:
            raise ValueError("Task missing 'task'")

        # Task name is any key except known fields
        task_keys = set(self._data.keys()) - {"task_uuid", "implant_uuid"}
        if len(task_keys) != 1:
            raise ValueError("Task must contain exactly one task definition")

        task_name = next(iter(task_keys))
        if not isinstance(self._data[task_name], dict):
            raise ValueError("Task definition must be a dict")

    @property
    def task_name(self) -> str:
        return next(
            key for key in self._data.keys() if key not in {"task_uuid", "implant_uuid"}
        )

    @property
    def task_args(self) -> Dict[str, Any]:
        return self._data[self.task_name]

    @staticmethod
    def create_task(
        task_uuid: str,
        implant_uuid: str,
        task_name: str,
        task_args: dict,
        convert_to_msgpack: bool = False,
    ) -> dict | bool:
        """
        Create a task payload.

        Builds a task structure containing the task UUID, target implant UUID,
        and task definition.

        Args:
            task_uuid: Unique identifier for the task.
            implant_uuid: Identifier of the intended target implant.
            task_name: Name of the task to execute.
            task_args: Dictionary of task-specific arguments.
            convert_to_msgpack: If True, return the task encoded as msgpack bytes.
                                If False (default), return the task as a Python dict.

        Returns:
            A task payload as a dict, or msgpack-encoded bytes if
            convert_to_msgpack is True.
        """

        task = {
            "task_uuid": task_uuid,
            "implant_uuid": implant_uuid,
            "task": {
                "name": task_name,
                "args": dict(task_args),
            },
        }

        if convert_to_msgpack:
            msgpack_task = msgpack.packb(task)
            return msgpack_task

        return task


class TaskResponse(BaseStructure):
    """
    Task Response Structure
    {
        "task_uuid": <uuid>,
        "implant_uuid": <int>,
        "result": {
            "data_type": "binary" | "text",
            "data": <any>
        }
    }
    """

    def validate(self) -> None:
        required = {"task_uuid", "implant_uuid", "result"}
        missing = required - self._data.keys()
        if missing:
            raise ValueError(f"TaskResponse missing fields: {missing}")

        result = self._data["result"]
        if not isinstance(result, dict):
            raise ValueError("'result' must be a dict")

        if "data_type" not in result or "data" not in result:
            raise ValueError("'result' must contain 'data_type' and 'data'")

        if result["data_type"] not in ("binary", "text"):
            raise ValueError("data_type must be 'binary' or 'text'")

    @property
    def data(self) -> Any:
        return self._data["result"]["data"]

    @property
    def data_type(self) -> str:
        return self._data["result"]["data_type"]


class Metadata(BaseStructure):
    """
    Metadata Structure
    {
        "implant_uuid": <uuid>,
        ...
    }
    """

    def validate(self) -> None:
        if "implant_uuid" not in self._data:
            raise ValueError("Metadata missing 'implant_uuid'")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
