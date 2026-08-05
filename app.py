import os
import json
import secrets
import requests
from datetime import datetime
from flask import Flask, request, Response

app = Flask(__name__)

# Fix this line - make sure it reads from environment
BASE_URL = os.environ.get('BASE_URL', 'https://your-relay.com')
PORT = int(os.environ.get('PORT', 10000))

webhooks = {}

@app.route('/create', methods=['POST'])
def create_webhook():
    data = request.get_json()
    
    if not data or 'target_url' not in data:
        return Response(
            response=json.dumps({'error': 'target_url is required'}),
            status=400,
            mimetype='application/json'
        )
    
    target_url = data['target_url']
    webhook_id = secrets.token_urlsafe(16)
    webhook_path = 'w/' + webhook_id
    
    webhooks[webhook_path] = {
        'target_url': target_url,
        'created': datetime.now().isoformat(),
        'requests': 0
    }
    
    # Debug: Print the URL being used
    print(f"BASE_URL = {BASE_URL}")
    print(f"Protected URL = {BASE_URL.rstrip('/') + '/' + webhook_path}")
    
    return Response(
        response=json.dumps({
            'protected_url': BASE_URL.rstrip('/') + '/' + webhook_path,
            'target': target_url,
            'created': webhooks[webhook_path]['created'],
            'id': webhook_id
        }),
        status=201,
        mimetype='application/json'
    )

@app.route('/w/<webhook_id>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
def relay_webhook(webhook_id):
    webhook_path = 'w/' + webhook_id
    
    if webhook_path not in webhooks:
        return Response(
            response=json.dumps({'error': 'Webhook not found'}),
            status=404,
            mimetype='application/json'
        )
    
    if request.method == 'DELETE':
        return Response(
            response=json.dumps({
                'error': 'DELETE requests are not allowed on this webhook',
                'webhook_id': webhook_id
            }),
            status=403,
            mimetype='application/json'
        )
    
    webhooks[webhook_path]['requests'] += 1
    target_url = webhooks[webhook_path]['target_url']
    
    headers = dict(request.headers)
    headers.pop('Host', None)
    headers.pop('Content-Length', None)
    
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            allow_redirects=False
        )
        
        return Response(
            response=resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
    except requests.exceptions.RequestException:
        return Response(
            response=json.dumps({'error': 'Target webhook unreachable'}),
            status=502,
            mimetype='application/json'
        )

@app.route('/stats/<webhook_id>', methods=['GET'])
def get_stats(webhook_id):
    webhook_path = 'w/' + webhook_id
    
    if webhook_path not in webhooks:
        return Response(
            response=json.dumps({'error': 'Webhook not found'}),
            status=404,
            mimetype='application/json'
        )
    
    return Response(
        response=json.dumps({
            'target': webhooks[webhook_path]['target_url'],
            'created': webhooks[webhook_path]['created'],
            'requests_forwarded': webhooks[webhook_path]['requests']
        }),
        status=200,
        mimetype='application/json'
    )

@app.route('/delete/<webhook_id>', methods=['DELETE'])
def delete_webhook(webhook_id):
    webhook_path = 'w/' + webhook_id
    
    if webhook_path not in webhooks:
        return Response(
            response=json.dumps({'error': 'Webhook not found'}),
            status=404,
            mimetype='application/json'
        )
    
    del webhooks[webhook_path]
    
    return Response(
        response=json.dumps({'message': 'Webhook deleted'}),
        status=200,
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
