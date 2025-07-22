#!/usr/bin/env python3
import os
import sys

# Simple API test without Unicode issues
def main():
    print("Gemini API Connection Test")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found")
        print("Please set environment variable:")
        print("set GEMINI_API_KEY=your-api-key-here")
        return False
    
    print(f"API Key found: {api_key[:10]}...")
    
    # Test import
    try:
        import google.generativeai as genai
        print("SUCCESS: google-generativeai imported")
    except ImportError as e:
        print(f"ERROR: Cannot import google-generativeai: {e}")
        return False
    
    # Test configuration
    try:
        genai.configure(api_key=api_key)
        print("SUCCESS: Gemini configured")
    except Exception as e:
        print(f"ERROR: Configuration failed: {e}")
        return False
    
    # Test simple text generation
    try:
        print("Testing text generation...")
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content("Say 'Hello World'")
        
        if response.text:
            print(f"SUCCESS: Generated text: {response.text.strip()}")
            return True
        else:
            print("ERROR: Empty response")
            return False
            
    except Exception as e:
        print(f"ERROR: Text generation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nAll tests PASSED!")
    else:
        print("\nSome tests FAILED!")
        sys.exit(1)