import asyncio
import getpass
from twscrape import API
from twscrape.logger import set_log_level

async def add_account(username: str, password: str, email: str, email_password: str):
    api = API()
    set_log_level("INFO")
    
    print(f"Adding account for username: {username}")
    try:
        await api.pool.add_account(
            username=username,
            password=password,
            email=email,
            email_password=email_password
        )
        print(f"Account {username} added successfully!")
        
        # Log the current state of the accounts pool
        try:
            accounts = await api.pool.accounts()  # Attempt to retrieve accounts
            print(f"Current accounts in pool: {[account.username for account in accounts]}")
        except Exception as e:
            print("\nCould not retrieve accounts. Please check your account configuration.")
            print(f"Error: {e}")
            print("This may indicate that the accounts pool is not functioning as expected.")
            print("Please ensure that TwScrape is configured correctly.")
        
    except Exception as e:
        print(f"Error adding account {username}: {e}")
        if "already exists" in str(e):
            print("This account is already configured in TwScrape.")
        elif "password" in str(e).lower():
            print("Password seems to be incorrect. Please try again.")
        elif "email" in str(e).lower():
            print("Email or email password seems to be incorrect. Please try again.")
        else:
            print("An unexpected error occurred. Please check your credentials and try again.")
            print(f"Full error message: {str(e)}")

async def add_accounts_from_file(file_path: str):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            username, password, email, email_password = line.strip().split(',')
            await add_account(username, password, email, email_password)

if __name__ == "__main__":
    file_path = "credentials.txt"
    asyncio.run(add_accounts_from_file(file_path))
