import os
import django
import sys

# Add the current directory to sys.path so we can import the plugin
sys.path.append(os.getcwd())

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

try:
    print("Attempting to import netbox_otnfaults.api.serializers...")
    from netbox_otnfaults.api import serializers
    print("Successfully imported netbox_otnfaults.api.serializers")
    print(f"OtnFaultSerializer: {serializers.OtnFaultSerializer}")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
