PHISHING = {
    "label": "Phishing",
    "description": "Attempts to steal personal information",
    "subtypes": {
        "title": "Select Phishing Type",
        "description": "What type of information is being sought?",
        "options": {
            "identifying_info": {
                "label": "Identifying Information",
                "description": "Seeking birthday, name, or other identifying information",
            },
            "location": {
                "label": "Location",
                "description": "Seeking location information",
            },
            "payment_info": {
                "label": "Payment Information",
                "description": "Seeking credit card or payment details",
            },
            "ssn": {
                "label": "Social Security Number",
                "description": "Seeking Social Security Number",
            },
        },
    },
}

INVESTMENT_SCAM = {
    "label": "Investment Scam",
    "description": "Fraudulent investment opportunities",
    "subtypes": {
        "title": "Select Investment Scam Type",
        "description": "What kind of investment scam is this?",
        "options": {
            "crypto": {
                "label": "Crypto",
                "description": "Cryptocurrency investment scam",
            },
            "counterfeit": {
                "label": "Counterfeit",
                "description": "Selling counterfeit items",
            },
            "other": {
                "label": "Other",
                "description": "Other investment scam type",
            },
        },
    },
}

ECOMMERCE = {
    "label": "E-Commerce Scam",
    "description": "Fake stores or counterfeit items",
    "subtypes": {
        "title": "Select E-Commerce Scam Type",
        "description": "What kind of e-commerce fraud is this?",
        "options": {
            "fake_store": {
                "label": "Fake Online Store",
                "description": "Fraudulent online store",
            },
            "counterfeit": {
                "label": "Counterfeit Items",
                "description": "Selling counterfeit items",
            },
        },
    },
}

ACCOUNT_TAKEOVER = {
    "label": "Account Takeover",
    "description": "Unauthorized account access",
    "subtypes": {
        "title": "Select Account Takeover Type",
        "description": "What kind of account takeover is this?",
        "options": {
            "unauthorized_login": {
                "label": "Unauthorized Login",
                "description": "Someone logged into my account without permission",
            },
            "unauthorized_message": {
                "label": "Unauthorized Message",
                "description": "Someone posted/messaged from my account",
            },
        },
    },
}

FRAUD_FLOW = {
    "phishing": PHISHING,
    "investment_scam": INVESTMENT_SCAM,
    "ecommerce": ECOMMERCE,
    "account_takeover": ACCOUNT_TAKEOVER,
}


def quote_message(message):
    """Truncate a message and place it inside a block quote"""
    message_content = message.content if message.content else "[No text content]"
    if len(message_content) > 1024:
        message_content = message_content[:1021] + "..."
    message_content = f">>> {message_content}"
    return message_content
