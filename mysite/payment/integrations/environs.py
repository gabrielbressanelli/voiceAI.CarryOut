import os
signing_secret = os.environ.get("DOORDASH_SIGNING_SECRET")
print(signing_secret)