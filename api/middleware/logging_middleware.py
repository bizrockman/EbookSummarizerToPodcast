"""
Logging-Middleware für API Request/Response Tracking
"""
import time
import logging
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

# Logger konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware für umfassendes Request/Response Logging
    
    Features:
    - Loggt alle eingehenden Requests mit Details
    - Loggt Response Status und Dauer
    - Fügt Request-ID hinzu für Tracking
    - Loggt Request Body bei POST/PUT/PATCH
    - Farbige Ausgabe für bessere Lesbarkeit
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Verarbeite Request und Response"""
        
        # Generiere Request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Start Zeit
        start_time = time.time()
        
        # Extrahiere Request Details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_ip = request.client.host if request.client else "unknown"
        
        # API Key (wenn vorhanden)
        api_key = request.headers.get("X-API-Key", "")
        api_key_display = f"{api_key[:8]}..." if api_key else "none"
        
        # Logge eingehenden Request
        logger.info(
            f"[{request_id}] ➡️  {method:6s} {path} | IP: {client_ip} | API Key: {api_key_display}"
        )
        
        # Logge Query Parameters wenn vorhanden
        if query_params:
            logger.debug(f"[{request_id}]     Query: {json.dumps(query_params)}")
        
        # Logge Request Body bei POST/PUT/PATCH (nur für nicht-file uploads)
        if method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    # Body lesen (muss danach wieder gesetzt werden)
                    body = await request.body()
                    if body:
                        body_str = body.decode("utf-8")
                        # Limitiere Body-Länge für Logging
                        if len(body_str) > 500:
                            body_display = body_str[:500] + "..."
                        else:
                            body_display = body_str
                        
                        logger.debug(f"[{request_id}]     Body: {body_display}")
                        
                        # Body wieder für Handler verfügbar machen
                        async def receive():
                            return {"type": "http.request", "body": body}
                        request._receive = receive
                except Exception as e:
                    logger.warning(f"[{request_id}]     Konnte Body nicht lesen: {e}")
        
        # Verarbeite Request
        try:
            response = await call_next(request)
            
            # Berechne Dauer
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)
            
            # Status Code Farbe/Symbol
            status_code = response.status_code
            if status_code < 300:
                status_symbol = "✅"
                level = logging.INFO
            elif status_code < 400:
                status_symbol = "↩️"
                level = logging.INFO
            elif status_code < 500:
                status_symbol = "⚠️"
                level = logging.WARNING
            else:
                status_symbol = "❌"
                level = logging.ERROR
            
            # Logge Response
            logger.log(
                level,
                f"[{request_id}] {status_symbol}  {status_code} {method:6s} {path} | {duration_ms}ms"
            )
            
            # Füge Request-ID zu Response Headers hinzu
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Berechne Dauer bis zum Fehler
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)
            
            # Logge Exception
            logger.error(
                f"[{request_id}] 💥  500 {method:6s} {path} | {duration_ms}ms | Error: {str(e)}",
                exc_info=True
            )
            
            # Re-raise Exception für FastAPI Error Handler
            raise


class DetailedLoggingMiddleware(BaseHTTPMiddleware):
    """
    Noch detailliertere Logging-Middleware (optional, für Debugging)
    
    Zusätzliche Features:
    - Loggt alle Headers
    - Loggt Response Body (bei kleinen Responses)
    - Loggt User-Agent und weitere Details
    """
    
    def __init__(self, app: ASGIApp, log_headers: bool = False, log_response_body: bool = False):
        super().__init__(app)
        self.log_headers = log_headers
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Verarbeite Request und Response"""
        
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Request Info
        method = request.method
        path = request.url.path
        client = request.client
        client_ip = client.host if client else "unknown"
        client_port = client.port if client else "unknown"
        
        # User Agent
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Basis-Log
        logger.info(f"[{request_id}] ➡️  {method} {path}")
        logger.debug(f"[{request_id}]     Client: {client_ip}:{client_port}")
        logger.debug(f"[{request_id}]     User-Agent: {user_agent}")
        
        # Headers loggen (optional)
        if self.log_headers:
            headers_dict = dict(request.headers)
            # Sensitive Headers ausblenden
            if "x-api-key" in headers_dict:
                headers_dict["x-api-key"] = headers_dict["x-api-key"][:8] + "..."
            logger.debug(f"[{request_id}]     Headers: {json.dumps(headers_dict, indent=2)}")
        
        # Verarbeite Request
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)
            
            status_code = response.status_code
            
            # Status-Emoji
            if status_code < 300:
                emoji = "✅"
            elif status_code < 400:
                emoji = "↩️"
            elif status_code < 500:
                emoji = "⚠️"
            else:
                emoji = "❌"
            
            logger.info(
                f"[{request_id}] {emoji}  {status_code} | {duration_ms}ms"
            )
            
            # Response Headers loggen (optional)
            if self.log_headers:
                response_headers = dict(response.headers)
                logger.debug(f"[{request_id}]     Response Headers: {json.dumps(response_headers, indent=2)}")
            
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            duration_ms = int(duration * 1000)
            
            logger.error(
                f"[{request_id}] 💥  ERROR | {duration_ms}ms | {str(e)}",
                exc_info=True
            )
            raise


def setup_file_logging(log_file: str = "api.log"):
    """
    Zusätzlich: Logging in Datei
    
    Args:
        log_file: Pfad zur Log-Datei
    """
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    
    logger.addHandler(file_handler)
    logger.info(f"File logging aktiviert: {log_file}")

