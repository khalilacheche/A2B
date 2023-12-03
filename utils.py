import requests
import pandas as pd
from datetime import datetime, timedelta
from isodate import duration_isoformat


def fetch_stations(latitude, longitude, radius=10000, limit=50):
    API_URL = "https://journey-service-int.api.sbb.ch/v3/places/by-coordinates"
    CLIENT_SECRET = "MU48Q~IuD6Iawz3QfvkmMiKHtfXBf-ffKoKTJdt5"
    CLIENT_ID = "f132a280-1571-4137-86d7-201641098ce8"
    SCOPE = "c11fa6b1-edab-4554-a43d-8ab71b016325/.default"

    def get_token():
        params = {
            "grant_type": "client_credentials",
            "scope": SCOPE,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        return requests.post(
            "https://login.microsoftonline.com/2cda5d11-f0ac-46b3-967d-af1b2e1bd01a/oauth2/v2.0/token",
            data=params,
        ).json()

    headers = {
        "accept": "application/json",
        "Accept-Language": "en",
        "Authorization": f"Bearer {get_token()['access_token']}",
    }

    params = {
        "longitude": longitude,
        "latitude": latitude,
        "radius": radius,
        "limit": limit,
        "type": "StopPlace",
        "includeVehicleModes": "false",
    }

    response = requests.get(API_URL, params=params, headers=headers, timeout=5)
    try:
        places = response.json()["places"]
        res = []
        for place in places:
            res.append(
                {
                    "name": place["name"],
                    "id": place["id"],
                    "coordinates": place["centroid"]["coordinates"],
                    "distance": place["distanceToSearchPosition"],
                }
            )
        res.sort(key=lambda x: x["distance"])
        return res
    except:
        return None


walking_speed_kmph = 5.0
biking_speed_kmph = 20.0
driving_speed_kmph = 60.0


def get_home_path(start_coordinates, arrival_coordinates, distance, mode, date, time):
    distance = distance / 1000
    if mode == "FOOT":
        duration = distance / walking_speed_kmph
    elif mode == "BIKE":
        duration = distance / biking_speed_kmph
    else:
        duration = distance / driving_speed_kmph

    duration = timedelta(hours=duration)

    arrival = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") + duration

    return {
        "mode": mode,
        "duration": duration_isoformat(duration),
        "departure_date": date,
        "departure_time": time,
        "departurePlaceCoordinates": start_coordinates,
        "arrival_date": arrival.strftime("%Y-%m-%d"),
        "arrival_time": arrival.strftime("%H:%M"),
        "arrivalPlaceCoordinates": arrival_coordinates,
    }


def get_home_paths(
    start_coordinates, arrival_coordinates, distance, date, time, start_id
):
    paths = [
        get_home_path(
            start_coordinates, arrival_coordinates, distance, "FOOT", date, time
        ),
        get_home_path(
            start_coordinates, arrival_coordinates, distance, "BIKE", date, time
        ),
    ]
    mobilitat = pd.read_csv("data/mobilitat.csv", delimiter=";")
    if start_id in mobilitat["OPUIC"]:
        paths.append(
            get_home_path(
                start_coordinates, arrival_coordinates, distance, "CAR", date, time
            )
        )
    return paths


def get_work_path(start_coordinates, arrival_coordinates, distance, mode, date, time):
    distance = distance / 1000
    if mode == "FOOT":
        duration = distance / walking_speed_kmph
    elif mode == "BIKE":
        duration = distance / biking_speed_kmph
    else:
        duration = distance / driving_speed_kmph

    duration = timedelta(hours=duration)

    arrival = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") + duration

    return {
        "mode": mode,
        "duration": duration_isoformat(duration),
        "departure_date": date,
        "departure_time": time,
        "departurePlaceCoordinates": start_coordinates,
        "arrival_date": arrival.strftime("%Y-%m-%d"),
        "arrival_time": arrival.strftime("%H:%M"),
        "arrivalPlaceCoordinates": arrival_coordinates,
    }
