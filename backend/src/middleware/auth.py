from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from firebase_admin import auth
from functools import wraps

security = HTTPBearer()

async def verify_token(request: Request):
    if "Authorization" not in request.headers:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = request.headers["Authorization"].split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        request.state.user_id = decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        await verify_token(request)
        return await func(request, *args, **kwargs)
    return wrapper