import asyncio
import getpass
from twscrape import API
from twscrape.logger import set_log_level

async def add_account(username: str):
    api = API()
    set_log_level("INFO")
    
    print("\nAdd Twitter account to TwScrape")
    print("--------------------------------")
    print(f"Username: {username}")
    
    try:
        # Get passwords securely using getpass
        password = getpass.getpass("Twitter password: ")
        email = getpass.getpass("Email address associated with Twitter account: ")
        email_password = getpass.getpass("Email password: ")
        
        print("\nAttempting to add account...")
        try:
            await api.pool.add_account(
                username=username,
                password=password,
                email=email,
                email_password=email_password
            )
            print("\nAccount added successfully!")
        except Exception as e:
            if "already exists" in str(e):
                print("This account is already configured in TwScrape.")
            else:
                print(f"\nError adding account: {e}")
                if "password" in str(e).lower():
                    print("Password seems to be incorrect. Please try again.")
                elif "email" in str(e).lower():
                    print("Email or email password seems to be incorrect. Please try again.")
                else:
                    print("An unexpected error occurred. Please check your credentials and try again.")
        
        # Attempt to list accounts
        try:
            accounts = await api.pool.accounts()
            print(f"\nTotal accounts configured: {len(accounts)}")
        except Exception as e:
            print("\nCould not retrieve accounts. Please check your account configuration.")
            print(f"Error: {e}")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Twitter username: ")
    
    asyncio.run(add_account(username))
