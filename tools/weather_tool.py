import requests

def get_weather(city: str):
    
    url = f"https://wttr.in/{city}?format=j1"
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=10,
    )
    
    response.raise_for_status()
    
    return response.json()