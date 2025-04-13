from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
import os
import requests
import json

from wati_api import wati_api, Message, Chat, Contact, MessageContext

def search_contacts(query: str) -> List[Dict[str, Any]]:
    """
    Search WhatsApp contacts by name or phone number.
    Returns all available contact information including name, phone number, WhatsApp ID, 
    creation date, status, custom parameters, and other fields from the WATI API.
    """
    contacts = wati_api.search_contacts(query)
    
    # Convert to dictionary format for the MCP API
    result = []
    for contact in contacts:
        # Create a dictionary with all available contact fields
        contact_dict = {
            "phone_number": contact.phone_number,
            "name": contact.name,
            "waid": contact.waid,
            "id": contact.id,
            "source": contact.source,
            "contact_status": contact.contact_status,
            "created": contact.created,
            "last_updated": contact.last_updated,
            "allow_broadcast": contact.allow_broadcast,
            "first_name": contact.first_name,
            "full_name": contact.full_name,
            "photo": contact.photo,
            "opted_in": contact.opted_in,
            "tenant_id": contact.tenant_id,
            "tag_name": contact.tag_name,
            "display_id": contact.display_id
        }
        
        # Add custom params if available
        if contact.custom_params:
            # Convert custom params from list of dicts to a single dict for easier access
            custom_params_dict = {}
            for param in contact.custom_params:
                if isinstance(param, dict) and "name" in param and "value" in param:
                    custom_params_dict[param["name"]] = param["value"]
            
            contact_dict["custom_params"] = custom_params_dict
        
        result.append(contact_dict)
    
    return result

def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_waid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context."""
    # Convert string dates to datetime if provided
    from_date = None
    to_date = None
    
    if after:
        try:
            from_date = datetime.fromisoformat(after)
        except ValueError:
            raise ValueError(f"Invalid date format for 'after': {after}. Please use ISO-8601 format.")

    if before:
        try:
            to_date = datetime.fromisoformat(before)
        except ValueError:
            raise ValueError(f"Invalid date format for 'before': {before}. Please use ISO-8601 format.")
            
    # Use the phone number or WAID provided
    phone_number = None
    if chat_waid:
        phone_number = chat_waid
    elif sender_phone_number:
        phone_number = sender_phone_number
    
    if not phone_number:
        return []
    
    # Get messages from the API
    messages = wati_api.get_messages(
        whatsapp_number=phone_number,
        page_size=limit,
        page_number=page + 1,  # API uses 1-based indexing
        from_date=from_date,
        to_date=to_date
    )
    
    # Format the messages for the response
    result = []
    for message in messages:
        result.append({
            "timestamp": message.timestamp.isoformat(),
            "sender": message.sender,
            "content": message.content,
            "is_from_me": message.is_from_me,
            "chat_waid": message.chat_waid,
            "id": message.id,
            "media_type": message.media_type
        })
    
    return result

def format_message(message: Message, show_chat_info: bool = True) -> str:
    """Format a single message with consistent formatting."""
    output = ""
    
    output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "
        
    content_prefix = ""
    if message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat WAID: {message.chat_waid}] "
    
    sender_name = "Me" if message.is_from_me else message.sender
    output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    
    return output

def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> str:
    """Format a list of messages for display."""
    output = ""
    if not messages:
        output += "No messages to display."
        return output
    
    for message in messages:
        output += format_message(message, show_chat_info)
    
    return output

def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria."""
    # For now, just return a list of contacts as chats
    contacts = wati_api.get_contacts(page_size=limit, page_number=page+1)
    
    result = []
    for contact in contacts:
        # Get the last message for this contact if requested
        last_message = None
        last_message_time = None
        last_sender = None
        last_is_from_me = None
        
        if include_last_message:
            messages = wati_api.get_messages(contact.phone_number, page_size=1, page_number=1)
            if messages:
                last_message = messages[0].content
                last_message_time = messages[0].timestamp.isoformat()
                last_sender = messages[0].sender
                last_is_from_me = messages[0].is_from_me
        
        chat = {
            "waid": contact.waid,
            "name": contact.name,
            "last_message_time": last_message_time,
            "last_message": last_message,
            "last_sender": last_sender,
            "last_is_from_me": last_is_from_me
        }
        
        result.append(chat)
    
    return result

def get_chat(chat_waid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by WAID."""
    # Get contact info
    contacts = wati_api.get_contacts(name=chat_waid)
    
    if not contacts:
        return {}
    
    contact = contacts[0]
    
    # Get the last message if requested
    last_message = None
    last_message_time = None
    last_sender = None
    last_is_from_me = None
    
    if include_last_message:
        messages = wati_api.get_messages(contact.phone_number, page_size=1, page_number=1)
        if messages:
            last_message = messages[0].content
            last_message_time = messages[0].timestamp.isoformat()
            last_sender = messages[0].sender
            last_is_from_me = messages[0].is_from_me
    
    return {
        "waid": contact.waid,
        "name": contact.name,
        "last_message_time": last_message_time,
        "last_message": last_message,
        "last_sender": last_sender,
        "last_is_from_me": last_is_from_me
    }

def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number."""
    return get_chat(sender_phone_number)

def get_contact_chats(waid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get the WhatsApp chat for the specified contact."""
    # With Wati, we only have direct chats
    chat = get_chat(waid)
    
    if chat:
        return [chat]
    else:
        return []

def get_last_interaction(waid: str) -> str:
    """Get most recent WhatsApp message involving the contact."""
    # Get the last message
    messages = wati_api.get_messages(waid, page_size=1, page_number=1)
    
    if messages:
        return format_message(messages[0])
    else:
        return "No recent interactions found."

def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message."""
    # With the Wati API, we need to know which chat the message is in
    # Since we don't have enough context, let's just get messages from recent chats
    
    # Get recent chats
    chats = list_chats(limit=5)
    
    for chat in chats:
        chat_waid = chat["waid"]
        
        context = wati_api.get_message_context(message_id, chat_waid, before, after)
        
        if context:
            # Format the message context for response
            return {
                "message": {
                    "timestamp": context.message.timestamp.isoformat(),
                    "sender": context.message.sender,
                    "content": context.message.content,
                    "is_from_me": context.message.is_from_me,
                    "chat_waid": context.message.chat_waid,
                    "id": context.message.id,
                    "media_type": context.message.media_type
                },
                "before": [
                    {
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "content": msg.content,
                        "is_from_me": msg.is_from_me,
                        "chat_waid": msg.chat_waid,
                        "id": msg.id,
                        "media_type": msg.media_type
                    }
                    for msg in context.before
                ],
                "after": [
                    {
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": msg.sender,
                        "content": msg.content,
                        "is_from_me": msg.is_from_me,
                        "chat_waid": msg.chat_waid,
                        "id": msg.id,
                        "media_type": msg.media_type
                    }
                    for msg in context.after
                ]
            }
    
    return {
        "message": None,
        "before": [],
        "after": []
    }

def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    """Send a WhatsApp message to a contact."""
    return wati_api.send_message(recipient, message)

def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    """Send a file via WhatsApp to the specified recipient."""
    return wati_api.send_file(recipient, media_path)

def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    """Send any audio file as a WhatsApp audio message to the specified recipient."""
    # Wati API doesn't have a specific audio message endpoint, so we use the regular file endpoint
    return wati_api.send_file(recipient, media_path)

def download_media(message_id: str, chat_waid: str) -> Optional[str]:
    """Download media from a WhatsApp message and return the local file path."""
    # In Wati API, we need the filename, not message ID
    # Since we don't have a way to get the filename from the message ID,
    # we'll just use the message ID as the filename for now
    return wati_api.download_media(message_id)

def send_interactive_buttons(
    recipient: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    header_image: Optional[str] = None,
    header_video: Optional[str] = None,
    header_document: Optional[str] = None
) -> Tuple[bool, str]:
    """Send an interactive WhatsApp message with buttons."""
    return wati_api.send_interactive_buttons(
        recipient=recipient,
        body_text=body_text,
        buttons=buttons,
        header_text=header_text,
        footer_text=footer_text,
        header_image=header_image,
        header_video=header_video,
        header_document=header_document
    )
