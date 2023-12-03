import json
import requests
import pandas as pd
import geopy.distance
from datetime import datetime, timedelta
from isodate import duration_isoformat
from co2calculator.co2calculator import calc_co2_bus, calc_co2_car, calc_co2_train
import warnings

warnings.filterwarnings("ignore")

API_URL = "https://journey-service-int.api.sbb.ch"
CLIENT_SECRET = "MU48Q~IuD6Iawz3QfvkmMiKHtfXBf-ffKoKTJdt5"
CLIENT_ID = "f132a280-1571-4137-86d7-201641098ce8"
SCOPE = "c11fa6b1-edab-4554-a43d-8ab71b016325/.default"

LIMIT = 5

walking_speed_kmph = 5.0
biking_speed_kmph = 20.0
driving_speed_kmph = 60.0


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


def use_token():
    headers = {
        "Authorization": f"Bearer {get_token()['access_token']}",
        "accept": "application/json",
        "Accept-Language": "en",
        "Content-Type": "application/json",
    }
    return headers

    # Include the header (and additional ones if needed in your request
    # Writing to sample.json


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
                depaturePlace = journey["stopPoints"][0]["place"]["name"]
                arrivalPlace = journey["stopPoints"][-1]["place"]["name"]
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
                        "departurePlace": depaturePlace,
                        "departurePlaceCoordinates": departurePlaceCoordinates,
                        "arrival_date": datetime.fromisoformat(arrivalTime).strftime(
                            "%Y-%m-%d"
                        ),
                        "arrival_time": datetime.fromisoformat(arrivalTime).strftime(
                            "%H:%M"
                        ),
                        "arrivalPlaceCoordinates": arrivalDeparturePlaceCoordinates,
                        "arrivalPlace": arrivalPlace,
                    }
                )
        tripSummary["path"] = paths
        tripSummary["co2_emissions"] = sum(
            [calculate_co2_emissions(path) for path in paths]
        )
        results.append(tripSummary)
    # print(results)
    return results


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


def normalize_column(column):
    min_val = float(column.min())
    max_val = float(column.max())
    normalized_column = (column - min_val) / (max_val - min_val)
    return normalized_column


def calculate_score(row, co2_weight, time_weight, transfers_weight):
    return (
        co2_weight * row["CO2 emissions"]
        + time_weight * row["time"]
        + transfers_weight * row["transfers"]
    )


def get_reduced_path(origin: str, destination: str, date: str, time: str):
    headers = use_token()
    results = get_path(headers, origin, destination, date, time)
    return [(result["path"], result["co2_emissions"]) for result in results]


def transform(row):
    paths = row["path"]

    if paths[0]["arrival_time"] != paths[1]["departure_time"]:
        diff = datetime.strptime(
            f"{paths[1]['departure_date']} {paths[1]['departure_time']}",
            "%Y-%m-%d %H:%M",
        ) - datetime.strptime(
            f"{paths[0]['arrival_date']} {paths[0]['arrival_time']}", "%Y-%m-%d %H:%M"
        )
        paths[0]["departure_date"] = (
            datetime.strptime(
                f"{paths[0]['departure_date']} {paths[0]['departure_time']}",
                "%Y-%m-%d %H:%M",
            )
            + diff
        ).strftime("%Y-%m-%d")
        paths[0]["departure_time"] = (
            datetime.strptime(
                f"{paths[0]['departure_date']} {paths[0]['departure_time']}",
                "%Y-%m-%d %H:%M",
            )
            + diff
        ).strftime("%H:%M")
        paths[0]["arrival_date"] = (
            datetime.strptime(
                f"{paths[0]['arrival_date']} {paths[0]['arrival_time']}",
                "%Y-%m-%d %H:%M",
            )
            + diff
        ).strftime("%Y-%m-%d")
        paths[0]["arrival_time"] = (
            datetime.strptime(
                f"{paths[0]['arrival_date']} {paths[0]['arrival_time']}",
                "%Y-%m-%d %H:%M",
            )
            + diff
        ).strftime("%H:%M")

    time = (
        datetime.strptime(
            f"{paths[-1]['arrival_date']} {paths[-1]['arrival_time']}",
            "%Y-%m-%d %H:%M",
        )
        - datetime.strptime(
            f"{paths[0]['departure_date']} {paths[0]['departure_time']}",
            "%Y-%m-%d %H:%M",
        )
    ).seconds

    transfers = len(paths)

    row["time"] = time
    row["transfers"] = transfers

    return row


def find_recommended_paths(
    start_lon,
    start_lat,
    target_lon,
    target_lat,
    date,
    time,
    co2_weight,
    time_weight,
    transfers_weight,
):
    start_stations = pd.DataFrame(fetch_stations(start_lat, start_lon, limit=LIMIT))
    target_stations = pd.DataFrame(fetch_stations(target_lat, target_lon, limit=LIMIT))

    df = pd.merge(
        start_stations, target_stations, how="cross", suffixes=["_start", "_target"]
    )

    df["home_to_station_path"] = [
        get_home_paths(
            [start_lon, start_lat],
            df.loc[i, "coordinates_start"],
            df.loc[i, "distance_start"],
            date,
            time,
            df.loc[i, "id_start"],
        )
        for i in range(len(df))
    ]

    df = df.explode("home_to_station_path").reset_index(drop=True)

    # headers = use_token()

    df["station_to_station_path"] = [
        get_reduced_path(
            df.loc[i, "id_start"],
            df.loc[i, "id_target"],
            df.loc[i, "home_to_station_path"]["arrival_date"],
            df.loc[i, "home_to_station_path"]["arrival_time"],
        )
        for i in range(len(df))
    ]

    paths = df.explode("station_to_station_path").reset_index(drop=True)

    paths["CO2 emissions"] = [x[1] for x in paths["station_to_station_path"]]
    paths["station_to_station_path"] = [x[0] for x in paths["station_to_station_path"]]

    paths["station_to_work_path"] = [
        [
            get_work_path(
                paths.loc[i, "coordinates_start"],
                paths.loc[i, "coordinates_target"],
                paths.loc[i, "distance_start"],
                "FOOT",
                paths.loc[i, "station_to_station_path"][-1]["arrival_date"],
                paths.loc[0, "station_to_station_path"][-1]["arrival_time"],
            ),
            get_work_path(
                paths.loc[i, "coordinates_start"],
                paths.loc[i, "coordinates_target"],
                paths.loc[i, "distance_start"],
                "BIKE",
                paths.loc[i, "station_to_station_path"][-1]["arrival_date"],
                paths.loc[0, "station_to_station_path"][-1]["arrival_time"],
            ),
            get_work_path(
                paths.loc[i, "coordinates_start"],
                paths.loc[i, "coordinates_target"],
                paths.loc[i, "distance_start"],
                "CAR",
                paths.loc[i, "station_to_station_path"][-1]["arrival_date"],
                paths.loc[0, "station_to_station_path"][-1]["arrival_time"],
            ),
        ]
        for i in range(len(paths))
    ]

    paths = paths.explode("station_to_work_path").reset_index(drop=True)

    paths["CO2 emissions"] = [
        paths.loc[i, "CO2 emissions"]
        + calculate_co2_emissions(paths.loc[i, "home_to_station_path"])
        + calculate_co2_emissions(paths.loc[i, "station_to_work_path"])
        for i in range(len(paths))
    ]

    final_df = pd.DataFrame(
        {
            "path": [
                [paths.loc[i, "home_to_station_path"]]
                + paths.loc[i, "station_to_station_path"]
                + [paths.loc[i, "station_to_work_path"]]
                for i in range(len(paths))
            ],
            "CO2 emissions": paths["CO2 emissions"],
        }
    )

    final_df["time"] = 0
    final_df["transfers"] = 0

    final_df = final_df.apply(transform, axis=1)

    final_df["CO2 emissions"] = normalize_column(final_df["CO2 emissions"])
    final_df["time"] = normalize_column(final_df["time"])
    final_df["transfers"] = normalize_column(final_df["transfers"])

    final_df["score"] = 0

    final_df["score"] = final_df.apply(
        lambda x: calculate_score(x, co2_weight, time_weight, transfers_weight), axis=1
    )

    final_df.sort_values(by=["score"], inplace=True)

    final_df = final_df.reset_index(drop=True)

    return final_df


if __name__ == "__main__":
    start_lat = "46.523904"
    start_lon = "6.564732"

    target_lat = "46.505265"
    target_lon = "6.627317"

    date = "2023-12-02"
    time = "17:07"

    co2_weight, time_weight, transfers_weight = 0.5, 0.9, 0.7

    df = find_recommended_paths(
        start_lon,
        start_lat,
        target_lon,
        target_lat,
        date,
        time,
        co2_weight,
        time_weight,
        transfers_weight,
    )

    print(df)
