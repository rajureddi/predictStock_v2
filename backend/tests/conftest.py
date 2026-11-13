import os

# Existing API tests call routes directly. The live site keeps the login on.
os.environ.setdefault("MARKETMIND_AUTH", "0")
