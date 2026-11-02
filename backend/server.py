from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
from contextlib import suppress
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr, StrictBool, field_validator
from typing import List
from pymongo.errors import DuplicateKeyError, PyMongoError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
from waitlist_emails import email_worker, queue_confirmation

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://127.0.0.1:27017')
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get('DB_NAME', 'valandala_website')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

WAITLIST_MESSAGE = "Ești pe listă! Te anunțăm pe email când se lansează Valandala."


class WaitlistSignup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", max_length=80)
    email: EmailStr = Field(max_length=254)
    consent: StrictBool
    website: str = Field(default="", max_length=200)

    @field_validator("name", "email", mode="before")
    @classmethod
    def trim_input(cls, value):
        return value.strip() if isinstance(value, str) else value


@app.on_event("startup")
async def prepare_waitlist():
    await db.launch_waitlist.create_index("email", unique=True)
    app.state.email_worker = asyncio.create_task(email_worker(db))


@api_router.post("/waitlist")
async def join_waitlist(signup: WaitlistSignup):
    if not signup.consent:
        raise HTTPException(422, "Acordul pentru notificarea lansării este necesar.")
    if signup.website:
        return {"success": True, "message": WAITLIST_MESSAGE}
    email = str(signup.email).casefold()
    try:
        # A unique email index and upsert make retries/concurrent requests idempotent.
        await db.launch_waitlist.update_one(
            {"email": email},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()), "email": email, "name": signup.name,
                "consent": True, "consent_version": "launch-notification-v1",
                "consent_text": "Sunt de acord să primesc un email de la Valandala despre lansarea aplicației.",
                "created_at": datetime.now(timezone.utc), "source": "presentation_website",
                "status": "subscribed",
            }},
            upsert=True,
        )
    except DuplicateKeyError:
        pass
    except PyMongoError:
        logger.exception("Waitlist storage unavailable")
        raise HTTPException(503, "Înscrierea nu poate fi salvată momentan. Te rugăm să încerci din nou.") from None
    try:
        subscriber = await db.launch_waitlist.find_one({"email": email, "status": "subscribed"})
        if subscriber:
            await queue_confirmation(db, subscriber)
    except PyMongoError:
        logger.exception("Waitlist receipt could not be queued")
        raise HTTPException(503, "Înscrierea este salvată, dar confirmarea nu a putut fi pregătită. Poți încerca din nou.") from None
    return {"success": True, "message": WAITLIST_MESSAGE}


# Serve the presentation directly too, so its form and API share an origin.
PUBLIC_DIR = ROOT_DIR.parent / "frontend" / "public"
app.mount("/assets", StaticFiles(directory=PUBLIC_DIR / "assets"), name="presentation-assets")


@app.get("/", include_in_schema=False)
@app.get("/valandala-landing.html", include_in_schema=False)
async def presentation_page():
    return FileResponse(PUBLIC_DIR / "valandala-landing.html")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=[origin.strip() for origin in os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    task = getattr(app.state, "email_worker", None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    client.close()