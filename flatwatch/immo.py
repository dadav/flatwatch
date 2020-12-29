import logging
import requests
import json
from urllib.parse import quote
from typing import List, Tuple, Optional

log = logging.getLogger('rich')

LOCATION_URL = 'https://www.immobilienscout24.de/geoautocomplete/v3/locations.json?i={}'
COUNT_URL = 'https://www.immobilienscout24.de/Suche/controller/oneStepSearch/resultCount.json'


def locations(query: str) -> List[Tuple[str, str]]:
    """
    This method should return a list of tuples
    """
    req = requests.get(LOCATION_URL.format(quote(query)))
    req.raise_for_status()
    return [(entry['entity']['label'], entry['entity']['id']) for entry in req.json()]


def flat_count(location: str, locationid: int, price: Optional[float], rooms: Optional[int],
               area: Optional[float], radius_in_km: Optional[int]) -> int:
    """
    This method queries for the given parameters and returns a list of
    result objects
    """
    data = {
        'world': 'LIVING',
        'location': location,
        'gacId': locationid,
        'price': price or '',
        'noOfRooms': rooms or '',
        'area': area or '',
        'radius': 'Km{}'.format(radius_in_km) if radius_in_km else '',
    }
    req = requests.post(COUNT_URL, data=data)
    req.raise_for_status()
    return int(req.json()['count'])
