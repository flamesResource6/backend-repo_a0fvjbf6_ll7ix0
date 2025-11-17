import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from database import db, create_document, get_documents
from schemas import User, BlogPost, ContactMessage

app = FastAPI(title="SaaS Landing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "SaaS Landing Backend Running"}

# Public: Pricing plans
class PricingPlan(BaseModel):
    id: str
    name: str
    price: str
    features: List[str]
    popular: bool = False

@app.get("/api/pricing", response_model=List[PricingPlan])
def get_pricing():
    return [
        PricingPlan(
            id="starter",
            name="Starter",
            price="$9/mo",
            features=["Up to 3 projects", "Basic analytics", "Email support"],
        ),
        PricingPlan(
            id="pro",
            name="Pro",
            price="$29/mo",
            features=["Unlimited projects", "Advanced analytics", "Priority support", "Team seats"],
            popular=True,
        ),
        PricingPlan(
            id="enterprise",
            name="Enterprise",
            price="Custom",
            features=["SAML SSO", "Dedicated support", "Custom limits", "Onboarding"],
        ),
    ]

# Auth (simple stub for demo; real auth would use hashing/JWT)
class AuthRequest(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    message: str
    user_email: EmailStr

@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(payload: AuthRequest):
    # In real world: hash password, check duplicate email, etc.
    password_hash = f"hash::{payload.password}"
    user = User(name=payload.name or "User", email=payload.email, password_hash=password_hash)
    try:
        user_id = create_document("user", user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return AuthResponse(message="Registered successfully", user_email=payload.email)

@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(payload: AuthRequest):
    # This is a stub: simply echoes success. You can extend to verify from DB.
    return AuthResponse(message="Logged in", user_email=payload.email)

# Contact form
class ContactResponse(BaseModel):
    message: str

@app.post("/api/contact", response_model=ContactResponse)
def submit_contact(msg: ContactMessage):
    try:
        create_document("contactmessage", msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ContactResponse(message="Thanks! We'll be in touch.")

# Blog endpoints
class BlogOut(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: str
    tags: List[str] = []
    published: bool = False
    published_at: Optional[datetime] = None

@app.get("/api/blog", response_model=List[BlogOut])
def list_blog_posts():
    try:
        docs = get_documents("blogpost", {"published": True}, limit=20)
    except Exception as e:
        # If DB isn't set up, return some demo posts
        demo = [
            BlogOut(
                title="Welcome to our blog",
                slug="welcome",
                excerpt="Insights on building modern SaaS.",
                content="This is a demo post. Connect the database to fetch real posts.",
                author="Team",
                tags=["saas", "product"],
                published=True,
                published_at=datetime.now(timezone.utc),
            )
        ]
        return demo

    out: List[BlogOut] = []
    for d in docs:
        out.append(
            BlogOut(
                title=d.get("title", "Untitled"),
                slug=d.get("slug", "post"),
                excerpt=d.get("excerpt"),
                content=d.get("content", ""),
                author=d.get("author", ""),
                tags=d.get("tags", []),
                published=d.get("published", False),
                published_at=d.get("published_at"),
            )
        )
    return out

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
