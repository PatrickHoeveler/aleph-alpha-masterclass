from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from service.db_service import SQLiteDatabase
from service.dependencies import with_settings
from service.kernel import HttpKernel
from service.routes import router
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

settings = with_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = HttpKernel(str(settings.pharia_kernel_address))
    database = SQLiteDatabase(settings.database_path, auto_connect=True)
    yield {"kernel": client, "database": database}
    await client.shutdown()
    database.disconnect()


app = FastAPI(lifespan=lifespan)

###############################################################################
# WARNING: Do not modify this CORS configuration unless you fully understand    #
# the Pharia Applications Proxy implications.                                   #
#                                                                              #
# This configuration is strictly for local development/preview purposes.        #
# In production deployments, CORS is automatically handled by PhariaAI.     #
# Modifying these settings in production will cause header conflicts.           #
###############################################################################
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

app.include_router(router)


###############################################################################
# WARNING: Do not modify the UI serving configuration below unless you fully    #
# understand the implications.                                                  #
#                                                                              #
# The StaticFiles mount is required to serve the Application UI in          #
# PhariaAssistant.                                                            #
###############################################################################
app.mount("/ui", StaticFiles(directory="ui-artifacts"), name="ui")
app.mount("/data", StaticFiles(directory="data"), name="data")


def main():
    uvicorn.run("service.main:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
