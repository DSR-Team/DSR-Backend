from fastapi.testclient import TestClient

from main import app 


client = TestClient(app)

address = "tz1SZzEGibUCrpgL2FNdBf665JRQV8Qax2LZ"


def test_get_payload():
    response = client.get(f"/login/{address}/payload/")
    assert response.status_code == 200
    
contract = "KT1AFq5XorPduoYyWxs5gEyrFK6fVjJVbtCj"
tokenId = "7889"

def test_get_token_by_contract_id():
    response = client.get(f"/token_metadata/{contract}/{tokenId}")
    print(response.json())
    assert response.status_code == 200
