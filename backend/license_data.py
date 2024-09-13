from google.cloud import vision
import requests
from bs4 import BeautifulSoup
import cv2
import json
# import sys, traceback

# filter out extraneous info from license plate
months = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC"
]

# ideally we would get state abbreviation, put it in edmunds API call
# however (comma) we figured it would be easier to stick to just CA license plates
states = {
    "alaska": 'AK',
    "alabama": 'AL',
    "arizona": 'AZ',
    "arkansas":'AR',
    "california":'CA',
    "colorado":'CO',
    "connecticut":'CT',
    "delaware":'DE',
    "florida":'FL',
    "georgia":'GA',
    "hawaii":'HI',
    "idaho":'ID',
    "illinois":'IL',
    "indiana":'IN',
    "iowa":'IA',
    "kansas":'KS',
    "kentucky":'KY',
    "louisiana":'LA',
    "maryland":'MD',
    "maine":'ME',
    "massachusetts":'MA',
    "michigan":'MI',
    "minnesota":'MN',
    "mississippi":'MS',
    "missouri":'MO',
    "montana":'MT',
    "nebraska":'NE',
    "nevada":'NV',
    "new jersey":'NJ',
    "new hampshire":'NH',
    "new mexico":'NM',
    "new york":'NY',
    "north carolina":'NC',
    "north dakota":'ND',
    "ohio":'OH',
    "oklahoma":'OK',
    "oregon":'OR',
    "pennsylvania":'PA',
    "rhode island":'RI',
    "south carolina":'SC',
    "south dakota":'SD',
    "tennessee":'TN',
    "texas":'TX',
    "utah":'UT',
    "vermont":'VT',
    "washington":'WA',
    "virginia":'VA',
    "west virginia":'WV',
    "wisconsin":'WI',
    "wyoming":'WY'
}


# states_abbrev =

def license_detect(path):
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    objects = client.object_localization(
        image=image).localized_object_annotations

    vertices = []

    print('Number of objects found: {}'.format(len(objects)))
    if len(objects) ==0:
        return
    for object_ in objects:
        if object_.name == "License plate":
            for vertex in object_.bounding_poly.normalized_vertices:
                vertices.append(vertex)

    if len(vertices) > 0:
        img = cv2.imread(path)
        height = img.shape[0]
        width = img.shape[1]
        crop_img = img[int(height*vertices[0].y):int(height*vertices[2].y), int(width*vertices[0].x):int(width*vertices[1].x)]
        cv2.imwrite("license_plate.png", crop_img)
        image_file.close()

        with open('license_plate.png', 'rb') as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations
        words = [text.description for text in texts]

        state = None
        plate_number = None

        for text in words[1:]:
            if text=="YA" or text=="YR": continue
            if text in months or text=="MO": continue
            try:
                num = int(text)
                if num>1950 and num<2025: continue
            except:
                if text.lower() in states.keys():
                    state = states[text.lower()]
                elif len(str(text)) in [7]:
                    plate_number = text

        print("LICENSE PLATE: ", plate_number)
        print("STATE: ", state)

        # hardcode the state for the demo
        state = 'CA'

        # Gets data for plate_number from edmund API
        headers = {
            'user-agent': 'PostmanRuntime/7.23.0'
        }
        vin_api = "https://www.edmunds.com/api/partner-offers/vin"
        vin_params={
            'plateNumber': plate_number,
            'plateState': state
        }
        attr_api = "https://www.edmunds.com/gateway/api/vehicle/v3/styles/vins/"
        try:
            vin_req = requests.get(url=vin_api, params=vin_params, headers=headers)
            vin = vin_req.json()["vin"]
            attr_req = requests.get(url=attr_api + str(vin), headers=headers)
            attributes = attr_req.json()
        except:
            # no license plate detected
            return { 'error' : "license plate not found in CA database" }

        car_properties = None
        try:
            car_properties = dict(attributes[0])
        except:
            car_properties = dict(attributes)

        print(attributes)

        # "https://www.edmunds.com/{makeNiceId}/{modelNiceId}/{year}/appraisal-value/?vin={VIN}&styleIds={styleId}"
        url = "https://www.edmunds.com/%s/%s/%s/appraisal-value/?vin=%s&styleIds=%s" % (
            car_properties['makeNiceId'],
            car_properties['modelNiceId'],
            car_properties['year'], 
            vin,
            car_properties['styleId']
        )
        print(url)

        webpage = BeautifulSoup(requests.get(url, headers=headers).text, "html.parser")

        # curr = webpage.find("text-right")

        print(vin)

        # image_url suddenly does not work and i'm not about to debug that
        # image_url = webpage.find('img', class_='vehicle-image')['src']
        # print(image_url)

        variants = webpage.find_all('caption', class_='text-gray-darker size-16 mb-0_25')
        variants = list([item.get_text() for item in variants])

        style = car_properties['styleName']

        style_idx = variants.index(car_properties['styleName'] + ' with no options')

        prices = webpage.find_all('td', class_='text-right')
        prices = list([item.get_text() for item in prices])[style_idx*12:(style_idx+1)*12]

        prices_mat = [[prices[j] for j in range(3*i, 3*(i+1))] for i in range(4)]

        price_upper = prices_mat[0][0]
        price_lower = prices_mat[3][0]

        
        print(prices_mat)
        print(style)

        json_load = {
            'LIC_NUM': plate_number,
            'LIC_STATE': state,
            'VIN_NUM': vin,
            'CAR_MAKE': car_properties['makeName'],
            'CAR_MODEL': car_properties['modelName'],
            'CAR_YEAR': car_properties['year'],
            'CAR_STYLE': style,
            # 'IMG_URL': image_url,
            # dimension 2: trade in, private party, retail dealer
            # dimension 1: outstanding, clean, average, rough [condition]
            # 'CAR_PRICES': prices
            'PRICE_UPPER': price_upper,
            'PRICE_LOWER': price_lower
        }

        print(json_load)
        return json_load
        
    else:
        # no license plate detected
        return { 'error' : "no license plate detected" }