#!/usr/bin/env python3
"""Test captcha generation"""

from captcha_generator import CaptchaGenerator

# Test captcha generation
gen = CaptchaGenerator()

# Generate captcha text
text = gen.generate_captcha_text()
print(f"Generated captcha text: {text}")
print(f"Text length: {len(text)}")
print(f"Text type: {type(text)}")

# Generate captcha image
try:
    image_base64 = gen.get_captcha_base64(text)
    print(f"Image generated successfully")
    print(f"Image data length: {len(image_base64)}")
    print(f"Image starts with: {image_base64[:50]}")
except Exception as e:
    print(f"Error generating image: {e}")
    import traceback
    traceback.print_exc()
