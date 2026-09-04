import random
import string
from PIL import Image, ImageDraw, ImageFont
import io
import base64

class CaptchaGenerator:
    def __init__(self):
        self.width = 180
        self.height = 60
        
    def generate_captcha_text(self, length=6):
        """Generate random captcha text"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def create_captcha_image(self, text):
        """Create captcha image with text"""
        # Create image with white background
        image = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Add background noise
        for _ in range(100):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)))
        
        # Add lines
        for _ in range(5):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 150), random.randint(100, 150), random.randint(100, 150)), width=1)
        
        # Draw text
        try:
            # Try to load a TrueType font
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            try:
                # Try Linux font
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Calculate text position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        # Draw each character with slight variation
        for i, char in enumerate(text):
            char_x = x + (i * text_width // len(text))
            char_y = y + random.randint(-3, 3)
            color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
            draw.text((char_x, char_y), char, fill=color, font=font)
        
        return image
    
    def get_captcha_base64(self, text):
        """Convert captcha image to base64 string"""
        image = self.create_captcha_image(text)
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"
