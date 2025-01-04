from aiohttp import ClientSession
from asyncio import run as run_async
from asyncio import sleep as asleep
from urllib.parse import quote
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Literal, AsyncIterator
from functools import cache
from Automated_Tasker.tasklist import WEEKDAYS
from tabulate import tabulate
from time import struct_time, strptime

listings_url = 'https://ottawa.ca/en/recreation-and-parks/facilities/place-listing?place_facets%5B0%5D=place_type%3A4285&place_facets%5B1%5D=place_type%3A2235821'
facility_url = 'https://ottawa.ca/en/recreation-and-parks/facilities/place-listing/'

@cache
def get_position(geolocator: Nominatim, address:str) -> tuple[str|None,str|None]:
    """Get the position of the address

    Args:
        geolocator: The geolocator used to find the latitude and longitude
        address: The address to look up in the Nominatim lookup

    Returns:
        The latitude and longitude tuple, or double None if it failed
    """
    geocoded_location = geolocator.geocode(address)
    if not geocoded_location:
        return None, None
    return geocoded_location.latitude, geocoded_location.longitude

async def get_pools(geolocator: Nominatim) -> list[dict[str,str]]:
    """Get all the pools listed on the City of Ottawa page

    Args:
        geolocator: The geolocator used to find the latitude and longitude

    Returns:
        A dict containing all the fields related to a pool that could be useful
    """
    pools = []
    for i in range(100):
        async with ClientSession() as session:
            async with session.get(listings_url+"&page="+str(i)) as response:
                body = await response.text()

        soup = BeautifulSoup(body, 'html.parser')
        pool_entries = soup.find('table', class_="table table-bordered table-condensed cols-2")

        if not pool_entries: # Break when we reach an empty page
            break

        pool_entries = pool_entries.find('tbody').findAll('tr')

        for entry in pool_entries:
            await asleep(1) # Pause this loop for geopy not to be overwhelmed with requests while proceeding with other code
            values = entry.findAll('td')
            name = values[0].text
            address = values[1].text.split('\n')[0]+", Ottawa, ON"
            latitude, longitude = get_position(geolocator, address)
            pools.append({'name': name, 'address': address, 'latitude': latitude, 'longitude': longitude})

    return pools

async def get_times(
    pools: list[dict[str,str]],
    day: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
) -> list[dict[str,str|int]]:
    """Find the tables for lane swims for a pool and extract the values on a weekday

    Args:
        pools: A list of all the dicts returned in the get_pools function
        day: Day of the week to extract the column from (assumes the order given in the Literal)

    Returns:
        Returns all the tables in all the given pool webpages that include a Lane Swim
    """
    slots = []
    for pool in pools:
        name = pool['name']
        url = name.replace('-','').replace('  ',' ').strip().lower().replace(' ','-') # Catches all the cases I've found so far

        async with ClientSession() as session:
            async with session.get(facility_url+quote(url)) as response:
                body = await response.text()

        soup = BeautifulSoup(body, 'html.parser')
        tables = soup.find_all('table')
        for table in tables:
            caption = table.find('caption').text.strip().replace('–','-')
            rows = table.find('tbody').findAll('tr')
            for row in rows:
                entries = row.findAll('td')
                header = row.find('th').text.lower()
                if 'lane' in header and 'swim' in header:
                    if len(entries) == 7:
                        entry = entries[WEEKDAYS.index(day)].text.strip().lower()
                        subtimes = entry.split('\n')
                        entry = []
                        for subtime in subtimes:
                            temp = subtime.strip()
                            if len(temp) > 4:
                                entry.append(temp)
                        if entry and entry[0] != "n/a":
                            name = pool['name'].split('-')[0].strip()
                            name = name.replace('Recreation', 'Rec')
                            name = name.replace('and Pool', '')
                            name = name.replace('and Wave Pool', '')
                            slots.append(dict(
                                pool = name,
                                address = pool['address'],
                                latitude = pool['latitude'],
                                longitude = pool['longitude'],
                                desc = caption.split('-')[-1].strip(),
                                time = (' ,'.join(entry)).replace(", ,", ", "),
                            ))
                    else:
                        continue
    return(slots)

async def convert_time(time_stamp: str) -> struct_time:
    """Convert the plethora of Ottawa webpage formats to a time

    Args:
        time_stamp: A string containing a single time of day

    Returns:
        A time struct of the value to be used for filtering and cleaner printing
    """
    time_stamp = time_stamp.strip().lower().encode('ascii', 'ignore').decode()
    
    if ':' in time_stamp:
        if 'am' in time_stamp or 'pm' in time_stamp:
            return strptime(time_stamp, "%I:%M %p")
        return strptime(time_stamp, "%H:%M")
    if 'am' in time_stamp or 'pm' in time_stamp:
        return strptime(time_stamp, "%I %p")
    return strptime(time_stamp, "%H")

async def convert_time_ranges(time_range: str) -> AsyncIterator[tuple[struct_time,struct_time]]:
    """_summary_

    Args:
        time_range: A string containing the values in the Ottawa website tables

    Yields:
        A tuple of start and stop time structs
    """
    for period in time_range.replace('–','-').replace("noon","12:00 pm").split(","):
        if "pm" in period and not " pm" in period:
            period = period.replace("pm", " pm")
        if "am" in period and not " am" in period:
            period = period.replace("am", " am")

        times = period.split('-')
        times[0], times[1] = times[0].strip(), times[1].strip()
        if times[1].endswith('m') and not times[0].endswith('m'):
            times[0] = times[0] + ' ' + times[1][-2:]
        yield await convert_time(times[0]), await convert_time(times[1]) 

async def get_lane_swims(
        day: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        location: str,
        start: struct_time = strptime("00:00", "%H:%M"),
        stop: struct_time = strptime("23:59", "%H:%M"),
    ) -> AsyncIterator[str]:
    """Create and return a series of tables to be used to display the data.
    
    Weird to make it an Iterator but here we are.

    Args:
        day: Day of the week
        location: The starting point from which to calculate pool distances from
        start: Start time if you don't want 12:00 AM
        stop: Stop time if you don't want 11:59 PM

    Yields:
        First, a pool location table.  Then a series of tables describing the pool times.
    """
    geolocator = Nominatim(user_agent="pools_locator")
    lat, long = get_position(geolocator, location)
    pools = await get_pools(geolocator)
    times = await get_times(pools, day)
    
    entries = []
    for time in times:
        distance = geodesic((lat, long),(time['latitude'],time['longitude'])).km
        entries.append([
            time['pool'],
            time['desc'],
            distance,
            time['address'].split(',')[0],
            time['time'],
        ])
    entries = sorted(entries, key=lambda x: x[2], reverse=True)

    # Pool Locations
    headers = [
        "Pool",
        "Dist. (km)",
        "Address",
    ]
    rows = []
    for entry in entries:
        pool = [
            entry[0],
            entry[2],
            entry[3],
        ]
        if pool not in rows:
            rows.append(pool)
    rows.append([
        "Starting Point",
        0,
        location.split(',')[0],
    ])
    yield tabulate(
            rows,
            headers=headers,
            floatfmt=".2f",
        )

    # Pool Times
    headers = [
        "Pool",
        "Table",
        "Time",
    ]
    rows = []
    for entry in entries:
        async for time in convert_time_ranges(entry[4]):
            if stop > time[0] and start < time[1]:
                rows.append([
                    entry[0],
                    entry[1],
                    f"{time[0].tm_hour:02d}:{time[0].tm_min:02d}-{time[1].tm_hour:02d}:{time[1].tm_min:02d}",
                ])
            if len(rows) == 25:
                yield tabulate(
                    rows,
                    headers=headers,
                )
                rows = []
    if rows:
        yield tabulate(
            rows,
            headers=headers,
        )