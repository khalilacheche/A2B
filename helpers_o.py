import requests
import json

# from co2calculator.co2calculator import calc_co2_bus, calc_co2_car, calc_co2_train
import geopy.distance
from datetime import datetime
import pandas as pd
from datetime import datetime, timedelta
from isodate import duration_isoformat


walking_speed_kmph = 5.0
biking_speed_kmph = 20.0
driving_speed_kmph = 60.0


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


def fetch_stations(latitude, longitude, radius=10000, limit=50):
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


def get_coordinates(query):
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json"}

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            # Assuming the first result is the desired location
            latitude = float(data[0]["lat"])
            longitude = float(data[0]["lon"])
            return latitude, longitude
        else:
            return None
    else:
        print("Error:", response.status_code)
        return None


def calculate_co2_emissions(path):
    if "arrivalPlaceCoordinates" in path and "departurePlaceCoordinates" in path:
        departurePlaceCoordinates = path["departurePlaceCoordinates"]
        arrivalPlaceCoordinates = path["arrivalPlaceCoordinates"]
        distance = geopy.distance.geodesic(
            tuple(departurePlaceCoordinates), tuple(arrivalPlaceCoordinates)
        ).km
        mode = path["mode"]
        if mode == "METRO" or mode == "TRAIN":
            return calc_co2_train(distance)
        if mode == "BUS":
            return calc_co2_bus(distance)
        if mode == "CAR":
            return calc_co2_car(distance)
        return 0
    else:
        print("bad format")
        return 0


def get_path(headers, origin: str, destination: str, date: str, time: str):
    body = {
        "origin": origin,
        "destination": destination,
        "date": date,
        "time": time,
        "includeSummary": True,
    }
    r = requests.request(
        url=API_URL + "/v3/trips/intervals/by-origin-destination",
        method="POST",
        headers=headers,
        data=json.dumps(body),
    )
    res = r.json()
    json_object = json.dumps(res, indent=4)
    with open("sample.json", "w") as outfile:
        outfile.write(json_object)
    trips = res["trips"]
    results = []
    for trip in trips:
        tripSummary = {
            "origin": trip["summary"]["firstStopPlace"]["place"]["name"],
            "destination": trip["summary"]["lastStopPlace"]["place"]["name"],
        }
        paths = []
        """
            "mode":t["mode"],
                         "duration":t["duration"],
                         "departure":{"place":t["serviceJourney"]["stopPoints"][0]["place"]["centroid"],"time":t["serviceJourney"]["stopPoints"][0]["departure"]["timeAimed"]},
                         } 
            """
        for t in trip["legs"]:
            if "serviceJourney" in t and "mode" in t and "duration" in t:
                journey = t["serviceJourney"]
                departureTime = journey["stopPoints"][0]["departure"]["timeAimed"]
                departurePlaceCoordinates = journey["stopPoints"][0]["place"][
                    "centroid"
                ]["coordinates"]
                arrivalTime = journey["stopPoints"][-1]["arrival"]["timeAimed"]
                arrivalDeparturePlaceCoordinates = journey["stopPoints"][-1]["place"][
                    "centroid"
                ]["coordinates"]
                mode = t["mode"]
                duration = t["duration"]
                paths.append(
                    {
                        "mode": mode,
                        "duration": duration,
                        "departure_date": datetime.fromisoformat(
                            departureTime
                        ).strftime("%Y-%m-%d"),
                        "departure_time": datetime.fromisoformat(
                            departureTime
                        ).strftime("%H:%M"),
                        "departurePlaceCoordinates": departurePlaceCoordinates,
                        "arrival_date": datetime.fromisoformat(arrivalTime).strftime(
                            "%Y-%m-%d"
                        ),
                        "arrival_time": datetime.fromisoformat(arrivalTime).strftime(
                            "%H:%M"
                        ),
                        "arrivalPlaceCoordinates": arrivalDeparturePlaceCoordinates,
                    }
                )
        tripSummary["path"] = paths
        tripSummary["co2_emissions"] = sum(
            [calculate_co2_emissions(path) for path in paths]
        )
        results.append(tripSummary)
    # print(results)
    return results


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
