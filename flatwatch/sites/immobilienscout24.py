import logging
import requests
from .base import SiteBase
from typing import List, Tuple
from bs4 import BeautifulSoup

log = logging.getLogger('rich')


class ImmobilienScout24(SiteBase):
    """\
    Siteclass for ImmobilienScout24
    """

    def __init__(self):
        pass

    def locations(self, query: str) -> List[Tuple[str, str]]:
        """
        This method should return a list of tuples
        """

    def query(self, location: Tuple[str, str], price: float, space: float):
        """
        This method queries for the given parameters and returns a list of
        result objects
        """
        raise NotADirectoryError()
