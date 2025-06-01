from abuse_types import ABUSE_TYPES, SEVERITY_LEVELS
import dspy
from dspy.evaluate import Evaluate
from typing import Literal, Optional
import os
import json
import pandas as pd

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

# ['fraud', 'spam', 'harassment', 'inappropriate']
abuse_types = list(set(ABUSE_TYPES.keys()) - {"other"})

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
    abuse_type: Optional[Literal[*abuse_types]] = dspy.OutputField(
        description="The abuse type of the message"
    )
    fraud_subtype: Optional[Literal[*fraud_subtypes]] = dspy.OutputField(
        description="The fraud subtype of the message, if the abuse type is fraud"
    )
    severity: Literal[*severity_levels] = dspy.OutputField(
        description="The severity that the message performs the abuse type at"
    )
    reason: str = dspy.OutputField(description="Additional information and your reasoning for the report")
    confidence: float = dspy.OutputField(description="The confidence in the report")


class Agent(dspy.Module):
    """
    Automatically report Discord messages that fall into our abuse types.
    """

    def __init__(self):
        super().__init__()
        self.response = dspy.ChainOfThought(AgentReport)

    def forward(self, message: str):
        return self.response(message=message)


def validate_abuse_type(example, prediction, trace=None):
    # check that the abuse types and subtypes are valid
    if prediction.abuse_type not in abuse_types and prediction.abuse_type is not None:
        print(f"❌ INVALID ABUSE TYPE: '{prediction.abuse_type}' not in {abuse_types}")
        return False

    if prediction.abuse_type == "fraud" and prediction.fraud_subtype not in fraud_subtypes:
        print(f"❌ INVALID FRAUD SUBTYPE: '{prediction.fraud_subtype}' not in {fraud_subtypes}")
        return False

    # check that fraud has a subtype (matching the assert logic)
    if prediction.abuse_type == "fraud" and prediction.fraud_subtype is None:
        print(f"❌ FRAUD TYPE MISSING SUBTYPE: abuse_type is 'fraud' but fraud_subtype is None")
        return False

    # check that the prediction matches the example
    if prediction.abuse_type != example.abuse_type:
        print(f"❌ ABUSE TYPE MISMATCH: expected '{example.abuse_type}', got '{prediction.abuse_type}'")
        return False

    if prediction.abuse_type == "fraud" and prediction.fraud_subtype != example.fraud_subtype:
        print(
            f"❌ FRAUD SUBTYPE MISMATCH: expected '{example.fraud_subtype}', got '{prediction.fraud_subtype}'"
        )
        return False

    return True


def evaluate_agent():
    df = pd.read_csv("discord_moderation_train_dataset.csv")
    trainset = []
    for _, row in df.iterrows():
        message = row["message"]
        abuse_type = row["abuse_type"]
        fraud_subtype = row["fraud_subtype"]

        # convert nan to None
        abuse_type = None if pd.isna(abuse_type) else abuse_type
        fraud_subtype = None if pd.isna(fraud_subtype) else fraud_subtype

        if abuse_type is not None and abuse_type not in abuse_types:
            assert False, f"Bad abuse type: {abuse_type}"

        if fraud_subtype is not None and fraud_subtype not in fraud_subtypes:
            assert False, f"Bad fraud subtype: {fraud_subtype}"

        if abuse_type == "fraud" and fraud_subtype is None:
            assert False, f"Bad fraud type: {abuse_type} and {fraud_subtype}"

        example = dspy.Example(
            message=message, abuse_type=abuse_type, fraud_subtype=fraud_subtype
        ).with_inputs("message")

        trainset.append(example)

    agent = Agent()

    evaluator = Evaluate(devset=trainset, num_threads=6, display_progress=True, display_table=5)
    evaluator(agent, metric=validate_abuse_type)


def run_example():
    example_fraud_message = """🎁 FREE NITRO GIVEAWAY! 🎁
    Click here to claim your free Discord Nitro: https://discord.gift/fake123
    Limited time offer! Don't miss out!"""

    example_good_message = """Hey everyone! Just wanted to share that I'm hosting a study group for CS152 this weekend. Let me know if you'd like to join!"""

    agent = Agent()

    print(agent(example_fraud_message))
    print(dspy.inspect_history())

    print(agent(example_good_message))
    print(dspy.inspect_history())


if __name__ == "__main__":
    evaluate_agent()
    # run_example()
