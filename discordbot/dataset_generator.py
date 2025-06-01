from abuse_types import ABUSE_TYPES, SEVERITY_LEVELS
import dspy
from typing import Literal, Optional, List, Dict, Any
import os
import json
import csv
import random
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up the language model - using GPT-4 for better dataset generation
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    openai_token = tokens["openai"]
    qwen_token = tokens["qwen"]

# Temperature controls randomness: 0.0 = deterministic, 1.0 = maximum creativity/diversity

model = "openai/qwen2.5-72b-instruct"
api_base = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
api_key = qwen_token

lm = dspy.LM(model=model, api_base=api_base, api_key=qwen_token, temperature=0.8)
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


def write_to_file(dataset_example: DatasetExample):
    message = dataset_example.message
    abuse_type = dataset_example.abuse_type
    fraud_subtype = dataset_example.fraud_subtype

    with open(f"logs/datagen_{abuse_type}.txt", "a") as f:
        f.write(f"{f'{fraud_subtype}: ' if fraud_subtype else ''}{message}\n")


class MessageGenerator(dspy.Signature):
    """
    Generate realistic Discord messages for testing moderation systems.
    """

    # Inputs
    category: str = dspy.InputField(
        description="Category of message to generate (benign, fraud, spam, harassment, inappropriate)"
    )
    subtype: Optional[str] = dspy.InputField(
        description="Specific fraud subtype, if the category is fraud", default=None
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
        }

    def generate_benign_messages(self, count: int) -> List[DatasetExample]:
        """Generate benign/clean messages."""
        examples = []

        for i in range(count):
            context = random.choice(self.contexts)
            style = random.choice(self.styles)
            scenario = random.choice(self.scenarios[context])

            # Generate message with varied prompts for diversity
            result = self.generator(
                category="benign", subtype=None, context=context, style=style, scenario=scenario
            )

            example = DatasetExample(message=result.message, abuse_type=None, fraud_subtype=None)
            examples.append(example)
            write_to_file(example)

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

                example = DatasetExample(message=result.message, abuse_type="fraud", fraud_subtype=subtype)
                examples.append(example)
                write_to_file(example)

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
            result = self.generator(
                category=category, subtype=None, context=context, style=style, scenario=scenario
            )

            example = DatasetExample(message=result.message, abuse_type=category, fraud_subtype=None)
            examples.append(example)
            write_to_file(example)

            print(f"Generated {category} message {i+1}/{count}")

        return examples

    def generate_full_dataset(self) -> List[DatasetExample]:
        """Generate the complete dataset with parallel execution."""
        all_examples = []

        print("🤖 Starting dataset generation with parallel execution...")

        # Prepare all generation tasks
        tasks = []

        with ThreadPoolExecutor(max_workers=6) as executor:
            # Submit benign message generation
            print("\n📝 Starting benign message generation...")
            future_benign = executor.submit(self.generate_benign_messages, self.generation_targets["benign"])
            tasks.append(("benign", future_benign))

            # Submit fraud message generation
            print("\n🚨 Starting fraud message generation...")
            future_fraud = executor.submit(self.generate_fraud_messages, self.generation_targets["fraud"])
            tasks.append(("fraud", future_fraud))

            # Submit other abuse type generations
            for abuse_type in ["spam", "harassment", "inappropriate"]:
                print(f"\n⚠️ Starting {abuse_type} message generation...")
                future_abuse = executor.submit(
                    self.generate_other_abuse_messages, abuse_type, self.generation_targets[abuse_type]
                )
                tasks.append((abuse_type, future_abuse))

            # Collect results as they complete
            for task_name, future in tasks:
                try:
                    examples = future.result()
                    all_examples.extend(examples)
                    print(f"✅ Completed {task_name} generation: {len(examples)} examples")
                except Exception as e:
                    print(f"❌ Error in {task_name} generation: {e}")

        # Shuffle the dataset
        random.shuffle(all_examples)

        print(f"\n✅ Dataset generation complete! Generated {len(all_examples)} examples.")
        return all_examples

    def save_dataset(self, examples: List[DatasetExample], filename: str):
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

    # Split into train and test sets first
    test_size = int(0.15 * len(examples))
    test_indices = random.sample(range(len(examples)), test_size)
    test_examples = [examples[i] for i in test_indices]
    train_examples = [examples[i] for i in range(len(examples)) if i not in test_indices]

    # Save train set
    generator.save_dataset(train_examples, "discord_moderation_train_dataset.csv")

    # Save test set
    generator.save_dataset(test_examples, "discord_moderation_test_dataset.csv")

    print("\n🎉 Dataset generation completed successfully!")
    print("Files created:")
    print("  - discord_moderation_train_dataset.csv (train dataset)")
    print("  - discord_moderation_test_dataset.csv (50 example test set)")


if __name__ == "__main__":
    main()
