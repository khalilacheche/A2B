import requests
import json
from co2calculator.co2calculator import calc_co2_bus,calc_co2_car,calc_co2_train
import geopy.distance

API_URL = "https://journey-service-int.api.sbb.ch"
CLIENT_SECRET = "MU48Q~IuD6Iawz3QfvkmMiKHtfXBf-ffKoKTJdt5"
CLIENT_ID = "f132a280-1571-4137-86d7-201641098ce8"
SCOPE = "c11fa6b1-edab-4554-a43d-8ab71b016325/.default"


def get_token():
    params = {
        'grant_type': 'client_credentials',
        'scope': SCOPE,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    return requests.post('https://login.microsoftonline.com/2cda5d11-f0ac-46b3-967d-af1b2e1bd01a/oauth2/v2.0/token',
                         data=params).json()

def use_token():
    headers = {
        'Authorization': f"Bearer {get_token()['access_token']}",
         'accept': 'application/json',
        'Accept-Language': 'en',
        'Content-Type': 'application/json',
    }
    return headers



    # Include the header (and additional ones if needed in your request
    # Writing to sample.json
  


def get_path(headers,origin:str,destination:str,date:str,time:str):
    body ={
        "origin": origin,
        "destination": destination,
        "date": date,
        "time": time,
        "includeSummary":True
    }
    r = requests.request(url=API_URL+"/v3/trips/intervals/by-origin-destination",method="POST",headers=headers,data=json.dumps(body))
    res = r.json()
    json_object = json.dumps(res, indent=4)
    with open("sample.json", "w") as outfile:
        outfile.write(json_object)
    trips = res["trips"]
    results= []
    for trip in trips:
            tripSummary = {
                "origin":trip["summary"]["firstStopPlace"]["place"]["name"],
                "destination":trip["summary"]["lastStopPlace"]["place"]["name"],
            }
            paths= []
            """
            "mode":t["mode"],
                         "duration":t["duration"],
                         "departure":{"place":t["serviceJourney"]["stopPoints"][0]["place"]["centroid"],"time":t["serviceJourney"]["stopPoints"][0]["departure"]["timeAimed"]},
                         } 
            """
            for t in trip["legs"]:
                if("serviceJourney" in t and "mode" in t and "duration" in t):
                    journey = t["serviceJourney"]
                    departureTime = journey["stopPoints"][0]["departure"]["timeAimed"]
                    departurePlaceCoordinates = journey["stopPoints"][0]["place"]["centroid"]["coordinates"]
                    arrivalTime =  journey["stopPoints"][-1]["arrival"]["timeAimed"]
                    arrivalPlaceCoordinates=journey["stopPoints"][-1]["place"]["centroid"]["coordinates"]
                    mode = t["mode"]
                    duration=t["duration"]
                    departurePlace = journey["stopPoints"][0]["place"]["name"]
                    arrivalPlace = journey["stopPoints"][-1]["place"]["name"]
                    paths.append({
                        "mode":mode,
                        "duration":duration,
                        "departureTime":departureTime,
                        "departurePlaceCoordinates":departurePlaceCoordinates,
                        "departurePlace":departurePlace,
                        "arrivalTime":arrivalTime,
                        "arrivalPlace":arrivalPlace,
                        "arrivalPlaceCoordinates":arrivalPlaceCoordinates
                    })
            tripSummary["path"] = paths
            tripSummary["co2_emissions"] = sum([calculate_co2_emissions(path) for path in paths])
            results.append(tripSummary)
    print(results)
    return results



def calculate_co2_emissions(path):
    if("arrivalPlaceCoordinates" in path and "departurePlaceCoordinates" in path):
        departurePlaceCoordinates = path["departurePlaceCoordinates"]
        arrivalPlaceCoordinates = path["arrivalPlaceCoordinates"]
        distance = geopy.distance.geodesic(tuple(departurePlaceCoordinates), tuple(arrivalPlaceCoordinates)).km
        mode = path["mode"]
        if(mode=="METRO" or mode=="TRAIN"):
            return calc_co2_train(distance)
        if(mode=="BUS"):
            return calc_co2_bus(distance)
        if(mode=="CAR"):
            return calc_co2_car(distance)
        return 0
    else:
        print("bad format")
        return 0 
    
    

if __name__ == "__main__":
    headers = use_token()
    results = get_path(headers=headers,origin="8592165",destination="8501214",date="2023-12-02",time="17:07")
    #r = requests.request(url="https://prail.api.sbb.ch:443"+"/api/v2/amanda/parking-facilities",method="GET",headers=headers)