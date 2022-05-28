from tools import *
from mongo import *
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
from datetime import datetime, timedelta
import pymongo
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
load_dotenv()
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES")

"""_summary_
uvicorn main:app --reload
"""

origins = [
    "https://stormy-temple-44410.herokuapp.com",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://dsr-team.github.io"
]
description = """
Hello, welcome to Decentral Showroom!
"""

app = FastAPI(
    docs_url=None, redoc_url=None,  
    title="Decentral Showroom",
    description=description,
    version="0.1.0",
    contact={
        "name": "dsr team",
        "uri": "dsr-team.github.io/",
        "email": ""
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def overridden_swagger():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Decentral Showroom",
        swagger_favicon_url="/static/favicon.ico"
    )
@app.get("/redoc", include_in_schema=False)
def overridden_redoc():
	return get_redoc_html(
        openapi_url="/openapi.json", 
        title="Decentral Showroom", 
        redoc_favicon_url="/static/favicon.ico"
    )

@app.get("/login/{address}/payload/")
async def payload(address):
    now = datetime.now()
    msg = "Tezos Signed Message: Confirming my identity as {address} on https://dsr-team.github.io/, time: {timestamp}".format(
        address=address, timestamp=now)
    payload = pack_str(msg)
    # todo: save msg to db
    Col_login.insert_one({'address': address, 'msg': msg, "time": now})
    return {"payload": payload}


@app.post("/login/")
async def login(address: str = Form(""), signature: str = Form("")):
    pubKey = requests.get(
        'https://api.tzkt.io/v1/accounts/{address}'.format(address=address)).json()['publicKey']

    cursor = Col_login.find({'address': address}).sort(
        'time', pymongo.DESCENDING).limit(1)
    msg = list(cursor)[0]["msg"]
    _ = verifyUserSignature(msg=msg, sig=signature, pubKey=pubKey, raw=False)

    Col_login.delete_many({'address': address})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"addr": address}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/renew_token/")
async def renew_token(address=Depends(get_current_active_user)):

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"addr": address}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/rooms/create/")
async def create_room(name: str = Form(""), image: str = Form(""), address=Depends(get_current_active_user)):
    id = "-1"
    while True:
        id = generate_room_id()
        cursor = Col_room.find({"id": id})
        if len(list(cursor)) == 0:
            break
    Col_room.insert_one({'name': name, 'image': image, 'owner': address, "id": id, "created_at": datetime.now(
    ), "updated_at": datetime.now(), "metadata": [{}, {}, {}, {}, {}, {}]})
    return {"id": id}


@app.get("/rooms/")
async def get_my_rooms(address=Depends(get_current_active_user)):
    print("address:", address)
    cursor = Col_room.find({"owner": address}, {"_id": 0})
    rooms = list(cursor)
    # print(len(list(cursor)))
    return rooms


class UpdateRoomModel(BaseModel):
    name: str | None = None
    image: str | None = None
    metadata: list | None = None


@app.put("/test/{room_id}/{address}/")
async def test(update_dict: UpdateRoomModel, room_id="", address=""):
    update_dict = {k: v for k, v in dict(update_dict).items() if v is not None}
    if "metadata" in update_dict:
        update_dict = check_metadata(update_dict, address)
    if "id" in update_dict:
        raise HTTPException(status_code=400, detail="id should not be updated")

    update_dict.update({"updated_at": datetime.now()})

    print("update_dict:", update_dict)

    return update_dict


@app.put("/rooms/{room_id}/update/")
async def update_room(update_dict: UpdateRoomModel, room_id="", address=Depends(get_current_active_user)):
    # , name=Form(""), image=Form(""),
    update_dict = {k: v for k, v in dict(update_dict).items() if v is not None}
    if "metadata" in update_dict:
        update_dict = check_metadata(update_dict, address)
    if "id" in update_dict:
        raise HTTPException(status_code=400, detail="id should not be updated")

    update_dict.update({"updated_at": datetime.now()})
    print(update_dict)
    try:
        result = Col_room.update_many(
            {'id': room_id, "owner": address}, {"$set": update_dict})
        cursor = Col_room.find({'id': room_id, "owner": address}, {"_id": 0})
        result = list(cursor)[0]
        return result
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="can't update room")


@app.get("/rooms/{room_id}/")
async def get_room_by_id(room_id):
    cursor = Col_room.find({"id": room_id}, {"_id": 0})
    rooms = list(cursor)
    if len(rooms) == 0:
        raise HTTPException(status_code=400, detail="Room not found")
    else:
        return rooms[0]


@app.delete("/rooms/{room_id}/delete/")
async def delete_room(room_id, address=Depends(get_current_active_user)):
    result = Col_room.delete_one({'id': room_id, "owner": address})
    if (result.deleted_count == 0):
        raise HTTPException(status_code=400, detail="Room not found")
    else:
        return {"result": "delete success"}


@app.get("/token_metadata/{contract}/{tokenId}")
async def get_token_metadata(contract: str, tokenId: int):
    result = requests.get("https://api.akaswap.com/v2/fa2tokens/{contract}/{tokenId}".format(
        contract=contract, tokenId=tokenId)).json()
    result = format_nft_metadata(result)
    return result


@app.get("/collections/")
async def get_my_collections(offset: int | None = 0, mimeTypes: str | None = "", address=Depends(get_current_active_user)):
    q_mimeTypes = "".join("&mimeTypes="+e for e in mimeTypes.split(","))[1:]

    result = get_nft(address, "?"+q_mimeTypes+"&offset="+str(offset))

    return result


@app.get("/accounts/{address}/nft/")
# offset:int | None=0, mimeTypes:str | None="", address=""):
async def get_collections_by_address(mimeTypes: str | None = "", offset: int | None = 0, address=""):

    q_mimeTypes = "".join("&mimeTypes="+e for e in mimeTypes.split(","))[1:]
    result = get_nft(address, "?"+q_mimeTypes+"&offset="+str(offset))
    return result
