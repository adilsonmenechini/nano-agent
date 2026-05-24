from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSkill(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description
        }