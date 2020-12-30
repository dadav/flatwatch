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


def flat_count(location: str, locationid: int, price: Optional[int] = None, rooms: Optional[int] = None,
               area: Optional[int] = None, radius_in_km: Optional[int] = None) -> int:
    """
    This method queries for the given parameters and returns a list of
    result objects
    """
    given = {
        'world': 'LIVING',
        'location': location.replace(' ', '+'),
        'gacId': locationid,
        'price': price,
        'noOfRooms': rooms,
        'area': area,
        'radius': 'Km{}'.format(radius_in_km) if radius_in_km else None,
    }

    data = {k: v for k, v in given.items() if v is not None}

    req = requests.post(COUNT_URL, data=data)
    req.raise_for_status()
    json_data = req.json()

    if bool(json_data['error']):
        raise Exception('Ups, something went wrong here...(used data: {} result: {})'.format(data, json_data))

    count = int(json_data['count'])
    log.debug('Good request for %s, found %d flats!', location, count)

    return count
