from requests import Session
import json
from flask import request, make_response, jsonify
import copy
from user import add_recipe_history, get_jwt_token, login

def get_ingredients(session, request_body):
    items = []
    for ingredient in request_body['ingredients']:
        url = "https://www.instacart.ca/v3/containers/loblaws/search_v3/{}?".format(ingredient)

        payload = {}
        headers = {
            'authority': 'www.instacart.ca',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9'
        }

        response = session.request("GET", url, headers=headers, data = payload)

        item = None
        content = json.loads(response.text)

        for module in content['container']['modules']:
            if module['data'].get('header', None) and module['data']['header']['label'].split(' ')[1] == 'results':
                for product in module['data']['items']:
                    if product['tracking_params']['original_position'] == 1:
                        item = product
                        break
                if item:
                    break
        item_dict = {
            "id": item['id'],
            "price": item['pricing']['price'],
            "name": item['name'],
            "image": item['image'],
            "tracking_params": item['tracking_params'],
            "source_value": ingredient
        }
        items.append(item_dict)
    return items

def add_to_cart(session, ingredients):
    url = "https://www.instacart.ca/v3/carts/50639323/update_items?source=web&cache_key="

    payload = json.dumps({
                "items": [
                            {
                                "item_id": ingredient['id'], 
                                "quantity": 1,
                                "source_type": "search",
                                "source_value": ingredient['source_value'],
                                "tracking": ingredient['tracking_params'],
                                "item_tasks":[],
                                "qty_type":"null"
                            }
                        for ingredient in ingredients],
                        "request_timestamp":1580265797400,
                        "options":{
                            "assign_to_first_journey_instructions": True
                        }
                })
    headers = {
        'authority': 'www.instacart.ca',
        'origin': 'https://www.instacart.ca',
        'x-csrf-token': 'dlqcoViByAwhUggi3o/uIi5l8d/ohbFyT7m+rwHaD/ZepVXKUlDSgSLNrTItXsXLdi9nEQIu8Ux79KKPofEONw==',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36',
        'content-type': 'application/json',
        'accept': 'application/json',
        'x-client-identifier': 'web',
        'x-requested-with': 'XMLHttpRequest',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'referer': 'https://www.instacart.ca/store/loblaws/search_v3/apple',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9'
    }

    response = session.request("PUT", url, headers=headers, data = payload)

    return response


def order():
    request_body = request.get_json()
    if not request_body:
        request_body = request.form
    session = Session()
    login(session, request_body)
    ingredients = get_ingredients(session, request_body)
    response = add_to_cart(session, ingredients)

    if response.status_code == 200:
        # succesfully added to cart, store user recipe history
        add_recipe_history(request_body)
        jwt_token = get_jwt_token(request_body, authenticated=True)
        resp = {
            'status': 'success',
            'status_code': 200,
            'message': 'added to cart',
        }

        resp = make_response(jsonify(resp))
        resp.set_cookie('mealplanner_auth_token', jwt_token.decode())

        return resp
    
    return response