from abuse_types import ABUSE_TYPES, SEVERITY_LEVELS
import dspy
from typing import Literal, Optional
import os
import json

# Set up the language model
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    openai_token = tokens["openai"]

lm = dspy.LM("openai/gpt-4o-mini", api_key=openai_token)
dspy.configure(lm=lm)

# ['fraud', 'spam', 'harassment', 'inappropriate', 'other']
abuse_types = list(ABUSE_TYPES.keys())

# ['phishing', 'crypto_scam', 'fake_giveaway', 'account_theft', 'impersonation', 'fake_links']
fraud_subtypes = list(ABUSE_TYPES["fraud"].subtypes.keys())

# ['low', 'medium', 'high', 'critical']
severity_levels = list(SEVERITY_LEVELS.keys())


class AgentReport(dspy.Signature):
    """
    Automatically report Discord messages that fall into our abuse types.
    """

    # Inputs
    message: str = dspy.InputField(description="The message to moderate")

    # Outputs
    abuse_type: Optional[Literal[*abuse_types]] = dspy.OutputField(description="The abuse type of the message")
    fraud_subtype: Optional[Literal[*fraud_subtypes]] = dspy.OutputField(
        description="The fraud subtype of the message, if the abuse type is fraud"
    )
    severity: Literal[*severity_levels] = dspy.OutputField(
        description="The severity that the message performs the abuse type at"
    )
    reason: str = dspy.OutputField(
        description="Additional information and your reasoning for the report"
    )
    confidence: float = dspy.OutputField(
        description="The confidence in the report"
    )


class Agent(dspy.Module):
    """
    Automatically report Discord messages that fall into our abuse types.
    """

    def __init__(self):
        super().__init__()
        self.response = dspy.ChainOfThought(AgentReport)

    def report(self, message: str):
        return self.response(message=message)
    
example_fraud_message = """🎁 FREE NITRO GIVEAWAY! 🎁
Click here to claim your free Discord Nitro: https://discord.gift/fake123
Limited time offer! Don't miss out!"""

example_good_message = """Hey everyone! Just wanted to share that I'm hosting a study group for CS152 this weekend. Let me know if you'd like to join!"""

agent = Agent()

print(agent.report(example_fraud_message))
print(agent.report(example_good_message))