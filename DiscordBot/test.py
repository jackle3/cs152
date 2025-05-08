from enum import Enum

class FraudType(Enum):
    PHISHING = ("Phishing", "Attempts to steal personal information")
    INVESTMENT_SCAM = ("Investment Scam", "Fraudulent investment opportunities")
    ECOMMERCE = ("E-Commerce Scam", "Fake stores or counterfeit items")
    ACCOUNT_TAKEOVER = ("Account Takeover", "Unauthorized account access")
    
    
for option in FraudType:
    print(option.value)
    print(option.name)

print(FraudType['PHISHING'])
    
