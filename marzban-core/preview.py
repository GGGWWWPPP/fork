from jinja2 import Template
import datetime
import os

with open('app/templates/subscription/index.html', 'r', encoding='utf-8') as f:
    template_content = f.read()

# Define dummy filters that Marzban uses
def bytesformat(value):
    return "12.5 GB"

def datetime_filter(value):
    return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

def now():
    return datetime.datetime.now()

from jinja2 import Environment

env = Environment()
env.filters['bytesformat'] = bytesformat
env.filters['datetime'] = datetime_filter
env.globals['now'] = now

template = env.from_string(template_content)

class DummyStatus:
    def __init__(self, val):
        self.value = val

class DummyResetStrategy:
    def __init__(self, val):
        self.value = val

# Dummy User Data
dummy_user = {
    'username': 'john_doe',
    'status': DummyStatus('active'),
    'data_limit': 50000000000,
    'used_traffic': 12500000000,
    'data_limit_reset_strategy': DummyResetStrategy('month'),
    'expire': datetime.datetime.now().timestamp() + (30 * 24 * 3600),
    'links': [
        'vless://dummy@example.com:443?type=tcp&security=tls#Node1'
    ]
}

rendered_html = template.render(user=dummy_user)

with open('preview.html', 'w', encoding='utf-8') as f:
    f.write(rendered_html)

print("Saved preview.html")
os.system("start preview.html")
