from abuse_types import ABUSE_TYPES, SEVERITY_LEVELS
import dspy
from dspy.evaluate import Evaluate
from typing import Literal, Optional
import os
import json
import pandas as pd
from dspy.teleprompt import MIPROv2
from datetime import datetime

# Global variable to store confusion matrix data
confusion_matrix_data = []


def configure_dspy():
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
        description="The severity of the abuse type in the message"
    )
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
    # Store data for confusion matrix
    global confusion_matrix_data
    confusion_matrix_data.append(
        {
            "message": example.message,
            "actual_abuse_type": example.abuse_type,
            "predicted_abuse_type": prediction.abuse_type,
            "actual_fraud_subtype": example.fraud_subtype,
            "predicted_fraud_subtype": prediction.fraud_subtype,
            "predicted_severity": prediction.severity,
            "predicted_confidence": prediction.confidence,
        }
    )

    # check that the abuse types and subtypes are valid
    if prediction.abuse_type not in abuse_types and prediction.abuse_type is not None:
        # print(f"❌ INVALID ABUSE TYPE: '{prediction.abuse_type}' not in {abuse_types}")
        return False

    if prediction.abuse_type == "fraud" and prediction.fraud_subtype not in fraud_subtypes:
        # print(f"❌ INVALID FRAUD SUBTYPE: '{prediction.fraud_subtype}' not in {fraud_subtypes}")
        return False

    # check that fraud has a subtype (matching the assert logic)
    if prediction.abuse_type == "fraud" and prediction.fraud_subtype is None:
        # print(f"❌ FRAUD TYPE MISSING SUBTYPE: abuse_type is 'fraud' but fraud_subtype is None")
        return False

    # check that the prediction matches the example
    if prediction.abuse_type != example.abuse_type:
        # print(f"❌ ABUSE TYPE MISMATCH: expected '{example.abuse_type}', got '{prediction.abuse_type}'")
        return False

    if prediction.abuse_type == "fraud" and prediction.fraud_subtype != example.fraud_subtype:
        # print(f"❌ FRAUD SUBTYPE MISMATCH: expected '{example.fraud_subtype}', got '{prediction.fraud_subtype}'")
        return False

    return True


def get_trainset():
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
    return trainset


def calculate_lm_cost():
    history = lm.history
    total_cost = 0
    for entry in history:
        total_cost += entry["cost"]
    print(f"Number of interactions: {len(history)}")
    print(f"Total cost: ${total_cost}")


def optimize_agent():
    trainset = get_trainset()
    agent = Agent()
    optimizer = MIPROv2(metric=validate_abuse_type, auto="medium")

    print(f"Optimizing program with MIPROv2...")
    optimized_program = optimizer.compile(agent, trainset=trainset)

    # Save optimized program for future use
    optimized_program.save("optimized_agent.json")

    calculate_lm_cost()


def load_optimized_agent():
    """Load the optimized agent from the saved JSON file."""
    configure_dspy()
    try:
        optimized_program = Agent()
        optimized_program.load("optimized_agent.json")
        print("✅ Loaded optimized agent from optimized_agent.json")
        return optimized_program
    except FileNotFoundError:
        print("❌ optimized_agent.json not found. Run optimize_agent() first.")
        return None
    except Exception as e:
        print(f"❌ Error loading optimized agent: {e}")
        return None


def evaluate_agent(optimized: bool = False):
    global confusion_matrix_data
    confusion_matrix_data = []  # Clear any previous data

    trainset = get_trainset()

    # Try to load optimized agent first, fallback to base agent
    if optimized:
        agent = load_optimized_agent()
        assert agent is not None, "Optimized agent not found"
        print("Using optimized agent for evaluation...")
        agent_type = "optimized"
    else:
        agent = Agent()
        print("Using base agent for evaluation...")
        agent_type = "base"

    evaluator = Evaluate(
        devset=trainset, num_threads=16, display_progress=True, return_outputs=True, return_all_scores=True
    )
    overall_score, result_triples, individual_scores = evaluator(agent, metric=validate_abuse_type)

    # Save confusion matrix data to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    confusion_df = pd.DataFrame(confusion_matrix_data)
    confusion_csv_path = f"logs/confusion_data_{agent_type}_{timestamp}.csv"
    confusion_df.to_csv(confusion_csv_path, index=False)
    print(f"✅ Saved confusion matrix data to {confusion_csv_path}")

    # save results to file
    with open(f"logs/evaluation_{agent_type}_{timestamp}.txt", "w") as f:
        f.write(f"Overall score: {overall_score}\n")
        f.write(f"Result triples: {result_triples}\n")
        f.write(f"Individual scores: {individual_scores}\n")

    # Clear the global data after saving
    confusion_matrix_data = []

    calculate_lm_cost()


def run_example_optimized():
    """Run examples with the optimized agent."""
    agent = load_optimized_agent()
    if agent is None:
        print("Cannot run examples - optimized agent not found.")
        return

    example_fraud_message = """🎁 FREE NITRO GIVEAWAY! 🎁
    Click here to claim your free Discord Nitro: https://discord.gift/fake123
    Limited time offer! Don't miss out!"""

    example_good_message = """Hey everyone! Just wanted to share that I'm hosting a study group for CS152 this weekend. Let me know if you'd like to join!"""

    print("=== OPTIMIZED AGENT RESULTS ===")
    print("\n--- Fraud Example ---")
    print(agent(example_fraud_message))

    print("\n--- Good Example ---")
    print(agent(example_good_message))

    calculate_lm_cost()


def run_example():
    example_fraud_message = """🎁 FREE NITRO GIVEAWAY! 🎁
    Click here to claim your free Discord Nitro: https://discord.gift/fake123
    Limited time offer! Don't miss out!"""

    example_good_message = """Hey everyone! Just wanted to share that I'm hosting a study group for CS152 this weekend. Let me know if you'd like to join!"""

    agent = Agent()

    print("=== BASE AGENT RESULTS ===")
    print("\n--- Fraud Example ---")
    print(agent(example_fraud_message))
    dspy.inspect_history()

    print("\n--- Good Example ---")
    print(agent(example_good_message))
    dspy.inspect_history()

    calculate_lm_cost()


def compare_agents():
    print("Evaluating optimized agent...")
    evaluate_agent(optimized=True)

    print("-" * 50)
    print("\n\n\n")

    print("Evaluating base agent...")
    evaluate_agent(optimized=False)


if __name__ == "__main__":
    # optimize_agent()          # Run optimization (takes time + money)
    configure_dspy()

    # compare_agents()

    # run_example()             # Test base agent on examples
    # run_example_optimized()   # Test optimized agent on examples
