import json
import os
import sys
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Add libs to path
LIBS_PATH = Path(__file__).resolve().parent.parent.parent / 'libs'
sys.path.insert(0, str(LIBS_PATH))
import llm_service


def index(request):
    """Serve the main page"""
    return render(request, 'body.html')


# ============================================================================
# Configuration API
# ============================================================================

@csrf_exempt
def api_config(request):
    """GET/POST /api/config - Load or save configuration"""
    if request.method == 'GET':
        config = llm_service.load_config()
        if config:
            return JsonResponse(config)
        else:
            return JsonResponse({'error': 'Failed to load configuration'}, status=500)
    
    elif request.method == 'POST':
        try:
            config = llm_service.load_config()
            if not config:
                return JsonResponse({'error': 'Failed to load configuration'}, status=500)
            
            new_defaults = json.loads(request.body)
            config['frontend_defaults'] = new_defaults
            
            if llm_service.save_config(config):
                return JsonResponse({'success': True, 'message': 'Configuration saved successfully'})
            else:
                return JsonResponse({'error': 'Failed to save configuration'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)



# ============================================================================
# Models API
# ============================================================================

def api_get_models(request):
    """GET /api/models - Return list of available language models"""
    config = llm_service.load_config()
    if config and 'language_models' in config:
        models = []
        for model in config['language_models']:
            models.append({
                'file_name': model.get('file_name', ''),
                'nickname': model.get('nickname', model.get('file_name', '')),
                'parameters_billions': model.get('parameters_billions', 0)
            })
        return JsonResponse(models, safe=False)
    else:
        return JsonResponse({'error': 'Failed to load models'}, status=500)


def api_refresh_models(request):
    """GET /api/models/refresh - Check if model files exist in configured directories"""
    try:
        config = llm_service.load_config()
        if not config:
            return JsonResponse({'error': 'Failed to load configuration'}, status=500)
            
        model_dirs = config.get('model_directories', {})
        lang_dir = model_dirs.get('language', '')
        voice_dir = model_dirs.get('voice', '')
        
        results = {
            'language': [],
            'voice': []
        }
        
        # Check language models
        for model in config.get('language_models', []):
            path = os.path.join(lang_dir, model['file_name']) if lang_dir else ''
            exists = os.path.exists(path) if path else False
            results['language'].append({
                **model,
                'exists': exists,
                'path': path
            })
            
        # Check voice models
        for model in config.get('voice_models', []):
            path = os.path.join(voice_dir, model['file_name']) if voice_dir else ''
            exists = os.path.exists(path) if path else False
            results['voice'].append({
                **model,
                'exists': exists,
                'path': path
            })
            
        return JsonResponse(results)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_manage_models(request):
    """POST /api/models/manage - Add or remove models"""
    try:
        config = llm_service.load_config()
        if not config:
            return JsonResponse({'error': 'Failed to load configuration'}, status=500)
            
        data = json.loads(request.body)
        action = data.get('action')
        model_type = data.get('type')  # 'language' or 'voice'
        model_data = data.get('data')
        
        if model_type not in ['language', 'voice']:
            return JsonResponse({'error': 'Invalid model type'}, status=400)
            
        key = f"{model_type}_models"
        
        # Ensure key exists
        if key not in config:
            config[key] = []
        
        if action == 'add':
            # Check if model already exists
            for m in config[key]:
                if m['file_name'] == model_data['file_name']:
                    return JsonResponse({'error': 'Model already exists'}, status=400)
            config[key].append(model_data)
            
        elif action == 'remove':
            file_name = model_data.get('file_name')
            config[key] = [m for m in config[key] if m['file_name'] != file_name]
            
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
        if llm_service.save_config(config):
            return JsonResponse({'success': True, 'message': 'Models updated successfully', 'models': config[key]})
        else:
            return JsonResponse({'error': 'Failed to save configuration'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_directories(request):
    """POST /api/config/directories - Update model directories"""
    try:
        config = llm_service.load_config()
        if not config:
            return JsonResponse({'error': 'Failed to load configuration'}, status=500)
        
        directories = json.loads(request.body)
        if 'language' in directories and 'voice' in directories:
            config['model_directories'] = directories
            if llm_service.save_config(config):
                return JsonResponse({'success': True, 'message': 'Directories updated successfully'})
        
        return JsonResponse({'error': 'Invalid directory data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# Server Control API
# ============================================================================

def api_server_status(request):
    """GET /api/server/status - Get current server status"""
    status = llm_service.get_server_status()
    return JsonResponse({'status': status})


@csrf_exempt
@require_http_methods(["POST"])
def api_server_start(request):
    """POST /api/server/start - Start the LLM server"""
    try:
        config_data = json.loads(request.body) if request.body else None
        
        if not config_data:
            full_config = llm_service.load_config()
            if full_config and 'frontend_defaults' in full_config:
                config_data = full_config['frontend_defaults']
            else:
                return JsonResponse({'error': 'No configuration provided'}, status=400)
        
        success, message = llm_service.start_server(config_data)
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'error': message}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_server_stop(request):
    """POST /api/server/stop - Stop the LLM server"""
    try:
        success, message = llm_service.stop_server()
        
        if success:
            return JsonResponse({'success': True, 'message': message})
        else:
            return JsonResponse({'error': message}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
