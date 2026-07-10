import modal

app = modal.App("data-analysis-api")

# Build the image with dependencies and mount backend source at runtime.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("backend/requirements1.txt")
    .add_local_dir(
        "backend",
        remote_path="/root/backend",
        ignore=[
            ".env",
            "__pycache__",
            "**/__pycache__",
            "*.pyc",
            "*.csv",
            "charts",
            "images",
            "interactive_charts",
            "scratch",
            "uploads",
            "winscp_uploaded_ent_runnning",
        ],
    )
)

secrets = [modal.Secret.from_name("data-api-secrets")]

# Persistent volume for uploaded CSVs, archived files, and generated chart images.
volume = modal.Volume.from_name("data-analysis-storage", create_if_missing=True)


@app.function(
    image=image,
    secrets=secrets,
    volumes={"/root/data": volume},
    timeout=600,
)
@modal.asgi_app()
def fastapi_app():
    import sys

    sys.path.insert(0, "/root/backend")
    from main import app as web_app

    return web_app
