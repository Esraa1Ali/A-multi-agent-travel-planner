"""Start the TheTerminal API from the repo root."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["smart-travel/api", "agents"],
        app_dir="smart-travel",
    )
