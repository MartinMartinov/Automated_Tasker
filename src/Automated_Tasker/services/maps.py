from __future__ import annotations

from Automated_Tasker.utils.vault import Vault
import googlemaps
import aiohttp

class GoogleMapsClient:
    """A class for accessing Google Maps APIs using the oauth2 API and Google Cloud Projects.

    Requires the Google Cloud API key for the account under the vault entry tag 'google-maps-api-key'.
    This is a paid service, but I'm hoping the volumes are so low the price is negligable"""

    URL = "/maps/api/distancematrix/json"

    def __init__(self, vault: Vault):
        """Start all the SwitchBot alarm devices.

        Parameters:
            vault (Vault | None): The vault with the google maps API key
        """
        self.api_key = vault.load_entries().get("google-maps-api-key")
        self.client = googlemaps.Client(self.api_key)

    async def get_distance(
            self,
            *,
            origin: str,
            destination: str,
            arrival_time: int,
            mode: str = "driving",
            units: str = "metric"
        ) -> dict:
        """
        Get the distance and travel time between two locations.
        
        Parameters:
            origin: Starting location as a string (e.g., "New York, NY")
            destination: Destination location as a string (e.g., "Los Angeles, CA")
            arrival time: Specifies the desired time of arrival in Unix time (e.g., 1738158772)
            mode: Mode of transportation (driving, walking, bicycling, transit)
            units: Unit system, either "metric" or "imperial" (default is "metric")
        
        Returns:
            Dictionary containing distance and duration
        """
        params = {
            "origins": origin,
            "destinations": destination,
            "transit_mode": mode,
            "units": units,
            "arrival_time": arrival_time,
        }
        data = self.client._request(GoogleMapsClient.URL, params)

        if "rows" not in data:
            raise ValueError("Failed to fetch data")

        if data['status'] == "REQUEST_DENIED":
            raise PermissionError(data['error_message'])
        
        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            raise ValueError("Invalid location or no route available")

        return {
            "distance": element["distance"]["text"],
            "duration": element["duration"]["text"]
        }