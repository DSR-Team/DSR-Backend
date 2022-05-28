import random
import string
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
import os
from pyblake2 import blake2b
import base58check
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ipfs_prefix = "https://assets.akaswap.com/ipfs/"
def generate_room_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def pack_str(msg):
    msg_hex = msg.encode().hex()
    msg_len = len(msg).to_bytes(4,'big').hex()
    prefix = bytes.fromhex('0501').hex()
    msg_concat_raw = prefix + msg_len + msg_hex
    return msg_concat_raw
def hash_str(msg_concat_raw):
    msg_pack = pack_str(msg_concat_raw)
    msg_concat = bytes.fromhex(msg_pack)
    b2b = blake2b(digest_size=32)
    b2b.update(msg_concat)
    msg_hashed = b2b.digest()
    return msg_hashed
prefix = {
  "edsig": [9, 245, 205, 134, 18],
  "edpk": [13, 15, 37, 217]
}
def b58decode(enc, prefix):
      return base58check.b58decode(enc)[len(prefix):]
def verifyUserSignature(msg, sig, pubKey, raw=True):
    sig_b = b58decode(sig, prefix["edsig"])[:-4]
    if raw:
        msg_b = bytes.fromhex(msg)
        b2b = blake2b(digest_size=32)
        b2b.update(msg_b)
        msg_hashed = b2b.digest()
    else:
        msg_hashed = hash_str(msg)
      
    vk_b = b58decode(pubKey, prefix["edpk"])[:-4]
    vk = VerifyKey(vk_b)
    
    try:
        ans =  vk.verify(msg_hashed, sig_b)
        #print(ans )
        #print("signature is good")
        return ans
    except BadSignatureError:
        #print("signature is bad!")
        raise HTTPException(status_code=400, detail="Bad Signature")
        #return 'Bad Signature',400
async def get_current_user(token: str = Depends(oauth2_scheme)):
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    #print("token:", token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        #print("payload:", payload)
        username:str = payload.get("addr")
        expires = payload.get("exp")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, expires=expires)
        
        #print("token_data:", token_data)
        now = utc.localize(datetime.utcnow())
        if expires is None:
            raise credentials_exception
        if (now > token_data.expires):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    """if expires is None:
        raise credentials_exception
    if datetime.utcnow() > token_data.expires:
        raise credentials_exception"""

    #user = get_user(fake_users_db, username=token_data.username)
    #if user is None:
    #    raise credentials_exception
    return token_data.username
class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None
async def get_current_active_user(current_user: User = Depends(get_current_user)):
    
    #if current_user.disabled:
    #    raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
def check_metadata(update_dict, address):
    update_dict = dict(update_dict)
    assert "metadata" in update_dict

    if (len(update_dict["metadata"])!=6):
            raise HTTPException(status_code=400, detail="metadata length error")
    nft_mimeTypes = []
    for i in range(len(update_dict["metadata"])):
        if (update_dict["metadata"][i]=={}):
            nft_mimeTypes.append({})
            continue
        tokenId = update_dict["metadata"][i]["tokenId"]
        contract = update_dict["metadata"][i]["contract"]
        
        
        r = requests.get("https://api.akaswap.com/v2/fa2tokens/{contract}/{tokenId}".format(contract=contract, tokenId=tokenId)).json()
        if (r=={}):
            raise HTTPException(status_code=400, detail="tokenID {} not found".format(tokenId))
        
        owners = r.get("owners")
        
        if (address not in owners):
            raise HTTPException(status_code=400, detail="token {} not yours".format(tokenId))
        nft_mimeTypes.append( r["mimeType"] )
    try:
        constraint = [("image", "video", "audio"),("image", "video", "audio"),("image", "video", "audio"),("image", "video", "audio"),"model","model"]
        for i in range(6):
                assert nft_mimeTypes[i]=={} or nft_mimeTypes[i].startswith(constraint[i]), "array {} should not be {}, it should be {}".format(i, nft_mimeTypes[i], constraint[i])
    except AssertionError as e:
        print("error:",e)
        raise HTTPException(status_code=400, detail=str(e))

    return update_dict
def format_ipfs_url(hash):
    return ipfs_prefix + hash
def get_nft(address, query_sting=""):
    url = "https://api.akaswap.com/v2/accounts/{address}/fa2tokens"+query_sting
    url = url.format(address=address)
    print(url)
    nfts = requests.get(url).json()
    #print(nfts)
    for i in range(len(nfts["tokens"])):
        pop_field = ["royalties", "ownerAliases", "amount", "owner","highestSoldPrice", "highestSoldTime", "sale", "additionalInfo", "recentlySoldPrice","recentlySoldTime"]
        format_ipfs_field = ["artifactUri", "displayUri", "thumbnailUri"]
        if type(nfts["tokens"][i]["recentlySoldPrice"])==float:
            nfts["tokens"][i]["latestSoldPrice"] = nfts["tokens"][i]["recentlySoldPrice"]/1e6
        
        for field in pop_field:
            nfts["tokens"][i].pop(field, None)
        for field in format_ipfs_field:
            nfts["tokens"][i][field] = format_ipfs_url(nfts["tokens"][i][field].replace("ipfs://", ""))

    return {"tokens":nfts["tokens"], "count":nfts["count"]}

def format_nft_metadata(result):
    if type(result["recentlySoldPrice"])==float:
        result["latestSoldPrice"] = result["recentlySoldPrice"]/1e6

    pop_field = ["aliases", "owners", "royalties", "ownerAliases", "amount", "highestSoldPrice", "highestSoldTime", "recentlySoldPrice", "recentlySoldTime", "sale", "additionalInfo"]
    for field in pop_field:
        result.pop(field, None)
    result.update({"artifactUri":result["artifactUri"].replace("ipfs://", ipfs_prefix)})
    result.update({"displayUri":result["displayUri"].replace("ipfs://", ipfs_prefix)})
    result.update({"thumbnailUri":result["thumbnailUri"].replace("ipfs://", ipfs_prefix)})
    return result
