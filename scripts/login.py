from google_auth_oauthlib.flow import InstalledAppFlow

# We are now requesting BOTH the base scope and the force-ssl scope
SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def login():
    flow = InstalledAppFlow.from_client_secrets_file('credentials/client_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    with open('credentials/token.json', 'w') as token:
        token.write(creds.to_json())
    print("[+] NEW token.json created successfully with FORCE-SSL!")

if __name__ == '__main__':
    login()