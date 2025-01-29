import json

def fetch_plate_details(number_plate):
    with open('utils/plate_details.json', 'r') as file:
        plate_details = json.load(file)
    return plate_details.get(number_plate)


def save_plate_details(number_plate, details):
    with open('utils/plate_details.json', 'r') as file:
        plate_details = json.load(file)
    plate_details[number_plate] = details
    with open('utils/plate_details.json', 'w') as file:
        json.dump(plate_details, file)
