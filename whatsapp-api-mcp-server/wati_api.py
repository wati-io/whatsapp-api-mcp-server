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
    waid: Optional[str] = None
    
@dataclass
class Message:
    """WhatsApp message data model"""
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_waid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None

@dataclass
class Chat:
    """WhatsApp chat data model"""
    waid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

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
                    waid = ""
                    
                    # Try different common field names for phone number
                    for field in ["phone", "phoneNumber", "wAid", "number", "whatsappNumber"]:
                        if field in contact_data and contact_data[field]:
                            phone_number = str(contact_data[field])
                            break
                    
                    # Try to get WAID (WhatsApp ID)
                    for field in ["wAid", "id", "waId", "whatsappId"]:
                        if field in contact_data and contact_data[field]:
                            waid = str(contact_data[field])
                            break
                    
                    # If WAID is not found, use phone number as WAID
                    if not waid and phone_number:
                        waid = phone_number
                            
                    # Try different common field names for name
                    for field in ["fullName", "firstName", "name", "contactName", "displayName"]:
                        if field in contact_data and contact_data[field]:
                            name = str(contact_data[field])
                            break
                    
                    if phone_number:
                        contact = Contact(
                            phone_number=phone_number,
                            name=name,
                            waid=waid
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
        logger.debug(f"get_messages complete response: {response}")
        logger.debug(f"get_messages response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        # Check if the API call was successful
        if isinstance(response, dict) and response.get("result") == "success":
            logger.info("API call was successful")
        
        messages = []
        # Check different possible response formats
        if isinstance(response, dict):
            # Try to find messages data in different possible fields
            messages_data = None
            
            # New API response structure: messages are in 'messages.items'
            if "messages" in response and isinstance(response["messages"], dict) and "items" in response["messages"]:
                messages_data = response["messages"]["items"]
                logger.debug(f"Found {len(messages_data) if messages_data else 0} messages in messages.items")
            # Check older API response formats
            elif "messages" in response and isinstance(response["messages"], list):
                messages_data = response["messages"]
                logger.debug(f"Found {len(messages_data) if messages_data else 0} messages in messages list")
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
                    if isinstance(result["messages"], dict) and "items" in result["messages"]:
                        messages_data = result["messages"]["items"]
                    else:
                        messages_data = result["messages"]
                elif "conversation" in result:
                    messages_data = result["conversation"]
            
            if messages_data and isinstance(messages_data, list):
                logger.info(f"Found {len(messages_data)} messages")
                for msg_data in messages_data:
                    logger.debug(f"Processing message: {msg_data}")
                    
                    # Try to determine if message is from me
                    is_from_me = False
                    for field in ["fromMe", "isFromMe", "outgoing", "isSent", "owner"]:
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
                                elif time_str.isdigit():  # Unix timestamp
                                    timestamp = datetime.fromtimestamp(int(time_str))
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
                    for field in ["id", "messageId", "message_id", "localMessageId"]:
                        if field in msg_data and msg_data[field]:
                            msg_id = str(msg_data[field])
                            break
                    
                    # Try to get media type
                    media_type = None
                    for field in ["type", "messageType", "media_type"]:
                        if field in msg_data and msg_data[field] != "chat" and msg_data[field] != "text":
                            media_type = msg_data[field]
                            break
                    
                    # Determine sender - for outgoing messages, use operator name if available
                    sender = ""
                    if is_from_me:
                        for field in ["operatorName", "assignedId"]:
                            if field in msg_data and msg_data[field]:
                                sender = str(msg_data[field])
                                break
                        if not sender:
                            sender = "You"
                    else:
                        sender = whatsapp_number
                    
                    # Create a message object
                    message = Message(
                        timestamp=timestamp,
                        sender=sender,
                        content=content,
                        is_from_me=is_from_me,
                        chat_waid=whatsapp_number,
                        id=msg_id,
                        media_type=media_type
                    )
                    messages.append(message)
        
        if not messages:
            logger.warning(f"Failed to parse messages or no messages found. Response structure: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            if isinstance(response, dict) and "messages" in response and isinstance(response["messages"], dict):
                logger.warning(f"Messages structure: {list(response['messages'].keys()) if isinstance(response['messages'], dict) else 'Not a dict'}")
        else:
            logger.info(f"Successfully parsed {len(messages)} messages")
                
        return messages

    def get_message_context(self, message_id: str, chat_waid: str, before: int = 5, after: int = 5) -> Optional[MessageContext]:
        """Get context around a specific message.
        
        Args:
            message_id: The ID of the message to get context for
            chat_waid: The WAID of the chat containing the message
            before: Number of messages to include before the target message
            after: Number of messages to include after the target message
            
        Returns:
            A MessageContext object or None if the message was not found
        """
        # Get all messages for this chat
        messages = self.get_messages(chat_waid, page_size=before + after + 1)
        
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
            recipient: The recipient's phone number or WAID
            message: The message text to send
            
        Returns:
            A tuple of (success, message)
        """
        endpoint = f"api/v1/sendSessionMessage/{recipient}"
        params = {
            "messageText": message
        }
        
        response = self._make_request("POST", endpoint, params=params)
        logger.debug(f"Complete send_message response: {response}")
        
        # Try to get the actual message from the response
        response_message = "Unknown message"
        if isinstance(response, dict):
            if "message" in response:
                response_message = response["message"]
        
        # WATI API has inconsistent success indicators
        # Per the logs, 'success' indicates API call success, while 'result' indicates operation success
        operation_success = False
        if isinstance(response, dict):
            # Check 'result' field first as it seems to indicate the operation success
            if "result" in response:
                operation_success = bool(response["result"])
            # If no 'result' field, fall back to the 'success' field
            elif response.get("success", False):
                operation_success = True
        
        return operation_success, response_message
            
    def send_file(self, recipient: str, media_path: str, caption: str = "") -> Tuple[bool, str]:
        """Send a file via WhatsApp.
        
        Args:
            recipient: The recipient's phone number or WAID
            media_path: The path to the media file or a URL
            caption: Optional caption for the media
            
        Returns:
            A tuple of (success, message)
        """
        endpoint = f"api/v1/sendSessionFile/{recipient}"
        params = {}
        
        if caption:
            params["caption"] = caption
            
        # Check if media_path is a URL
        is_url = media_path.startswith(('http://', 'https://'))
        temp_file = None
        
        try:
            url = f"{self.base_url}/{self.tenant_id}/{endpoint}"
            
            # If it's a URL, download it to a temp file first
            if is_url:
                logger.info(f"Detected URL: {media_path}. Downloading to temporary file...")
                import tempfile
                import urllib.request
                from urllib.parse import urlparse
                from os.path import basename
                import mimetypes
                
                # Create a temporary file with an appropriate extension
                parsed_url = urlparse(media_path)
                file_name = basename(parsed_url.path)
                
                # If no extension in the URL, default to .tmp
                extension = os.path.splitext(file_name)[1]
                if not extension:
                    extension = ".tmp"
                
                # Create the temp file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
                temp_file.close()
                
                # Download the file
                try:
                    urllib.request.urlretrieve(media_path, temp_file.name)
                    logger.info(f"Downloaded URL to temporary file: {temp_file.name}")
                    media_path = temp_file.name
                except Exception as e:
                    return False, f"Error downloading file from URL: {str(e)}"
            
            # Determine the MIME type of the file
            content_type = None
            try:
                import mimetypes
                content_type = mimetypes.guess_type(media_path)[0]
                if not content_type:
                    # Try to determine content type from extension
                    ext = os.path.splitext(media_path)[1].lower()
                    content_type_map = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp',
                        '.pdf': 'application/pdf',
                        '.mp3': 'audio/mpeg',
                        '.mp4': 'video/mp4',
                        '.ogg': 'audio/ogg',
                        '.txt': 'text/plain',
                        '.doc': 'application/msword',
                        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    }
                    content_type = content_type_map.get(ext, 'application/octet-stream')
                
                logger.info(f"Determined content type: {content_type} for file: {media_path}")
            except Exception as e:
                logger.warning(f"Failed to determine content type: {str(e)}")
                content_type = 'application/octet-stream'  # Default fallback
            
            # Now send the local file with the appropriate content type
            with open(media_path, "rb") as file:
                # Specify the content type in the files parameter
                file_tuple = (os.path.basename(media_path), file, content_type)
                files = {"file": file_tuple}
                
                logger.info(f"Sending file {media_path} with content type: {content_type}")
                response = requests.post(url, headers={"Authorization": self.headers["Authorization"]}, 
                                        params=params, files=files)
                
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Complete send_file response: {result}")
            
            # Try to get the actual message from the response
            response_message = "Unknown message"
            if isinstance(result, dict):
                if "message" in result:
                    response_message = result["message"]
                elif "error" in result:
                    response_message = result["error"]
            
            # Check both 'result' and 'success' fields
            operation_success = False
            if isinstance(result, dict):
                # Check 'result' field first as it seems to indicate the operation success
                if "result" in result:
                    operation_success = bool(result["result"])
                # If no 'result' field, fall back to the 'success' field
                elif result.get("success", False):
                    operation_success = True
            
            return operation_success, response_message
                
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}")
            return False, f"Error sending file: {str(e)}"
        finally:
            # Clean up the temporary file if it exists
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    logger.info(f"Deleted temporary file: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file.name}: {str(e)}")
            
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
                logger.error(f"Error downloading media: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None
                
    def send_template_message(self, recipient: str, template_name: str, broadcast_name: str, 
                             parameters: List[Dict[str, str]]) -> Tuple[bool, str]:
        """Send a WhatsApp template message.
        
        Args:
            recipient: The recipient's phone number or WAID
            template_name: The name of the template to use
            broadcast_name: The name for this broadcast
            parameters: List of template parameters as dictionaries with 'name' and 'value' keys
            
        Returns:
            A tuple of (success, message)
        """
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
        logger.debug(f"Complete send_template_message response: {response}")
        
        # Try to get the actual message from the response
        response_message = "Unknown message"
        if isinstance(response, dict):
            if "message" in response:
                response_message = response["message"]
        
        # Check both 'result' and 'success' fields
        operation_success = False
        if isinstance(response, dict):
            # Check 'result' field first as it seems to indicate the operation success
            if "result" in response:
                operation_success = bool(response["result"])
            # If no 'result' field, fall back to the 'success' field
            elif response.get("success", False):
                operation_success = True
        
        return operation_success, response_message

# Create a global API instance
wati_api = WatiAPI() 