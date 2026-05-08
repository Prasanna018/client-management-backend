from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, workspaces, tasks
from app.db.mongodb import connect_to_mongo, close_mongo_connection, settings

app = FastAPI(title="ClientFlow API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        settings.FRONTEND_URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and Shutdown events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])

@app.get("/")
async def root():
    return {"message": "Welcome to ClientFlow API"}

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Backend is live"}
