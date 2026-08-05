import os
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, Response, render_template_string
import requests

app = Flask(__name__)

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
webhooks = {}

# ------------------ Frontend (HTML) ------------------
HTML = """
<!DOCTYPE html>
<html>
<head><title>distraction on the beat ho</title></head>
<body style="display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f0f0;">
<div style="background:white;padding:2rem;border-radius:8px;width:480px;max-width:94%;box-shadow:0 2px 12px rgba(0,0,0,0.15);">
<h2 style="margin-top:0;">Protect your webhook</h2>
<input id="targetInput" type="text" placeholder="change me to your webhook" style="width:100%;padding:0.6rem;margin:0.5rem 0;box-sizing:border-box;font-size:1rem;border:1px solid #ccc;border-radius:4px;">
<button id="createBtn" style="width:100%;padding:0.6rem;background:#007bff;color:white;border:none;border-radius:4px;font-size:1rem;cursor:pointer;">Create</button>
<div id="resultArea" style="margin-top:1rem;display:none;background:#e9ecef;padding:0.5rem 0.8rem;border-radius:4px;display:flex;justify-content:space-between;align-items:center;word-break:break-all;">
<span id="protectedUrl" style="flex:1;"></span>
<button id="copyBtn" style="background:#28a745;color:white;border:none;border-radius:4px;padding:0.3rem 0.9rem;cursor:pointer;font-size:0.9rem;margin-left:0.5rem;">Copy</button>
</div>
<div id="status" style="margin-top:0.6rem;color:#666;"></div>
<div id="errorMsg" style="margin-top:0.4rem;color:#dc3545;"></div>
</div>
<script>
const targetInput = document.getElementById('targetInput');
const createBtn = document.getElementById('createBtn');
const resultArea = document.getElementById('resultArea');
const protectedUrl = document.getElementById('protectedUrl');
const copyBtn = document.getElementById('copyBtn');
const status = document.getElementById('status');
const errorMsg = document.getElementById('errorMsg');

createBtn.addEventListener('click', async () => {
    const target = targetInput.value.trim();
    errorMsg.textContent = '';
    status.textContent = 'Creating...';
    resultArea.style.display = 'none';

    if (!target) {
        errorMsg.textContent = 'Please enter a target URL.';
        status.textContent = '';
        return;
    }

    try {
        const res = await fetch('/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_url: target })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Server error');
        protectedUrl.textContent = data.protected_url;
        resultArea.style.display = 'flex';
        status.textContent = '';
    } catch (err) {
        errorMsg.textContent = 'Error: ' + err.message;
        status.textContent = '';
    }
});

copyBtn.addEventListener('click', () => {
    const url = protectedUrl.textContent;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => alert('Copied!')).catch(() => fallbackCopy(url));
    } else {
        fallbackCopy(url);
    }
});

function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    alert('Copied!');
}
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

# ------------------ API endpoints ------------------
@app.route('/create', methods=['POST'])
def create_webhook():
    data = request.get_json()
    if not data or 'target_url' not in data:
        return jsonify({'error': 'target_url is required'}), 400

    target = data['target_url']
    webhook_id = secrets.token_urlsafe(16)
    created = datetime.utcnow().isoformat()
    webhooks[webhook_id] = {'target_url': target, 'created': created}

    return jsonify({
        'protected_url': f"{BASE_URL}/w/{webhook_id}",
        'target': target,
        'created': created,
        'id': webhook_id
    }), 201

@app.route('/w/<webhook_id>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def proxy(webhook_id):
    if webhook_id not in webhooks:
        return jsonify({'error': 'Webhook not found'}), 404

    if request.method == 'DELETE':
        return jsonify({'error': 'DELETE requests are not allowed'}), 403

    target = webhooks[webhook_id]['target_url']
    headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}

    try:
        resp = requests.request(
            method=request.method,
            url=target,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            allow_redirects=False
        )
        return Response(resp.content, status=resp.status_code, headers=dict(resp.headers))
    except Exception:
        return jsonify({'error': 'Failed to forward request'}), 502

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
