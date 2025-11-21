import jwt, time, math, base64, os, environ, requests
from django.http import JsonResponse, HttpResponse

endpoint_url = 'https://openapi.doordash.com/drive/v2'

def create_JWT():
    developer_id = "61a4abf9-8560-444c-b889-3991c9caf467"   
    key_id       = "112b9497-e633-4701-a0b1-a16e3d8faf7b"   
    signing_secret = os.environ.get("DOORDASH_SIGNING_SECRET")
    print(signing_secret)



    def fix_padding(s: str) -> bytes:
        # DoorDash often omits '=' padding; this adds it back
        s = s.strip()
        s += "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s)

    payload = {
        "aud": "doordash",
        "iss": developer_id,
        "kid": key_id,
        "exp": math.floor(time.time() + 300),  # now + 5 minutes
        "iat": math.floor(time.time()),
    }

    key_bytes = fix_padding(signing_secret)

    token = jwt.encode(
        payload,
        key_bytes,
        algorithm="HS256",
        headers={"dd-ver": "DD-JWT-V1"},
    )

    print(token)

    return token

def create_DD_quote(token):
    url = f'{endpoint_url}/quotes'
    jwt_token = token
    headers = {
        "Authorization": "Bearer " + jwt_token,
        "Content-Type": "application/json"
    }

    request_body = {
        "external_delivery_id": "TEST-160MAIN-0007",
        "pickup_address": "160 E Main St, Northville, MI 48167",
        "pickup_business_name": "160 Main",
        "pickup_phone_number": "+17402088961",
        "dropoff_address": "14221 Levan Rd, Livonia, MI 48154",
        "dropoff_business_name": "Test Customer 2",
        "dropoff_phone_number": "+17402088962",
        "order_value": 4500,
        "tip": 600,
        "currency": "USD",
        "pickup_instructions": "Pick up at host stand.",
        "dropoff_instructions": "Leave at front door."
    }

    try:
        response = requests.post(url, headers=headers, json=request_body, timeout=10)
    except requests.RequestException as e:
        return {
            'ok': False,
            'status': None,
            'data': None,
            'error': f'Network error callin Doordash /quotes: {e}'
        }
    status = response.status_code

    # parsing JSON responses, but also if it is not JSON guard for that
    try:
        body_json = response.json()
        body_text = None
    except ValueError:
        body_json = None
        body_text= response.text

    if 200 <= status < 300:
        return {
            "ok": True,
            "status": status,
            "data" : body_json if body_json is not None else body_text,
            "error": None,
        }
    error_payload = body_json if body_json is not None else body_text,
    return{
        "ok": False,
        "status": status,
        "data": None,
        'error': f'Doordash returned HTTP {status}: {error_payload}'
    }





quote = create_DD_quote(create_JWT())
print(quote)