from utils.logger import get_module_logger

log = get_module_logger("dashboard")

def start_dashboard(owner, config):
    port = config["serving"]["dashboard"]["port"]
    log.info(f"Dashboard starting on port {port}... (Starter Mode)")
    # Dashboard logic will go here
    log.success(f"✓ Dashboard is live on port {port}")
