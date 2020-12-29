"""
Contains the base class of the supported sites
"""
import logging
from typing import List, Tuple

SITES = list()
log = logging.getLogger('rich')


class SiteBase:
    """
    Parent of the sublcasses
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        SITES.append(cls)
        log.info('Loaded site backend: %s', cls.__module__)

    def locations(self, query: str) -> List[Tuple[str, str]]:
        """
        This method should return a list of tuples
        """
        raise NotImplementedError()

    def query(self, location: Tuple[str, str], price: float, space: float):
        """
        This method queries for the given parameters and returns a list of
        result objects
        """
        raise NotADirectoryError()
