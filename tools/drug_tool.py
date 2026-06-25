import requests

def get_drug_information(drug_name: str):
    
    url = (
        "https://api.fda.gov/drug/label.json"
        f"?search=openfda.generic_name:{drug_name}&limit=1"
    )
    
    response = requests.get(url, timeout=15)
    
    if response.status_code != 200:
        return {"error": "Drug not found"}
    
    data = response.json()["results"[0]]
    
    return{
        "purpose": data.get("purpose", []),
        "warnings": data.get("warnings", []),
        "dosage": data.get("dosage_and_administration", []),
        "adverse_reactions": data.get("adverse_reactions", []),
        "indications": data.get("indications_and_usage", [])
    }