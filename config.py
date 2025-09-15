# Mehwish Chat API 5.5 Configuration
# Created by Syed Kawish Ali - kawish.alisas@gmail.com
# GitHub: https://github.com/kawish304/

API_CONFIG = {
    "version": "5.5",
    "name": "Mehwish Chat API",
    "creator": "Syed Kawish Ali",
    "email": "kawish.alisas@gmail.com",
    "github": "https://github.com/kawish304/",
    "languages": ["rom-ur", "en", "ar", "es", "fr", "de", "zh", "hi", "ru"],
    "default_language": "rom-ur",
    "rate_limits": {
        "free": {"requests": 100, "period": "day"},
        "basic": {"requests": 1000, "period": "day", "price": "$10/month"},
        "pro": {"requests": 10000, "period": "day", "concurrent": 10, "price": "$50/month"},
        "enterprise": {"requests": "unlimited", "concurrent": 50, "price": "custom"}
    },
    "modules": {
        "ai_models": ["llama", "dr_ai_medical", "stability_ai", "advanced_models", "gaming_ai"],
        "ecommerce": ["amazon", "aliexpress", "ebay", "alibaba", "daraz"],
        "social_media": ["whatsapp", "facebook", "youtube", "twitter", "instagram", "tiktok", "linkedin"],
        "education": ["quran_hadith", "science", "math", "history", "space", "physics", "chemistry", "biology"],
        "technology": ["coding", "ethical_hacking", "mobile_apps", "web_dev", "software", "cli", "screen_sharing"],
        "business": ["seo", "freelancing", "real_estate", "banking", "ecommerce", "economy", "stats"],
        "utilities": ["weather", "calendar", "currency", "translation", "voice", "telecom", "maps", "entertainment"],
        "special": ["nadra_like", "legal", "government", "healthcare", "energy", "transportation"]
    },
    "legal": {
        "terms": "https://mehwish.chat/terms",
        "privacy": "https://mehwish.chat/privacy",
        "disclaimer": "This API is for educational and legitimate purposes only. Illegal activities are strictly prohibited."
    }
}