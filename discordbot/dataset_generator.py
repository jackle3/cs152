from abuse_types import ABUSE_TYPES, SEVERITY_LEVELS
import dspy
from typing import Literal, Optional, List, Dict, Any
import os
import json
import csv
import random
from dataclasses import dataclass

# Set up the language model - using GPT-4 for better dataset generation
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    openai_token = tokens["openai"]

# Temperature controls randomness: 0.0 = deterministic, 1.0 = maximum creativity/diversity
lm = dspy.LM("openai/gpt-4o-mini", api_key=openai_token, temperature=0.8)
dspy.configure(lm=lm)

# Extract available types
abuse_types = list(ABUSE_TYPES.keys())
fraud_subtypes = list(ABUSE_TYPES["fraud"].subtypes.keys())


@dataclass
class DatasetExample:
    """Represents a single example in our dataset."""

    message: str
    abuse_type: Optional[str]
    fraud_subtype: Optional[str]


class MessageGenerator(dspy.Signature):
    """
    Generate realistic Discord messages for testing moderation systems.
    """

    # Inputs
    category: str = dspy.InputField(
        description="Category of message to generate (benign, fraud, spam, harassment, inappropriate, other)"
    )
    subtype: Optional[str] = dspy.InputField(
        description="Specific subtype if category is fraud", default=None
    )
    context: str = dspy.InputField(
        description="Discord server context (gaming, programming, general, etc.)", default="general"
    )
    style: str = dspy.InputField(description="Communication style for the message", default="casual")
    scenario: str = dspy.InputField(
        description="Specific scenario or situation for the message", default="general discussion"
    )

    # Outputs
    message: str = dspy.OutputField(
        description="A realistic Discord message that fits the category, style, and scenario"
    )


class DatasetGenerator(dspy.Module):
    """
    Generate a comprehensive dataset for testing Discord moderation.
    """

    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(MessageGenerator)

        # Define generation contexts for variety
        self.contexts = [
            "gaming",
            "programming",
            "crypto",
            "general",
            "memes",
            "art",
            "music",
            "study group",
            "trading",
            "tech support",
        ]

        # Define communication styles for prompt diversity
        self.styles = [
            "casual",
            "formal",
            "excited",
            "urgent",
            "questioning",
            "helpful",
            "frustrated",
            "friendly",
            "technical",
            "slang",
        ]

        # Define scenarios for each context to add more diversity
        self.scenarios = {
            "gaming": [
                "discussing strategy",
                "looking for teammates",
                "sharing achievements",
                "asking for help",
                "organizing tournament",
                "reviewing games",
                "streaming setup",
            ],
            "programming": [
                "debugging code",
                "sharing project",
                "asking for advice",
                "job discussion",
                "learning new language",
                "code review",
                "career help",
            ],
            "crypto": [
                "market discussion",
                "trading tips",
                "project analysis",
                "technical discussion",
                "price speculation",
                "news sharing",
                "investment advice",
            ],
            "general": [
                "casual chat",
                "sharing news",
                "asking questions",
                "making friends",
                "daily life",
                "entertainment",
                "random thoughts",
            ],
            "memes": [
                "sharing memes",
                "joking around",
                "reacting to content",
                "creating content",
                "discussing trends",
                "being silly",
                "pop culture",
            ],
            "art": [
                "sharing artwork",
                "asking for feedback",
                "discussing techniques",
                "finding inspiration",
                "commission work",
                "tool recommendations",
                "tutorials",
            ],
            "music": [
                "sharing songs",
                "discussing artists",
                "making playlists",
                "music production",
                "concert talk",
                "instrument help",
                "collaboration",
            ],
            "study group": [
                "homework help",
                "exam preparation",
                "sharing notes",
                "group project",
                "scheduling meetings",
                "academic discussion",
                "study tips",
            ],
            "trading": [
                "market analysis",
                "sharing trades",
                "investment discussion",
                "risk management",
                "learning trading",
                "platform help",
                "economic news",
            ],
            "tech support": [
                "troubleshooting",
                "setup help",
                "product recommendations",
                "error fixing",
                "software advice",
                "hardware issues",
                "tutorials",
            ],
        }

        # Define generation targets
        self.generation_targets = {
            "benign": 200,  # Clean messages
            "fraud": {
                "phishing": 30,
                "crypto_scam": 30,
                "fake_giveaway": 30,
                "account_theft": 20,
                "impersonation": 20,
                "fake_links": 30,
            },
            "spam": 50,
            "harassment": 40,
            "inappropriate": 40,
            "other": 30,
        }

    def generate_benign_messages(self, count: int) -> List[DatasetExample]:
        """Generate benign/clean messages."""
        examples = []

        for i in range(count):
            context = random.choice(self.contexts)
            style = random.choice(self.styles)
            scenario = random.choice(self.scenarios[context])

            # Generate message with varied prompts for diversity
            result = self.generator(category="benign", context=context, style=style, scenario=scenario)

            examples.append(DatasetExample(message=result.message, abuse_type=None, fraud_subtype=None))

            print(f"Generated benign message {i+1}/{count}")

        return examples

    def generate_fraud_messages(self, subtype_counts: Dict[str, int]) -> List[DatasetExample]:
        """Generate fraud messages with specific subtypes."""
        examples = []

        for subtype, count in subtype_counts.items():
            for i in range(count):
                context = random.choice(self.contexts)
                style = random.choice(self.styles)
                scenario = random.choice(self.scenarios[context])

                # Generate message with varied prompts for diversity
                result = self.generator(
                    category="fraud", subtype=subtype, context=context, style=style, scenario=scenario
                )

                examples.append(
                    DatasetExample(message=result.message, abuse_type="fraud", fraud_subtype=subtype)
                )

                print(f"Generated {subtype} message {i+1}/{count}")

        return examples

    def generate_other_abuse_messages(self, category: str, count: int) -> List[DatasetExample]:
        """Generate non-fraud abuse messages."""
        examples = []

        for i in range(count):
            context = random.choice(self.contexts)
            style = random.choice(self.styles)
            scenario = random.choice(self.scenarios[context])

            # Generate message with varied prompts for diversity
            result = self.generator(category=category, context=context, style=style, scenario=scenario)

            examples.append(DatasetExample(message=result.message, abuse_type=category, fraud_subtype=None))

            print(f"Generated {category} message {i+1}/{count}")

        return examples

    def generate_full_dataset(self) -> List[DatasetExample]:
        """Generate the complete dataset."""
        all_examples = []

        print("🤖 Starting dataset generation...")

        # Generate benign messages
        print("\n📝 Generating benign messages...")
        benign_examples = self.generate_benign_messages(self.generation_targets["benign"])
        all_examples.extend(benign_examples)

        # Generate fraud messages
        print("\n🚨 Generating fraud messages...")
        fraud_examples = self.generate_fraud_messages(self.generation_targets["fraud"])
        all_examples.extend(fraud_examples)

        # Generate other abuse types
        for abuse_type in ["spam", "harassment", "inappropriate", "other"]:
            print(f"\n⚠️ Generating {abuse_type} messages...")
            other_examples = self.generate_other_abuse_messages(
                abuse_type, self.generation_targets[abuse_type]
            )
            all_examples.extend(other_examples)

        # Shuffle the dataset
        random.shuffle(all_examples)

        print(f"\n✅ Dataset generation complete! Generated {len(all_examples)} examples.")
        return all_examples

    def save_dataset(self, examples: List[DatasetExample], filename: str = "discord_moderation_dataset.csv"):
        """Save the dataset to a CSV file."""
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["message", "abuse_type", "fraud_subtype"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for example in examples:
                writer.writerow(
                    {
                        "message": example.message,
                        "abuse_type": example.abuse_type,
                        "fraud_subtype": example.fraud_subtype,
                    }
                )

        print(f"💾 Dataset saved to {filename}")

    def print_dataset_stats(self, examples: List[DatasetExample]):
        """Print statistics about the generated dataset."""
        stats = {"total": len(examples), "benign": 0, "abuse_types": {}, "fraud_subtypes": {}}

        for example in examples:
            if example.abuse_type is None:
                stats["benign"] += 1
            else:
                if example.abuse_type not in stats["abuse_types"]:
                    stats["abuse_types"][example.abuse_type] = 0
                stats["abuse_types"][example.abuse_type] += 1

                if example.fraud_subtype:
                    if example.fraud_subtype not in stats["fraud_subtypes"]:
                        stats["fraud_subtypes"][example.fraud_subtype] = 0
                    stats["fraud_subtypes"][example.fraud_subtype] += 1

        print("\n📊 Dataset Statistics:")
        print(f"Total examples: {stats['total']}")
        print(f"Benign messages: {stats['benign']}")
        print("\nAbuse types:")
        for abuse_type, count in stats["abuse_types"].items():
            print(f"  {abuse_type}: {count}")
        print("\nFraud subtypes:")
        for fraud_subtype, count in stats["fraud_subtypes"].items():
            print(f"  {fraud_subtype}: {count}")


def main():
    """Main function to generate and save the dataset."""
    generator = DatasetGenerator()

    # Generate the dataset
    examples = generator.generate_full_dataset()

    # Print statistics
    generator.print_dataset_stats(examples)

    # Save to CSV
    generator.save_dataset(examples)

    # Also save a smaller test set
    test_examples = random.sample(examples, min(50, len(examples)))
    generator.save_dataset(test_examples, "discord_moderation_test_dataset.csv")

    print("\n🎉 Dataset generation completed successfully!")
    print("Files created:")
    print("  - discord_moderation_dataset.csv (full dataset)")
    print("  - discord_moderation_test_dataset.csv (50 example test set)")


if __name__ == "__main__":
    main()
