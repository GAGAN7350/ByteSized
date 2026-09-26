from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.rtl.router import router as rtl_router
from backend.routers.second_ext.router import router as second_ext_router

app = FastAPI(
    title="SiliconBob Backend API",
    description="Electronic Chip Design & RTL Optimization Engine for IBM Bob — Multi-Extension Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# MOUNT EXTENSION ROUTERS
# Add one include_router() call per new extension below.
# =====================================================================
app.include_router(rtl_router)
app.include_router(second_ext_router)
