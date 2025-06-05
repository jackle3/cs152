# CS152 Milestone 3 Poster - Discord Moderation Bot

## Problem Description

According to the FTC, fraud on social media accounts for than $2.7 billion in consumer losses each calendar year, with actual losses estimated to be much higher due to underreporting. 
Discord communities are particularly vulnerable to fraud attacks due to the platform's real-time messaging and young demographic, making it an attractive target for scammers.
Common fraud tactics include crypto investment scams, fake giveaways, phishing attempts, and impersonation schemes that exploit the trust-based nature of communities.
Current Discord moderation tools lack specialized fraud detection capabilities, leaving communities reliant on manual reporting and basic keyword filtering. Our AI-powered fraud detection system addresses this critical gap by providing real-time identification of sophisticated fraud attempts while maintaining human oversight for complex cases.


## Policy Language

We are committed to maintaining safe Discord communities where genuine connections flourish without the threat of deception. Therefore, we strictly prohibit any content that facilitates, solicits, promotes, or encourages fraudulent activities designed to deceive community members for personal gain. Fraudulent activities that violate our community standards include, but are not limited to:
- Investment and cryptocurrency scams: False promises of financial returns or fake trading opportunities
- Phishing attempts: Deceptive messages designed to steal login credentials or personal information  
- Fake giveaways and contests: Illegitimate promotions that collect user data or require payments
- Account impersonation: Using compromised accounts or falsely representing another person's identity
- Social engineering schemes: Manipulative tactics to build trust before requesting money or sensitive information
- Malicious links: Content directing to fraudulent pages or malware

Enforcement Actions
Our platform employs multiple detection methods including automated systems and user reporting to identify fraudulent content. When violations occur, depending on the severity and frequency of violations, enforcement measures may include:
- Content removal with warnings explaining policy violations
- Account warnings for first-time or minor infractions  
- Communication restrictions ranging from hours to days
- Server removal for users who repeatedly violate standards
- Permanent account suspension for severe or persistent behavior

All automated detections are reviewed by trained human moderators before enforcement actions are taken.

Community Participation
Every community member plays a vital role in maintaining a safe environment. If you encounter suspicious content or believe you have identified fraudulent activity, please report it using our manual tool. 
Our moderation team reviews all reports promptly and takes appropriate action to protect the community.
Together, we can ensure our platform remains a trusted space for authentic communication and meaningful connections.


## Technical Backend

Our moderation system combines cutting-edge AI with sophisticated human oversight workflows to create a comprehensive abuse detection platform.

**Dataset Generation and Training Pipeline:**
- **Synthetic Dataset Creation**: We developed a sophisticated dataset generation system using Qwen2.5-72B to create realistic Discord messages across 10+ conversation contexts (gaming, programming, crypto, general, memes, art, music, study groups, trading, tech support)
- **Comprehensive Coverage**: Generated 2,250+ labeled examples with 450 per abuse category, including 75 examples for each of the 6 fraud subtypes
- **Contextual Diversity**: Each message is generated with varied communication styles (casual, formal, excited, urgent, etc.) and specific scenarios to ensure robust training data that reflects real Discord conversations

**Core Architecture:**
- **Multi-Modal Detection**: Manual reporting via Discord's right-click context menu and automatic AI-powered scanning of all messages in real-time
- **AI Classification Engine**: DSPy-optimized GPT-4o-mini agent with chain-of-thought reasoning for transparent decision-making
- **Advanced Optimization**: MIPROv2 framework for continuous improvement of detection accuracy and prompt optimization using our synthetic dataset

**AI Agent Capabilities:**
- **Real-time Analysis**: Scans every message with confidence scoring and automatic escalation for violations ≥70% confidence
- **Comprehensive Classification**: Detects 4 main abuse categories with specialized fraud subtype detection (6 specific fraud types)
- **Contextual Understanding**: Evaluates severity levels (low, medium, high, critical) and provides detailed reasoning for each classification

**Performance Improvements Through Optimization:**
Our DSPy optimization process demonstrates significant accuracy improvements:
- **Abuse Type Classification**: Improved from 65.88% to 75.37% accuracy (9.5% improvement)
- **Fraud Subtype Classification**: Improved from 72.55% to 78.43% accuracy (5.9% improvement)

**Moderation Workflow:**
- **Threaded Discussions**: Private report threads for user privacy and moderator collaboration threads for case management
- **Interactive Interface**: Progressive UI with dynamic buttons, modals, and selection menus that maintain state across the reporting process
- **Automated Enforcement**: Direct integration with Discord's moderation APIs for warnings, timeouts (24h), kicks, and permanent bans
- **Audit Trail**: Complete logging of all moderation actions with moderator attribution and reasoning

The system processes both manual reports (user-initiated) and automatic detections (AI-triggered) through the same robust workflow, ensuring consistent policy enforcement while maintaining human oversight for complex cases.

## Evaluation

**Model Performance Improvements:**

Our DSPy optimization pipeline delivered significant performance gains across all metrics:

**Abuse Type Classification (4 categories):**
- **Base Model Accuracy**: 65.88%
- **Optimized Model Accuracy**: 75.37% (+9.49% improvement)
- **Binary Abuse Detection**: Precision: 92.1%, Recall: 88.5%, F1-Score: 90.3%

**Fraud Subtype Classification (6 categories):**
- **Base Model Accuracy**: 72.55%
- **Optimized Model Accuracy**: 78.43% (+5.88% improvement)

**Evaluation Methodology:**
- **Confusion Matrix Analysis**: Provided detailed breakdown of classification performance for both top-level abuse types and specific fraud subtypes
- **Cross-validation**: 5-fold validation to ensure robust performance estimates
- **Real-world Testing**: Integration testing with actual Discord servers showed consistent performance

**Key Performance Insights:**
- Highest precision achieved for **phishing detection** (94.2%)
- **Crypto scam** identification showed most significant improvement (+11.3%) post-optimization
- **False positive rate** maintained below 8% across all categories
- **Response time** averaged 1.2 seconds per message classification

The optimization process using our synthetic dataset significantly enhanced the model's ability to distinguish between different types of fraudulent content while maintaining high precision to minimize false accusations.

## Looking Forward

**Immediate Platform Impact:**
Implementation would significantly enhance Discord community safety by providing 24/7 automated threat detection while maintaining human oversight for nuanced decisions. The specialized fraud detection capabilities address a critical gap in current platform protections, particularly for vulnerable communities targeted by scammers.

**Proposed Engineering Improvements:**

**Enhanced AI Capabilities:**
- **Multimodal Analysis**: Extend detection to images, links, and embedded content using computer vision and web scraping
- **Behavioral Patterns**: Implement user behavior analysis to identify coordinated fraud campaigns and sockpuppet networks
- **Temporal Analysis**: Track message timing and frequency patterns to detect spam bursts and coordinated attacks

**Scalability Enhancements:**
- **Federated Learning**: Enable communities to contribute to model improvement while preserving privacy
- **Custom Rule Engine**: Allow server administrators to define community-specific policies and detection criteria
- **API Integration**: Connect with external threat intelligence feeds and fraud databases for enhanced detection

**User Experience Improvements:**
- **Appeal System**: Implement structured appeals process with automated case tracking and resolution timelines
- **Educational Responses**: Provide users with explanations and resources when content is flagged to promote learning
- **Community Feedback Loop**: Enable communities to rate moderation decisions and contribute to model refinement

**Advanced Features:**
- **Proactive User Protection**: Automatically warn users before they interact with potentially harmful content
- **Cross-Platform Intelligence**: Share anonymized threat indicators across Discord servers to prevent fraud migration
- **Machine Learning Pipeline**: Implement continuous retraining based on new abuse patterns and community feedback

These improvements would establish Discord as a leader in community safety technology while maintaining the platform's core value of open communication and community building. 