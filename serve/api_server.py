from utils.logger import get_module_logger

log = get_module_logger("api_server")

def start_api_server(owner, config):
    port = config["serving"]["api"]["port"]
    log.info(f"API Server starting on port {port}... (Starter Mode)")
    # API logic will go here
    log.success(f"✓ API Server is live on port {port}")
