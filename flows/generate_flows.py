from graphviz import Digraph
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'DiscordBot')))
from helpers import ABUSE_TYPES, MESSAGE_ACTIONS, USER_ACTIONS, SEVERITY_LEVELS

def add_abuse_type_nodes(dot, parent, abuse_type, user_color, system_color):
    """Recursively add nodes for abuse types and subtypes"""
    if abuse_type.subtypes:
        subtype_prompt = f"Select {abuse_type.label} subtype"
        subtype_prompt_id = f"{parent}_subtype_prompt"
        dot.node(subtype_prompt_id, subtype_prompt, fillcolor=system_color)
        dot.edge(parent, subtype_prompt_id)
        for key, subtype in abuse_type.subtypes.items():
            subtype_id = f"{subtype_prompt_id}_{key}"
            dot.node(subtype_id, subtype.label, fillcolor=user_color)
            dot.edge(subtype_prompt_id, subtype_id)
            add_abuse_type_nodes(dot, subtype_id, subtype, user_color, system_color)
    else:
        # End of this path, go to additional info and confirmation
        dot.edge(parent, 'additional_info')

def create_user_reporting_flow():
    """Create the user reporting flow diagram"""
    dot = Digraph(comment='User Reporting Flow')
    dot.attr(rankdir='TB')
    dot.attr(ranksep='2.0')
    
    # Node styles
    dot.attr('node', shape='box', style='rounded,filled', fontsize='12')
    user_color = 'white'  # User action
    system_color = 'lightblue'  # System message/response
    
    # Start
    dot.node('start', 'User reports a message', fillcolor=user_color)
    dot.node('reason', 'Please select the reason for reporting this message.', fillcolor=system_color)
    
    # Add all top-level abuse types
    for key, abuse_type in ABUSE_TYPES.items():
        node_id = f"abuse_{key}"
        dot.node(node_id, abuse_type.label, fillcolor=user_color)
        dot.edge('reason', node_id)
        add_abuse_type_nodes(dot, node_id, abuse_type, user_color, system_color)
        # # For the focused abuse type (fraud), expand all subtypes
        # if key == 'fraud':
        #     add_abuse_type_nodes(dot, node_id, abuse_type, user_color, system_color)
        # else:
        #     # For other types, go directly to additional info
        #     dot.edge(node_id, 'additional_info')
    
    # Additional info and confirmation
    dot.node('additional_info', 'Add additional information (optional)', fillcolor=system_color)
    dot.node('confirm', 'Review and confirm report', fillcolor=system_color)
    dot.node('thank', 'Thank you for reporting. Our moderation team will review your report and take appropriate action.', fillcolor=system_color)
    dot.edge('additional_info', 'confirm')
    dot.edge('confirm', 'thank')
    
    # Block user option
    dot.node('block_prompt', 'Would you like to block this user?', fillcolor=system_color)
    dot.node('block_yes', 'Yes', fillcolor=user_color)
    dot.node('block_no', 'No', fillcolor=user_color)
    dot.edge('thank', 'block_prompt')
    dot.edge('block_prompt', 'block_yes')
    dot.edge('block_prompt', 'block_no')
    
    dot.render('user_reporting_flow', format='pdf', cleanup=True)

def create_moderator_flow():
    """Create the moderator flow diagram"""
    dot = Digraph(comment='Moderator Flow')
    dot.attr(rankdir='TB')
    
    # Node styles
    dot.attr('node', shape='box', style='rounded,filled', fontsize='12')
    mod_color = 'white'  # Moderator action
    system_color = 'lightgreen'  # System action/response
    
    # Start
    dot.node('start', 'Report received in mod channel', fillcolor=system_color)
    dot.node('review', 'Moderator reviews report details', fillcolor=mod_color)
    
    # Message action
    msg_action_id = 'msg_action'
    msg_action_label = 'Choose message action:' + ''.join(f"\n- {v}" for v in MESSAGE_ACTIONS.values())
    dot.node(msg_action_id, msg_action_label, fillcolor=mod_color)
    dot.edge('review', msg_action_id)
    for key, label in MESSAGE_ACTIONS.items():
        node_id = f"msg_{key}"
        dot.node(node_id, f"System: {label}", fillcolor=system_color)
        dot.edge(msg_action_id, node_id, label=label)
        dot.edge(node_id, 'user_action')
    
    # User action
    user_action_id = 'user_action'
    user_action_label = 'Choose user action:' + ''.join(f"\n- {v['label']}" for v in USER_ACTIONS.values())
    dot.node(user_action_id, user_action_label, fillcolor=mod_color)
    for key, v in USER_ACTIONS.items():
        node_id = f"user_{key}"
        dot.node(node_id, f"System: {v['label']}", fillcolor=system_color)
        dot.edge(user_action_id, node_id, label=v['label'])
        dot.edge(node_id, 'severity')
    
    # Severity
    severity_label = 'Set severity level:' + ''.join(f"\n- {v['label']}" for v in SEVERITY_LEVELS.values())
    dot.node('severity', severity_label, fillcolor=mod_color)
    dot.edge('msg_action', 'user_action')  # For completeness
    dot.edge('user_action', 'severity')
    
    # Summary
    dot.node('summary', 'System sends moderation summary', fillcolor=system_color)
    dot.node('done', 'Report marked as handled', fillcolor=system_color)
    dot.edge('severity', 'summary')
    dot.edge('summary', 'done')
    
    dot.render('moderator_flow', format='pdf', cleanup=True)

if __name__ == '__main__':
    create_user_reporting_flow()
    create_moderator_flow() 