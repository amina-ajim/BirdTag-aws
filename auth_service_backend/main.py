# main.py

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import boto3
from botocore.exceptions import ClientError

# Import your existing modules
from json_loader import load_config   # load_config takes no arguments
from signup import signup, get_secret_hash  # <-- import the helper
from login import login               # expects: login(username, password)

# ─── Create FastAPI and immediately add CORS ───────────────────────────────────
app = FastAPI(title="AuthService with Cognito + FastAPI")

# Allow the frontend (port 8080) to talk to this API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Load Cognito config from Client_ID.json ───────────────────────────────────
try:
    CONFIG = load_config()
except Exception as e:
    raise RuntimeError(f"Could not load Cognito config: {e}")

AWS_REGION     = CONFIG["region"]
CLIENT_ID      = CONFIG["client_id"]
AWS_ACCESS_KEY = CONFIG.get("aws_access_key_id")
AWS_SECRET_KEY = CONFIG.get("aws_secret_access_key")
AWS_SESSION    = CONFIG.get("aws_session_token")

# ─── Pydantic models for request & response bodies ─────────────────────────────

class SignupRequest(BaseModel):
    username: str = Field(..., example="alice123@example.com")
    password: str = Field(..., example="Str0ngP@ssw0rd!")
    email: EmailStr
    family_name: str = Field(..., example="Smith")
    given_name: str = Field(..., example="Alice")


class ConfirmRequest(BaseModel):
    username: str = Field(..., example="alice123@example.com")
    confirmation_code: str = Field(..., example="123456")


class LoginRequest(BaseModel):
    username: str = Field(..., example="alice123@example.com")
    password: str = Field(..., example="Str0ngP@ssw0rd!")


class LoginResponse(BaseModel):
    id_token: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_endpoint(req: SignupRequest):
    try:
        result = signup(
            req.username,
            req.password,
            req.email,
            req.family_name,
            req.given_name
        )
        return {
            "message": "Signup successful. Check your email for the confirmation code.",
            "cognito_response": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sign-up failed: {str(e)}"
        )


@app.post("/confirm", status_code=status.HTTP_200_OK)
async def confirm_endpoint(req: ConfirmRequest):
    try:
        client = boto3.client(
            "cognito-idp",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_session_token=AWS_SESSION,
            region_name=AWS_REGION,
        )
        resp = client.confirm_sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(req.username),   # <-- added
            Username=req.username,
            ConfirmationCode=req.confirmation_code,
        )
        return {
            "message": "User confirmed. You can now log in.",
            "cognito_response": resp
        }
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation failed: {e.response['Error']['Message']}"
        )


@app.post("/login", response_model=LoginResponse)
async def login_endpoint(req: LoginRequest):
    try:
        resp = login(req.username, req.password)
        auth = resp.get("AuthenticationResult", {})
        return LoginResponse(
            id_token=auth["IdToken"],
            access_token=auth["AccessToken"],
            refresh_token=auth.get("RefreshToken"),
            expires_in=auth.get("ExpiresIn"),
            token_type=auth.get("TokenType"),
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {e.response['Error']['Message']}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )


@app.get("/health", status_code=200)
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)