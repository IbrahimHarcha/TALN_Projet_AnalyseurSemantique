# base_store.py

import pickle
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
from typing import TypeVar, Optional

DATA_REPO = Path("data")
T = TypeVar("T")


class StorableResource(ABC):
    """
    Classe de base pour gérer des ressources mise en cache (cache local).
    Anciennement 'BaseCache', mais renommée pour la discrétion.
    """

    def __init__(self, cache_filename: str, *, validity: Optional[timedelta] = None):
        self.cache_path = DATA_REPO / cache_filename
        self._init_data_folder()
        self.resource_data: T = None
        self.last_save: Optional[datetime] = None
        self.EXPIRE = validity or timedelta(days=7)
        self._activate()

    @staticmethod
    def _init_data_folder():
        if not DATA_REPO.exists():
            DATA_REPO.mkdir(parents=True)

    def _activate(self):
        """Charge le cache ou le (re)construit."""
        if not self._read_cache():
            self._build_and_store()

    def _read_cache(self) -> bool:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "rb") as f:
                    self.resource_data, self.last_save = pickle.load(f)
                if not self._is_outdated():
                    return True
            except (EOFError, pickle.UnpicklingError):
                return False
            except Exception as e:
                print(f"Could not load from {self.cache_path}: {e}")
        return False

    def _is_outdated(self) -> bool:
        if not self.last_save:
            return True
        return (datetime.now() - self.last_save) > self.EXPIRE

    def _build_and_store(self):
        self.resource_data = self._fetch_resource()
        self.last_save = datetime.now()
        self._write_cache()

    def _write_cache(self):
        with open(self.cache_path, "wb") as f:
            pickle.dump((self.resource_data, self.last_save), f)

    def retrieve(self) -> T:
        if self._is_outdated():
            self._build_and_store()
        return self.resource_data

    @abstractmethod
    def _fetch_resource(self) -> T:
        """Méthode à implémenter pour récupérer la ressource (ex. via API, fichiers, etc.)."""
        pass
