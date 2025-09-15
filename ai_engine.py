# Enhanced AI Models Class
class AIModels:
    def __init__(self):
        self.context = {}
        self.patterns = {
            "greeting": [r"hello|hi|hey", "Hello! How can I assist you today?"],
            "farewell": [r"bye|goodbye|see you", "Goodbye! Have a great day!"],
            "thanks": [r"thank|thanks|appreciate", "You're welcome! Happy to help!"],
            "weather": [r"weather|temperature|forecast", "I can help with weather information. Try the /api/weather endpoint."],
            "code": [r"code|program|function", "I can generate code in multiple languages. Use the /api/code/generate endpoint."]
        }
    
    def _match_pattern(self, prompt: str) -> Optional[str]:
        """Match patterns in the user input"""
        for pattern, response in self.patterns.values():
            if re.search(pattern, prompt.lower()):
                return response
        return None
    
    def _maintain_context(self, user_id: str, prompt: str, response: str):
        """Maintain conversation context"""
        if user_id not in self.context:
            self.context[user_id] = []
        
        # Keep last 5 exchanges
        self.context[user_id].append((prompt, response))
        if len(self.context[user_id]) > 5:
            self.context[user_id].pop(0)
    
    def llama_response(self, prompt: str, user_id: str = "default") -> str:
        pattern_response = self._match_pattern(prompt)
        if pattern_response:
            self._maintain_context(user_id, prompt, pattern_response)
            return pattern_response
        
        # Enhanced responses with context awareness
        context = self.context.get(user_id, [])
        responses = [
            f"Based on your previous questions, I think you might be interested in: {prompt}",
            f"Following up on our conversation: {prompt}",
            f"Llama analysis suggests: {prompt.capitalize()}",
            f"Considering your interests: {prompt}",
            f"Context-aware response: {prompt}"
        ]
        
        response = random.choice(responses)
        self._maintain_context(user_id, prompt, response)
        return response
    
    def mehwish_response(self, prompt: str, user_id: str = "default") -> str:
        pattern_response = self._match_pattern(prompt)
        if pattern_response:
            self._maintain_context(user_id, prompt, pattern_response)
            return pattern_response
        
        # Mehwish-specific enhanced responses
        responses = [
            f"Mehwish AI recommends: {prompt}",
            f"After deep analysis, Mehwish suggests: {prompt}",
            f"Mehwish's intelligent response: {prompt}",
            f"Based on advanced algorithms: {prompt}",
            f"Mehwish Pro analysis: {prompt}"
        ]
        
        response = random.choice(responses)
        self._maintain_context(user_id, prompt, response)
        return response
    
    def custom_response(self, prompt: str, user_id: str = "default") -> str:
        pattern_response = self._match_pattern(prompt)
        if pattern_response:
            self._maintain_context(user_id, prompt, pattern_response)
            return pattern_response
        
        # Custom model responses with personalization
        responses = [
            f"Custom model analysis: {prompt}",
            f"Personalized response: {prompt}",
            f"Based on your usage patterns: {prompt}",
            f"Custom AI recommendation: {prompt}",
            f"Tailored response: {prompt}"
        ]
        
        response = random.choice(responses)
        self._maintain_context(user_id, prompt, response)
        return response

# Enhanced Image Generator with actual image processing
class EnhancedImageGenerator:
    def generate_image(self, prompt: str, style: str = "cartoon"):
        try:
            # Create a more sophisticated image
            width, height = 400, 300
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                except:
                    font = ImageFont.load_default()
            
            # Add text with wrapping
            lines = self._wrap_text(prompt, font, width-20)
            y_text = 10
            for line in lines:
                draw.text((10, y_text), line, font=font, fill='black')
                y_text += 25
            
            # Apply style-based transformations
            if style == "cartoon":
                img = self._apply_cartoon_effect(img)
            elif style == "sketch":
                img = self._apply_sketch_effect(img)
            
            output_path = f"static/image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(output_path)
            
            return output_path
        except Exception as e:
            logger.error(f"Enhanced image generation error: {e}")
            return None
    
    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within specified width"""
        lines = []
        words = text.split()
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _apply_cartoon_effect(self, img):
        """Apply a cartoon effect to the image"""
        # Convert to numpy array for OpenCV processing
        cv_img = np.array(img.convert('RGB'))
        
        # Apply bilateral filter for cartoon effect
        filtered = cv2.bilateralFilter(cv_img, 9, 300, 300)
        
        # Convert back to PIL image
        return Image.fromarray(filtered)
    
    def _apply_sketch_effect(self, img):
        """Apply a sketch effect to the image"""
        # Convert to numpy array for OpenCV processing
        cv_img = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
        
        # Invert the grayscale image
        inverted = 255 - gray
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
        
        # Invert the blurred image
        inverted_blurred = 255 - blurred
        
        # Create sketch effect
        sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
        
        # Convert back to PIL image
        return Image.fromarray(sketch)

# Update the initialization with enhanced classes
ai_models = AIModels()
image_gen = EnhancedImageGenerator()

# Add user_id parameter to the AI chat endpoint
@app.post("/api/ai/chat")
async def ai_chat(request: AIRequest, user: dict = Depends(get_api_key)):
    try:
        track_api_usage(user["user_id"], "/api/ai/chat")
        
        if request.model == "llama":
            response = ai_models.llama_response(request.prompt, str(user["user_id"]))
        elif request.model == "mehwish":
            response = ai_models.mehwish_response(request.prompt, str(user["user_id"]))
        elif request.model == "custom":
            response = ai_models.custom_response(request.prompt, str(user["user_id"]))
        else:
            response = ai_models.llama_response(request.prompt, str(user["user_id"]))
        
        return {"response": response, "model": request.model, "language": request.language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))