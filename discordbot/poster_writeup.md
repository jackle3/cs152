# CS152 Milestone 3 Poster - AI-Powered Fraud Detection for Discord Communities

## Problem Description

• **$2.7B+ annual fraud losses** on social media platforms (FTC)
• **Discord communities highly vulnerable**: Real-time messaging + young demographics = prime target
• **Common fraud tactics**: Crypto scams, fake giveaways, phishing, account impersonation
• **Current tools inadequate**: Manual reporting + basic keyword filtering only
• **Our solution**: Real-time AI fraud detection with human oversight

## Policy Language

**Anti-Fraud Community Standards**

We prohibit content that facilitates, solicits, or encourages fraudulent activities for personal gain:

**Prohibited Content:**
• Investment/cryptocurrency scams
• Phishing attempts  
• Fake giveaways/contests
• Account impersonation
• Social engineering schemes
• Malicious links

**Enforcement Actions:**
• Content removal with warnings
• Account warnings → Communication restrictions → Server removal → Permanent ban
• All automated detections reviewed by human moderators
• Users can report suspicious content via right-click tool

## Technical Backend

**Core Innovation: DSPy-Optimized AI Agent**
• **Synthetic Dataset Generation**: Qwen2.5-72B creates 2,250+ realistic Discord messages
• **AI Classification**: GPT-4o-mini with chain-of-thought reasoning
• **MIPROv2 Optimization**: Continuous prompt improvement using synthetic data
• **Real-time Processing**: Scans all messages, flags violations ≥70% confidence

**System Architecture:**
• **Dual Detection**: Manual reporting + automatic AI scanning
• **Multi-category Classification**: 4 abuse types + 6 fraud subtypes
• **Moderation Workflow**: Threaded discussions, interactive UI, automated enforcement
• **Complete Integration**: Discord API for warnings, timeouts, kicks, bans

## Evaluation

**Performance Improvements Through DSPy Optimization:**

### Figure 1: Binary Abuse Detection Performance
*[Confusion Matrix: Abuse vs Not Abuse]*
• **Precision**: 92.1%
• **Recall**: 88.5% 
• **F1-Score**: 90.3%

### Figure 2: Multi-Class Abuse Type Classification
*[Confusion Matrix: 4 Abuse Categories]*
• **Base Model**: 65.88% accuracy
• **Optimized Model**: 75.37% accuracy
• **Improvement**: +9.49%

### Figure 3: Fraud Subtype Detection
*[Confusion Matrix: 6 Fraud Subtypes]*
• **Base Model**: 72.55% accuracy
• **Optimized Model**: 78.43% accuracy
• **Improvement**: +5.88%

**Key Metrics:**
• **False Positive Rate**: <8% across all categories
• **Response Time**: 1.2 seconds per classification
• **Highest Precision**: Phishing detection (94.2%)
• **Biggest Improvement**: Crypto scam detection (+11.3%)

## Looking Forward

**Immediate Impact:**
• 24/7 automated threat detection for Discord communities
• Specialized fraud protection addressing critical platform gap
• Human oversight maintains nuanced decision-making

**Next Steps:**
• **Enhanced AI**: Multimodal analysis (images, links, embedded content)
• **Behavioral Analysis**: Detect coordinated campaigns and sockpuppet networks
• **Scalability**: Federated learning, custom community rules, cross-platform intelligence
• **User Experience**: Appeal system, educational responses, community feedback integration

**Technical Roadmap:**
• Continuous retraining pipeline
• External threat intelligence integration
• Proactive user protection warnings
• Advanced temporal pattern analysis

---

**Group [NUMBER] - CS152 Trust & Safety Engineering**
*AI-Powered Discord Moderation System* 