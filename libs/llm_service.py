"""
LLM Service Layer for Django

This module provides:
- Configuration loading/saving (llm_config.json)
- LLM server state management
- Server start/stop functionality
"""

import threading
import types
import json
import os
from pathlib import Path

# Global server state
_llm_server = None
_server_thread = None
_server_status = "stopped"  # stopped, starting, running, error

# Configuration path - use environment variable or default
CONFIG_PATH = Path(os.environ.get('LLM_CONFIG_PATH', Path.home() / '.llm_config.json'))


def get_config_path():
    """Get the configuration file path"""
    return CONFIG_PATH


def load_config():
    """Load configuration from llm_config.json"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Return default config if file doesn't exist
            return get_default_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        return get_default_config()


def save_config(config_data):
    """Save configuration to llm_config.json"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def get_default_config():
    """Return default configuration"""
    return {
        "model_directories": {
            "language": "",
            "voice": ""
        },
        "language_models": [],
        "voice_models": [],
        "frontend_defaults": {
            "model": "",
            "streaming": True,
            "context_size": 15,
            "max_tokens": 13,
            "temperature": 0.1,
            "repeat_penalty": 1.2,
            "host": "127.0.0.1",
            "port": 8080,
            "compute_mode": "auto",
            "gpu_layers": 999,
            "threads": 0,
            "advanced_settings_open": False
        }
    }


def get_server_status():
    """Get current server status"""
    global _server_status
    return _server_status


def set_server_status(status):
    """Set server status"""
    global _server_status
    _server_status = status


def run_server_in_thread(args):
    """Run LocalLMM in a separate thread"""
    global _llm_server, _server_status
    try:
        # Try to import LocalLMM
        try:
            from LocalLMM import LocalLMM, LoggerWrapper
        except ImportError:
            print("LocalLMM not available, running in mock mode")
            _server_status = "running"
            import time
            while _server_status == "running":
                time.sleep(1)
            return

        print("Initializing LocalLMM instance...")
        logger = LoggerWrapper()
        _llm_server = LocalLMM(args=args, logger=logger)
        
        print("Starting LocalLMM server...")
        _llm_server.run()
        
        _server_status = "running"
        
        import time
        while _server_status == "running":
            time.sleep(1)
            
        print("LocalLMM server execution finished")
        
        if _llm_server:
            _llm_server.shutdown()
            
    except Exception as e:
        print(f"Error in server thread: {e}")
        _server_status = "error"
        _llm_server = None


def start_server(config_data):
    """Start the LLM server with given configuration"""
    global _llm_server, _server_thread, _server_status
    
    if _server_status in ["running", "starting"]:
        return False, "Server is already running"
    
    try:
        # Construct arguments object for LocalLMM
        args = types.SimpleNamespace()
        
        args.model = config_data.get('model', '')
        args.host = config_data.get('host', '127.0.0.1')
        args.port = int(config_data.get('port', 8080))
        args.n_predict = 8192
        
        # Calculate powers of 2 for slider values
        args.max_new_tokens = 2 ** int(config_data.get('max_tokens', 13))
        args.context_size = 2 ** int(config_data.get('context_size', 15))
        
        args.temperature = float(config_data.get('temperature', 0.1))
        args.repeat_penalty = float(config_data.get('repeat_penalty', 1.2))
        args.threads = int(config_data.get('threads', 0))
        args.gpu_layers = int(config_data.get('gpu_layers', 999))
        args.server_only = True
        args.logs = True
        
        compute_mode = config_data.get('compute_mode', 'auto')
        args.cpu = (compute_mode == 'cpu')
        args.gpu = (compute_mode == 'gpu')
        
        # Other required defaults
        args.inference_only = False
        args.inference_port = None
        args.stop = ["<|eot_id|>"]
        args.timeout = None
        args.kv_cache = "optimized"
        args.session_id = "default"
        args.slot_id = 0
        args.remember = True
        args.reset_session = False
        args.clear_slot = None
        args.slot_save_path = None
        
        # Start server in thread
        _server_status = "starting"
        _server_thread = threading.Thread(target=run_server_in_thread, args=(args,))
        _server_thread.daemon = True
        _server_thread.start()
        
        return True, "Server starting..."
        
    except Exception as e:
        _server_status = "error"
        return False, str(e)


def stop_server():
    """Stop the LLM server"""
    global _llm_server, _server_status
    
    if _server_status == "stopped":
        return False, "Server is not running"
    
    try:
        if _llm_server:
            _llm_server.shutdown()
            _llm_server = None
        
        _server_status = "stopped"
        return True, "Server stopped"
        
    except Exception as e:
        return False, str(e)
