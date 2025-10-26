"""
Quick test to verify OpenAI API connection
Run this to make sure your API key is working
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection"""

    print("="*60)
    print("Testing OpenAI API Connection")
    print("="*60)
    print()

    # Check if API key is set
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env file")
        print()
        print("Please make sure your .env file contains:")
        print("OPENAI_API_KEY=sk-proj-...")
        return False

    print(f"✓ API key found: {api_key[:20]}...{api_key[-10:]}")
    print()

    # Try to import openai
    try:
        import openai
        print("✓ OpenAI package installed")
    except ImportError:
        print("❌ OpenAI package not installed")
        print()
        print("Please run: pip install openai")
        return False

    print()
    print("Testing API connection...")
    print()

    # Try to make a simple API call
    try:
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use mini for cheaper test
            messages=[
                {
                    "role": "user",
                    "content": "Say 'OpenAI connection successful!' and nothing else."
                }
            ],
            max_tokens=20
        )

        result = response.choices[0].message.content
        print(f"✓ API Response: {result}")
        print()
        print("="*60)
        print("🎉 SUCCESS! OpenAI API is working correctly")
        print("="*60)
        print()
        print("Your system is ready to process invoices with AI!")
        print()
        return True

    except openai.AuthenticationError:
        print("❌ Authentication Error: Invalid API key")
        print()
        print("Please check your API key in the .env file")
        return False

    except openai.RateLimitError:
        print("❌ Rate Limit Error: Too many requests")
        print()
        print("Please wait a moment and try again")
        return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("Please check:")
        print("1. Your API key is valid")
        print("2. You have API credits available")
        print("3. Your internet connection is working")
        return False

if __name__ == "__main__":
    # Try to install python-dotenv if not available
    try:
        import dotenv
    except ImportError:
        print("Installing python-dotenv...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'python-dotenv'])
        from dotenv import load_dotenv
        load_dotenv()

    test_openai_connection()
    input("\nPress Enter to exit...")
