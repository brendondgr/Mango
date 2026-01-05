"""
Flask Web Server for LLM Server Control Frontend

This module provides a Flask web server with API routes for:
- Serving the main frontend page
- Loading and saving configuration settings
- Retrieving available language models
"""

import threading
import types
from flask import Flask, render_template, jsonify, request
import json
import os
from pathlib import Path
from LocalLMM import LocalLMM, LoggerWrapper
from LocalLMM.utils.config_initializer import get_config_path

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

# Path to llm_config.json
CONFIG_PATH = get_config_path()

# Global server state
llm_server = None
server_thread = None
server_status = "stopped"  # stopped, starting, running, error


def load_config():
    """Load configuration from llm_config.json"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def save_config(config_data):
    """Save configuration to llm_config.json"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def run_server_in_thread(args):
    """Run LocalLMM in a separate thread"""
    global llm_server, server_status
    try:
        print("Initializing LocalLMM instance...")
        # Initialize logger
        logger = LoggerWrapper()
        llm_server = LocalLMM(args=args, logger=logger)
        
        print("Starting LocalLMM server...")
        # Status is already "starting" from the route handler
        llm_server.run()
        
        # run() blocks until model is loaded in server-only mode.
        # Now we are ready.
        server_status = "running"
        
        # Keep thread alive while server is running
        # LocalLMM.run() returns immediately in server-only mode, 
        # so we need to prevent the thread from exiting.
        import time
        while server_status == "running":
            time.sleep(1)
            
        print("LocalLMM server execution finished")
        
        # Ensure cleanup if loop exited for other reasons
        if llm_server:
            llm_server.shutdown()
            
    except Exception as e:
        print(f"Error in server thread: {e}")
        server_status = "error"
        llm_server = None


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('body.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return current configuration"""
    config = load_config()
    if config:
        return jsonify(config)
    else:
        return jsonify({'error': 'Failed to load configuration'}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update frontend_defaults in configuration"""
    try:
        # Load current config
        config = load_config()
        if not config:
            return jsonify({'error': 'Failed to load configuration'}), 500
        
        # Get updated frontend defaults from request
        new_defaults = request.json
        
        # Update the frontend_defaults section
        config['frontend_defaults'] = new_defaults
        
        # Save config
        if save_config(config):
            return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models', methods=['GET'])
def get_models():
    """Return list of available language models"""
    config = load_config()
    if config and 'language_models' in config:
        models = []
        for model in config['language_models']:
            models.append({
                'file_name': model.get('file_name', ''),
                'nickname': model.get('nickname', model.get('file_name', '')),
                'parameters_billions': model.get('parameters_billions', 0)
            })
        return jsonify(models)
    else:
        return jsonify({'error': 'Failed to load models'}), 500


@app.route('/api/server/status', methods=['GET'])
def get_server_status():
    """Get current server status"""
    global server_status
    return jsonify({'status': server_status})


@app.route('/api/server/start', methods=['POST'])
def start_server():
    """Start the LLM server with current configuration"""
    global llm_server, server_thread, server_status
    
    if server_status == "running" or server_status == "starting":
        return jsonify({'error': 'Server is already running'}), 400
        
    try:
        # Get configuration from request or file
        config_data = request.json
        if not config_data:
            full_config = load_config()
            if full_config and 'frontend_defaults' in full_config:
                config_data = full_config['frontend_defaults']
            else:
                return jsonify({'error': 'No configuration provided'}), 400
        
        # Construct arguments object for LocalLMM
        # We need to map frontend config keys to LocalLMM args
        args = types.SimpleNamespace()
        
        # Default mappings
        args.model = config_data.get('model', '')
        args.host = config_data.get('host', '127.0.0.1')
        args.port = int(config_data.get('port', 8080))
        args.n_predict = 8192 # Default from argparse
        
        # Calculate powers of 2 for slider values
        # UI sends slider value (e.g. 15), backend needs 2^15
        args.max_new_tokens = 2 ** int(config_data.get('max_tokens', 13))
        args.context_size = 2 ** int(config_data.get('context_size', 15))
        
        args.temperature = float(config_data.get('temperature', 0.1))
        args.repeat_penalty = float(config_data.get('repeat_penalty', 1.2))
        args.threads = int(config_data.get('threads', 0))
        args.gpu_layers = int(config_data.get('gpu_layers', 999))
        args.server_only = True # Always run as server-only from web UI
        args.logs = True
        
        # Handle compute mode
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
        server_status = "starting"
        server_thread = threading.Thread(target=run_server_in_thread, args=(args,))
        server_thread.daemon = True
        server_thread.start()
        
        return jsonify({'success': True, 'message': 'Server starting...'})
        
    except Exception as e:
        server_status = "error"
        return jsonify({'error': str(e)}), 500


@app.route('/api/server/stop', methods=['POST'])
def stop_server():
    """Stop the LLM server"""
    global llm_server, server_status
    
    if server_status == "stopped":
        return jsonify({'error': 'Server is not running'}), 400
        
    try:
        if llm_server:
            llm_server.shutdown()
            llm_server = None
        
        server_status = "stopped"
        return jsonify({'success': True, 'message': 'Server stopped'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/directories', methods=['POST'])
def update_directories():
    """Update model directories in configuration"""
    try:
        config = load_config()
        if not config:
            return jsonify({'error': 'Failed to load configuration'}), 500
        
        directories = request.json
        if 'language' in directories and 'voice' in directories:
            config['model_directories'] = directories
            if save_config(config):
                return jsonify({'success': True, 'message': 'Directories updated successfully'})
        
        return jsonify({'error': 'Invalid directory data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/manage', methods=['POST'])
def manage_models():
    """Add or remove models"""
    try:
        config = load_config()
        if not config:
            return jsonify({'error': 'Failed to load configuration'}), 500
            
        action = request.json.get('action')
        model_type = request.json.get('type') # 'language' or 'voice'
        model_data = request.json.get('data')
        
        if model_type not in ['language', 'voice']:
            return jsonify({'error': 'Invalid model type'}), 400
            
        key = f"{model_type}_models"
        
        if action == 'add':
            # Check if model already exists
            for m in config[key]:
                if m['file_name'] == model_data['file_name']:
                    return jsonify({'error': 'Model already exists'}), 400
            config[key].append(model_data)
            
        elif action == 'remove':
            file_name = model_data.get('file_name')
            config[key] = [m for m in config[key] if m['file_name'] != file_name]
            
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
        if save_config(config):
            return jsonify({'success': True, 'message': 'Models updated successfully', 'models': config[key]})
        else:
            return jsonify({'error': 'Failed to save configuration'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/refresh', methods=['GET'])
def refresh_models_status():
    """Check if model files exist in the configured directories"""
    try:
        config = load_config()
        if not config:
            return jsonify({'error': 'Failed to load configuration'}), 500
            
        lang_dir = config['model_directories'].get('language', '')
        voice_dir = config['model_directories'].get('voice', '')
        
        results = {
            'language': [],
            'voice': []
        }
        
        # Check language models
        for model in config.get('language_models', []):
            path = os.path.join(lang_dir, model['file_name'])
            exists = os.path.exists(path)
            results['language'].append({
                **model,
                'exists': exists,
                'path': path
            })
            
        # Check voice models
        for model in config.get('voice_models', []):
            path = os.path.join(voice_dir, model['file_name'])
            exists = os.path.exists(path)
            results['voice'].append({
                **model,
                'exists': exists,
                'path': path
            })
            
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Run Flask app on port 5001 (to avoid conflict with other apps)
    app.run(host='127.0.0.1', port=5001, debug=True)

