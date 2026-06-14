"""
Empire Memory — loads civilization's collective knowledge.

Every agent reads this at startup to understand:
- The vision (what we're building)
- The doctrine (rules we follow)
- The lessons (what we learned)
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import get_module_logger

log = get_module_logger("empire_memory")


class EmpireMemory:
    """Singleton — all agents share the same memory."""
    
    _instance: Optional["EmpireMemory"] = None
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self._doctrine: str = ""
        self._strategic_memory: Dict[str, Any] = {}
        self._lessons: str = ""
        self._loaded = False
    
    @classmethod
    def get_instance(cls, base_path: str = ".") -> "EmpireMemory":
        if cls._instance is None:
            cls._instance = cls(base_path)
        return cls._instance
    
    def load_all(self):
        if self._loaded:
            return
        try:
            doctrine_path = self.base_path / "EMPIRE_DOCTRINE.md"
            if doctrine_path.exists():
                self._doctrine = doctrine_path.read_text()
            
            memory_path = self.base_path / "memory" / "strategic_memory.json"
            if memory_path.exists():
                with open(memory_path) as f:
                    self._strategic_memory = json.load(f)
            
            lessons_path = self.base_path / "memory" / "LESSONS_LEARNED.md"
            if lessons_path.exists():
                self._lessons = lessons_path.read_text()
            
            self._loaded = True
            log.success("🧠 Empire Memory loaded")
        except Exception as e:
            log.error(f"Memory load error: {e}")
    
    def get_doctrine(self) -> str:
        if not self._loaded:
            self.load_all()
        return self._doctrine
    
    def get_strategic_memory(self) -> Dict[str, Any]:
        if not self._loaded:
            self.load_all()
        return self._strategic_memory
    
    def get_lessons(self) -> str:
        if not self._loaded:
            self.load_all()
        return self._lessons
    
    def get(self, dotted_key: str, default: Any = None) -> Any:
        mem = self.get_strategic_memory()
        keys = dotted_key.split(".")
        val = mem
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val
    
    def get_user_teachings(self) -> list:
        return self.get("USER_TEACHINGS_VERBATIM", [])


def load_empire_memory(base_path: str = ".") -> EmpireMemory:
    mem = EmpireMemory.get_instance(base_path)
    mem.load_all()
    return mem
