from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media,
    send_interactive_buttons as whatsapp_send_interactive_buttons
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """
    Searches WhatsApp contacts based on a query.
    Returns all available contact information including name, phone number, WhatsApp ID,
    creation date, status, custom parameters, and other fields from the WATI API.
    
    Args:
        query: A search term to find matching contacts
        
    Returns:
        A list of contacts with all available contact information
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
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
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_waid: Optional WhatsApp ID (WAID) to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_waid=chat_waid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or WAID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_waid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by WAID.
    
    Args:
        chat_waid: The WhatsApp ID (WAID) of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_waid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(waid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get the WhatsApp chat for the specified contact.
    
    Args:
        waid: The contact's WhatsApp ID (WAID) to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(waid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(waid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        waid: The WhatsApp ID (WAID) of the contact to search for
    """
    message = whatsapp_get_last_interaction(waid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a contact.

    Args:
        recipient: The recipient's phone number with country code but no + or other symbols
                 (e.g., "85264318721")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient.
    
    Args:
        recipient: The recipient's phone number with country code but no + or other symbols
                 (e.g., "85264318721")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient.
    
    Args:
        recipient: The recipient's phone number with country code but no + or other symbols
                 (e.g., "85264318721")
        media_path: The absolute path to the audio file to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_waid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_waid: The WhatsApp ID (WAID) of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_waid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def send_interactive_buttons(
    recipient: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    header_image: Optional[str] = None,
    header_video: Optional[str] = None,
    header_document: Optional[str] = None
) -> Dict[str, Any]:
    """Send an interactive WhatsApp message with buttons.
    
    Args:
        recipient: The recipient's phone number with country code but no + or other symbols
                 (e.g., "85264318721")
        body_text: The main text content of the message
        buttons: List of button objects, each with 'text' key (and optionally 'id')
        header_text: Optional text to display in the header
        footer_text: Optional text to display in the footer
        header_image: Optional URL or local path to an image to display in the header
        header_video: Optional URL or local path to a video to display in the header
        header_document: Optional URL or local path to a document to display in the header
        
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    if not body_text:
        return {
            "success": False,
            "message": "Body text must be provided"
        }
    
    if not buttons or not isinstance(buttons, list) or len(buttons) == 0:
        return {
            "success": False,
            "message": "At least one button must be provided"
        }
    
    # Call the whatsapp_send_interactive_buttons function
    success, status_message = whatsapp_send_interactive_buttons(
        recipient=recipient,
        body_text=body_text,
        buttons=buttons,
        header_text=header_text,
        footer_text=footer_text,
        header_image=header_image,
        header_video=header_video,
        header_document=header_document
    )
    
    return {
        "success": success,
        "message": status_message
    }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')