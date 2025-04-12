import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wati_api")

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
# These values should be set in environment variables
WATI_API_BASE_URL = os.environ.get("WATI_API_BASE_URL", "https://api.wati.io")
WATI_TENANT_ID = os.environ.get("WATI_TENANT_ID", "your-tenant-id")
WATI_AUTH_TOKEN = os.environ.get("WATI_AUTH_TOKEN", "your-auth-token")

logger.info(f"Initialized with API URL: {WATI_API_BASE_URL}, Tenant ID: {WATI_TENANT_ID}")

# Data models
@dataclass
class Contact:
    """WhatsApp contact data model"""
    phone_number: str
    name: Optional[str]
    jid: Optional[str] = None
    
@dataclass
class Message:
    """WhatsApp message data model"""
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None

@dataclass
class Chat:
    """WhatsApp chat data model"""
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern."""
        return self.jid.endswith("@g.us")

@dataclass
class MessageContext:
    """Context around a specific message"""
    message: Message
    before: List[Message]
    after: List[Message]

class WatiAPI:
    """Wrapper for the Wati WhatsApp API"""
    
    def __init__(self, base_url: str = WATI_API_BASE_URL, tenant_id: str = WATI_TENANT_ID, auth_token: str = WATI_AUTH_TOKEN):
        """
        Initialize the Wati API client.
        
        Args:
            base_url: The base URL for the API
            tenant_id: Your Wati tenant ID
            auth_token: Your Wati authentication token
        """
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        logger.info(f"WatiAPI initialized with base_url={base_url}, tenant_id={tenant_id}")
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make an API request to Wati.
        
        Args:
            method: The HTTP method (GET, POST, etc.)
            endpoint: The API endpoint to call
            params: Query parameters (for GET requests)
            data: Request body (for POST requests)
            
        Returns:
            The response data as a dictionary
        """
        url = f"{self.base_url}/{self.tenant_id}/{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Request params: {params}")
        logger.debug(f"Request data: {data}")
        
        try:
            if method.upper() == "GET":
                logger.debug(f"Sending GET request with headers: {self.headers}")
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == "POST":
                logger.debug(f"Sending POST request with headers: {self.headers}")
                response = requests.post(url, headers=self.headers, params=params, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            
            # Try to get response content as text for logging
            try:
                response_text = response.text
                logger.debug(f"Response body: {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
            except Exception as e:
                logger.debug(f"Could not get response text: {e}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                result = response.json()
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return {"success": False, "error": f"Invalid JSON response: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_contacts(self, name: Optional[str] = None, page_size: int = 20, page_number: int = 1) -> List[Contact]:
        """Get a list of contacts.
        
        Args:
            name: Optional name filter
            page_size: Number of results per page
            page_number: Page number for pagination
            
        Returns:
            A list of Contact objects
        """
        logger.info(f"Getting contacts with name={name}, page_size={page_size}, page_number={page_number}")
        
        params = {
            "pageSize": page_size,
            "pageNumber": page_number
        }
        
        if name:
            params["name"] = name
            
        response = self._make_request("GET", "api/v1/getContacts", params=params)
        logger.debug(f"get_contacts response: {response}")
        
        contacts = []
        # Check different possible response formats
        if isinstance(response, dict):
            # Try to find contacts data in different possible fields
            contacts_data = None
            
            if "contact_list" in response:
                contacts_data = response["contact_list"]
            elif "contacts" in response:
                contacts_data = response["contacts"]
            elif "data" in response:
                contacts_data = response["data"]
            elif "result" in response and isinstance(response["result"], list):
                contacts_data = response["result"]
            
            if contacts_data and isinstance(contacts_data, list):
                logger.info(f"Found {len(contacts_data)} contacts")
                for contact_data in contacts_data:
                    logger.debug(f"Processing contact: {contact_data}")
                    phone_number = ""
                    name = ""
                    
                    # Try different common field names for phone number
                    for field in ["phone", "phoneNumber", "wAid", "number", "whatsappNumber"]:
                        if field in contact_data and contact_data[field]:
                            phone_number = str(contact_data[field])
                            break
                            
                    # Try different common field names for name
                    for field in ["fullName", "firstName", "name", "contactName", "displayName"]:
                        if field in contact_data and contact_data[field]:
                            name = str(contact_data[field])
                            break
                    
                    if phone_number:
                        contact = Contact(
                            phone_number=phone_number,
                            name=name,
                            jid=phone_number
                        )
                        contacts.append(contact)
        
        if not contacts:
            logger.warning(f"Failed to parse contacts or no contacts found. Response structure: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        else:
            logger.info(f"Successfully parsed {len(contacts)} contacts")
                
        return contacts
    
    def search_contacts(self, query: str) -> List[Contact]:
        """Search for contacts by name or phone number.
        
        Args:
            query: The search query
            
        Returns:
            A list of matching Contact objects
        """
        logger.info(f"Searching contacts with query={query}")
        return self.get_contacts(name=query)
    
    def get_messages(self, whatsapp_number: str, page_size: int = 20, page_number: int = 1,
                   from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> List[Message]:
        """Get messages for a specific WhatsApp number.
        
        Args:
            whatsapp_number: The WhatsApp number to get messages for
            page_size: Number of results per page
            page_number: Page number for pagination
            from_date: Optional start date filter
            to_date: Optional end date filter
            
        Returns:
            A list of Message objects
        """
        logger.info(f"Getting messages for {whatsapp_number}, page_size={page_size}, page_number={page_number}")
        
        params = {
            "pageSize": page_size,
            "pageNumber": page_number
        }
        
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%d %H:%M:%S")
            
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%d %H:%M:%S")
            
        endpoint = f"api/v1/getMessages/{whatsapp_number}"
        response = self._make_request("GET", endpoint, params=params)
        logger.debug(f"get_messages response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        messages = []
        # Check different possible response formats
        if isinstance(response, dict):
            # Try to find messages data in different possible fields
            messages_data = None
            
            if "messages" in response:
                messages_data = response["messages"]
            elif "conversation" in response:
                messages_data = response["conversation"]
            elif "data" in response:
                messages_data = response["data"]
            elif "result" in response and isinstance(response["result"], list):
                messages_data = response["result"]
            
            # If we still don't have messages_data, check if there's a nested structure
            if not messages_data and "result" in response and isinstance(response["result"], dict):
                result = response["result"]
                if "messages" in result:
                    messages_data = result["messages"]
                elif "conversation" in result:
                    messages_data = result["conversation"]
            
            if messages_data and isinstance(messages_data, list):
                logger.info(f"Found {len(messages_data)} messages")
                for msg_data in messages_data:
                    logger.debug(f"Processing message: {msg_data}")
                    
                    # Try to determine if message is from me
                    is_from_me = False
                    for field in ["fromMe", "isFromMe", "outgoing", "isSent"]:
                        if field in msg_data:
                            is_from_me = bool(msg_data[field])
                            break
                    
                    # Try to get the timestamp
                    timestamp = datetime.now()
                    for field in ["timestamp", "time", "date", "created", "dateTime"]:
                        if field in msg_data:
                            time_str = str(msg_data[field])
                            try:
                                # Try different timestamp formats
                                if 'T' in time_str:
                                    timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                                else:
                                    try:
                                        timestamp = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        timestamp = datetime.strptime(time_str, "%b-%d-%Y")
                                break
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid timestamp format: {time_str} - Error: {e}")
                    
                    # Try to get content
                    content = ""
                    for field in ["text", "content", "body", "message", "messageText"]:
                        if field in msg_data and msg_data[field]:
                            content = str(msg_data[field])
                            break
                    
                    # Try to get message ID
                    msg_id = ""
                    for field in ["id", "messageId", "message_id"]:
                        if field in msg_data:
                            msg_id = str(msg_data[field])
                            break
                    
                    # Try to get media type
                    media_type = None
                    for field in ["type", "messageType", "media_type"]:
                        if field in msg_data and msg_data[field] != "chat" and msg_data[field] != "text":
                            media_type = msg_data[field]
                            break
                    
                    # Create a message object
                    message = Message(
                        timestamp=timestamp,
                        sender=msg_data.get("owner", "") if is_from_me else whatsapp_number,
                        content=content,
                        is_from_me=is_from_me,
                        chat_jid=f"whatsapp_number",
                        id=msg_id,
                        media_type=media_type
                    )
                    messages.append(message)
        
        if not messages:
            logger.warning(f"Failed to parse messages or no messages found. Response structure: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        else:
            logger.info(f"Successfully parsed {len(messages)} messages")
                
        return messages

    def get_message_context(self, message_id: str, chat_jid: str, before: int = 5, after: int = 5) -> Optional[MessageContext]:
        """Get context around a specific message.
        
        Args:
            message_id: The ID of the message to get context for
            chat_jid: The JID of the chat containing the message
            before: Number of messages to include before the target message
            after: Number of messages to include after the target message
            
        Returns:
            A MessageContext object or None if the message was not found
        """
        # Extract phone number from JID
        if "@" in chat_jid:
            phone_number = chat_jid.split("@")[0]
        else:
            phone_number = chat_jid
            
        # Get all messages for this chat
        messages = self.get_messages(phone_number, page_size=before + after + 1)
        
        target_message = None
        target_index = -1
        
        # Find the target message
        for i, msg in enumerate(messages):
            if msg.id == message_id:
                target_message = msg
                target_index = i
                break
                
        if not target_message:
            return None
            
        # Get context messages
        before_messages = []
        after_messages = []
        
        if target_index > 0:
            start_index = max(0, target_index - before)
            before_messages = messages[start_index:target_index]
            
        if target_index < len(messages) - 1:
            end_index = min(len(messages), target_index + after + 1)
            after_messages = messages[target_index + 1:end_index]
            
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
    
    def send_message(self, recipient: str, message: str) -> Tuple[bool, str]:
        """Send a WhatsApp message.
        
        Args:
            recipient: The recipient's phone number or JID
            message: The message text to send
            
        Returns:
            A tuple of (success, message)
        """
        # Extract phone number from JID if needed
        if "@" in recipient:
            recipient = recipient.split("@")[0]
            
        endpoint = f"api/v1/sendSessionMessage/{recipient}"
        params = {
            "messageText": message
        }
        
        response = self._make_request("POST", endpoint, params=params)
        
        if response.get("success", False):
            return True, "Message sent successfully"
        else:
            return False, response.get("error", "Unknown error")
            
    def send_file(self, recipient: str, media_path: str, caption: str = "") -> Tuple[bool, str]:
        """Send a file via WhatsApp.
        
        Args:
            recipient: The recipient's phone number or JID
            media_path: The path to the media file
            caption: Optional caption for the media
            
        Returns:
            A tuple of (success, message)
        """
        # Extract phone number from JID if needed
        if "@" in recipient:
            recipient = recipient.split("@")[0]
            
        endpoint = f"api/v1/sendSessionFile/{recipient}"
        params = {}
        
        if caption:
            params["caption"] = caption
            
        try:
            url = f"{self.base_url}/{self.tenant_id}/{endpoint}"
            
            with open(media_path, "rb") as file:
                files = {"file": file}
                response = requests.post(url, headers={"Authorization": self.headers["Authorization"]}, 
                                        params=params, files=files)
                
            response.raise_for_status()
            result = response.json()
            
            if result.get("success", False):
                return True, "File sent successfully"
            else:
                return False, result.get("error", "Unknown error")
                
        except Exception as e:
            return False, f"Error sending file: {str(e)}"
            
    def download_media(self, file_name: str) -> Optional[str]:
        """Download media from WhatsApp.
        
        Args:
            file_name: The name of the file to download
            
        Returns:
            The local path to the downloaded file or None if download failed
        """
        endpoint = f"api/v1/getMedia"
        params = {
            "fileName": file_name
        }
        
        try:
            url = f"{self.base_url}/{self.tenant_id}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, stream=True)
            
            if response.status_code == 200:
                # Create downloads directory if it doesn't exist
                os.makedirs("downloads", exist_ok=True)
                
                # Save the file
                local_path = os.path.join("downloads", file_name)
                with open(local_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            
                return local_path
            else:
                print(f"Error downloading media: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error downloading media: {str(e)}")
            return None
                
    def send_template_message(self, recipient: str, template_name: str, broadcast_name: str, 
                             parameters: List[Dict[str, str]]) -> Tuple[bool, str]:
        """Send a WhatsApp template message.
        
        Args:
            recipient: The recipient's phone number or JID
            template_name: The name of the template to use
            broadcast_name: The name for this broadcast
            parameters: List of template parameters as dictionaries with 'name' and 'value' keys
            
        Returns:
            A tuple of (success, message)
        """
        # Extract phone number from JID if needed
        if "@" in recipient:
            recipient = recipient.split("@")[0]
            
        endpoint = f"api/v1/sendTemplateMessage"
        params = {
            "whatsappNumber": recipient
        }
        
        data = {
            "template_name": template_name,
            "broadcast_name": broadcast_name,
            "parameters": parameters
        }
        
        response = self._make_request("POST", endpoint, params=params, data=data)
        
        if response.get("success", False):
            return True, "Template message sent successfully"
        else:
            return False, response.get("error", "Unknown error")

# Create a global API instance
wati_api = WatiAPI() 