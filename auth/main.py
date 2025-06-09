from fastapi import FastAPI, Form
from auth.signup import signup_user
from auth.confirm_user import confirm_signup
from auth.login import login_user

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
import boto3

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

REGION = "us-east-1"
CLIENT_ID = "rb6c6jodg8k6nc6tu1jo8q414"
USER_POOL_ID = "us-east-1_38PS4mWzu"
cognito = boto3.client("cognito-idp", region_name=REGION)

@app.post("/signup")
def signup(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    given_name: str = Form(...),
    family_name: str = Form(...)
):
    return signup_user(username, password, email, family_name, given_name)

@app.post("/confirm")
def confirm(email: str = Form(...), code: str = Form(...)):
    return confirm_signup(email, code)


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        print("Redirecting to welcome page...")
        return RedirectResponse(url="/welcome-page", status_code=303)
    except Exception as e:
        return JSONResponse(status_code=401, content={"message": str(e)})

@app.get("/signup-page", response_class=HTMLResponse)
def get_signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/confirm-page", response_class=HTMLResponse)
def get_confirm_form(request: Request):
    return templates.TemplateResponse("confirm.html", {"request": request})

@app.get("/login-page", response_class=HTMLResponse)
def get_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/welcome-page", response_class=HTMLResponse)
def get_welcome_page(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

