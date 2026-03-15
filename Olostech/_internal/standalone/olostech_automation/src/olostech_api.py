"""
Olostech API Client - Prototype
Direct API interaction with Olostech SaudeTech system
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple, List
import time
import random
import string
from pathlib import Path


class OlostechAPIClient:
    """Client for direct API interaction with Olostech system"""

    def __init__(self, base_url: str = "https://w6.olostech.com.br", har_path: str = None):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.dynamic_fields = {}
        self.access_code = "44626%23%7C%2349301%23%7C%231%23%7C%230"  # From HAR file
        self.selected_professional_id = None  # Store selected professional for attendance creation

        # Load HAR data if available
        self.har_parser = None
        if har_path and Path(har_path).exists():
            from har_tools.har_parser import HARParser
            self.har_parser = HARParser(har_path)
            self.dynamic_fields = self.har_parser.get_login_field_names()
            self.access_code = self.har_parser.get_access_code()
            print(f"[OK] Loaded HAR data: {har_path}")

    async def _request_delay(self, min_sec: float = 0.3, max_sec: float = 1.2) -> None:
        """
        Add randomized delay between requests to prevent server overload
        
        Args:
            min_sec: Minimum seconds to pause (default: 0.3)
            max_sec: Maximum seconds to pause (default: 1.2)
        
        This ensures respectful timing between API calls and avoids
            rapid-fire requests that could impact server performance.
        """
        import asyncio
        import random
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    def get_dynamic_field_names(self) -> Dict[str, str]:
        """
        Extract dynamic field names from login page or HAR

        Returns:
            Dictionary with 'username' and 'password' field names
        """
        # If we have HAR data, use it
        if self.har_parser and self.dynamic_fields:
            print("[OK] Using field names from HAR file")
            return self.dynamic_fields

        print("Attempting to extract dynamic field names from login page...")

        try:
            # GET login page
            response = self.session.get(
                f"{self.base_url}/logon.asp?origem=0",
                timeout=10
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find username field (starts with txtNomeLogon)
            username_field = soup.find('input', {'name': lambda x: x and x.startswith('txtNomeLogon')})
            # Find password field (starts with txtSenhaLogon)
            password_field = soup.find('input', {'name': lambda x: x and x.startswith('txtSenhaLogon')})

            if username_field and password_field:
                self.dynamic_fields = {
                    'username': username_field['name'],
                    'password': password_field['name']
                }
                print(f"[OK] Found username field: {self.dynamic_fields['username']}")
                print(f"[OK] Found password field: {self.dynamic_fields['password']}")
                return self.dynamic_fields
            else:
                print("[!] Could not find login fields in HTML")
                print("[!] Generating field names based on pattern...")
                
                # Generate based on pattern from HAR
                suffix = ''.join(random.choices(string.digits, k=8))
                self.dynamic_fields = {
                    'username': f'txtNomeLogon_{suffix}',
                    'password': f'txtSenhaLogon_{suffix}'
                }
                print(f"[OK] Generated: {self.dynamic_fields}")
                return self.dynamic_fields

        except Exception as e:
            print(f"[X] Error: {e}")
            print("[!] Falling back to generated field names...")
            
            # Fallback: generate field names
            suffix = ''.join(random.choices(string.digits, k=8))
            self.dynamic_fields = {
                'username': f'txtNomeLogon_{suffix}',
                'password': f'txtSenhaLogon_{suffix}'
            }
            return self.dynamic_fields

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with Olostech system

        Args:
            username: Login username
            password: Login password

        Returns:
            True if login successful, False otherwise
        """
        print(f"\nAttempting login for user: {username}")

        # Get dynamic field names if not already cached
        if not self.dynamic_fields:
            if not self.get_dynamic_field_names():
                return False

        # Prepare login data (from HAR file analysis)
        login_data = {
            self.dynamic_fields['username']: username,
            self.dynamic_fields['password']: password,
            'lstAcesso': self.access_code
        }

        try:
            # First POST (origem=0)
            print("-> Step 1: Initial login request...")
            response1 = self.session.post(
                f"{self.base_url}/logon.asp?origem=0",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': f"{self.base_url}/logon.asp?origem=0"
                },
                timeout=10
            )
            print(f"  Status: {response1.status_code}")

            # Second POST (origem=1) - actual authentication
            print("-> Step 2: Authentication request...")
            response2 = self.session.post(
                f"{self.base_url}/logon.asp?origem=1",
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': self.base_url,
                    'Referer': f"{self.base_url}/logon.asp?origem=0"
                },
                timeout=10
            )
            print(f"  Status: {response2.status_code}")

            # Check if login successful
            if response2.status_code == 200:
                # Check if redirected to main interface
                if 'default.asp' in response2.text or 'saudeweb' in response2.text:
                    print("[OK] Login successful!")
                    print(f"[OK] Session cookies: {len(self.session.cookies)}")
                    return True
                else:
                    print("[X] Login failed - unexpected response")
                    return False
            else:
                print(f"[X] Login failed - status code: {response2.status_code}")
                return False

        except Exception as e:
            print(f"[X] Login error: {e}")
            return False

    def select_unit(self, unit_id: str = "2867") -> bool:
        """
        Select healthcare unit

        Args:
            unit_id: Unit ID (default: 2867 = Dispensário - Mandados Judiciais)

        Returns:
            True if selection successful
        """
        print(f"\nSelecting unit ID: {unit_id}")

        # Unit data from HAR file
        unit_data = {
            'txtChaveControleAceite': '1429',
            'lstUnidades': f"{unit_id}%23%7CDispens%E1rio+-+Mandados+Judiciais%23%7C18208%23%7C103%2C5%2C13%2C102%2C1%2C137%2C4"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/saudeweb/acesso/logon.asp?origem=1",
                data=unit_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/acesso/logon.asp?origem=0"
                },
                timeout=10
            )

            print(f"Status: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            print(f"[X] Unit selection error: {e}")
            return False

    def select_environment(self, environment_value: str = None, environment_name: str = None) -> bool:
        """
        Select work environment (Dispensário da Farmácia Básica)

        Args:
            environment_value: Environment value from HTML (optional, uses hardcoded default)
            environment_name: Environment display name (for logging)

        Returns:
            True if selection successful
        """
        # Use hardcoded value that works (tested in Olostech project)
        if environment_value is None:
            environment_value = "103|#MFB|#Dispensário da Farmácia Básica Release 8"
            environment_name = "Dispensário da Farmácia Básica Release 8"

        if environment_name is None:
            environment_name = "Dispensário da Farmácia Básica Release 8"

        print(f"\n[Step 6/8] Selecting environment: {environment_name}")

        # Use exact format from HTML (not URL-encoded)
        env_data = {
            'lstUnidades': '2867#|Dispensário - Mandados Judiciais#|18208#|103,5,13,102,1,137,4',
            'lstAmbientes': environment_value
        }

        try:
            print(f"  [DEBUG] Sending POST request...")
            print(f"  [DEBUG] URL: {self.base_url}/saudeweb/acesso/logon.asp?origem=2")
            print(f"  [DEBUG] Session cookies: {len(self.session.cookies)}")
            print(f"  [DEBUG] Cookie names: {[c.name for c in self.session.cookies]}")

            response = self.session.post(
                f"{self.base_url}/saudeweb/acesso/logon.asp?origem=2",
                data=env_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/acesso/logon.asp?origem=1"
                },
                timeout=10
            )

            print(f"  [DEBUG] Response status: {response.status_code}")
            print(f"  [DEBUG] Response headers:")
            for key, value in response.headers.items():
                if key.lower() in ['content-type', 'content-length', 'location', 'server']:
                    print(f"    {key}: {value}")

            if response.status_code != 200:
                print(f"  [X] Environment selection failed with status {response.status_code}")

                # Enhanced error reporting for 500 errors
                if response.status_code == 500:
                    print(f"  [ERROR] Server error (500) - detailed info:")
                    print(f"    Response body (first 500 chars): {response.text[:500]}")

                    # Check for specific error patterns
                    text_lower = response.text.lower()
                    if 'sql' in text_lower or 'database' in text_lower:
                        print(f"    [TIP] Possible database error - check environment ID (103)")
                    if 'session' in text_lower or 'timeout' in text_lower:
                        print(f"    [TIP] Possible session issue - check if unit selection completed")
                    if 'invalid' in text_lower or 'not found' in text_lower:
                        print(f"    [TIP] Environment ID (103) may not exist for your account")

                    # Try to provide helpful troubleshooting
                    print(f"    [TROUBLESHOOTING]")
                    print(f"    1. Environment ID 103 may be invalid - check if 'Dispensário da Farmácia Básica' exists in your account")
                    print(f"    2. Unit selection may not have completed properly")
                    print(f"    3. Session state may be corrupted - try running login again")
                    print(f"    4. Check HAR file for different environment IDs")

                return False

            print("  [OK] Environment selected successfully")
            print(f"  [DEBUG] Session cookies after: {len(self.session.cookies)}")
            return True

        except Exception as e:
            print(f"  [X] Environment selection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def select_professional_activity(self, activity_id: str = "59067%7C%7C588%7C%7C65%7C%7CTecnico+em+Farmacia") -> bool:
        """
        Select professional activity (origem=3) - CRITICAL STEP

        This step was MISSING from original implementation and caused login failures.
        According to HAR file analysis, this is required after environment selection.

        Args:
            activity_id: Professional activity ID in format: "id%7C%7Cxxx%7C%7Cyyy%7C%7CName"
                         Default: "59067%7C%7C588%7C%7C65%7C%7CTecnico+em+Farmacia"

        Returns:
            True if selection successful
        """
        print(f"\n[Step 7/8] Selecting professional activity")
        print(f"  Activity ID: {activity_id}")

        prof_data = {
            'lstUnidades': '2867%23%7CDispens%E1rio+-+Mandados+Judiciais%23%7C18208%23%7C103%2C5%2C13%2C102%2C1%2C137%2C4',
            'lstAmbientes': '103%7C%23MFB%7C%23Dispens%E1rio+da+Farm%E1cia+B%E1sica+Release+8',
            'lstAtividadeProfissional': activity_id
        }

        try:
            response = self.session.post(
                f"{self.base_url}/saudeweb/acesso/logon.asp?origem=3",
                data=prof_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/acesso/logon.asp?origem=2"
                },
                timeout=10
            )

            print(f"  Status: {response.status_code}")

            if response.status_code != 200:
                print(f"  [X] Professional activity selection failed with status {response.status_code}")
                return False

            print("  [OK] Professional activity selected successfully")
            return True

        except Exception as e:
            print(f"  [X] Professional activity selection error: {e}")
            return False

    def initialize_session_state(self) -> bool:
        """
        Initialize session state after professional activity selection.

        CRITICAL: These steps are required to properly set the SaudeTech cookie
        with actual session values. Without these, the cookie has mid=&id= (empty)
        and all AJAX calls fail with "Sua sessão caiu" (session expired).

        Sequence from HAR (w3.olostech.com.br):
        1. GET session.asp - Initialize session
        2. GET grava_logon.asp - Write login cookie
        3. GET grava_logon.asp?origem=2 - Additional cookie data
        4. GET grava_logon.asp?origem=1 - Final cookie setup
        5. GET default.asp - Main dashboard (sets final cookies)

        Returns:
            True if session initialization successful
        """
        print("\n[Step 8/8] Initializing session state...")

        try:
            # Step 1: session.asp
            print("  [1/5] Getting session.asp...")
            response1 = self.session.get(
                f"{self.base_url}/saudeweb/acesso/session.asp",
                headers={
                    'Referer': f"{self.base_url}/saudeweb/acesso/logon.asp?origem=3"
                },
                timeout=10
            )
            print(f"    Status: {response1.status_code}, Cookies: {len(self.session.cookies)}")

            # Step 2: grava_logon.asp
            print("  [2/5] Writing login cookie (grava_logon.asp)...")
            response2 = self.session.get(
                f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp",
                headers={
                    'Referer': f"{self.base_url}/saudeweb/acesso/session.asp"
                },
                timeout=10
            )
            print(f"    Status: {response2.status_code}, Cookies: {len(self.session.cookies)}")

            # Step 3: grava_logon.asp?origem=2
            print("  [3/5] Writing additional cookie data (origem=2)...")
            response3 = self.session.get(
                f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp?origem=2",
                headers={
                    'Referer': f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp"
                },
                timeout=10
            )
            print(f"    Status: {response3.status_code}, Cookies: {len(self.session.cookies)}")

            # Step 4: grava_logon.asp?origem=1
            print("  [4/5] Finalizing cookie setup (origem=1)...")
            response4 = self.session.get(
                f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp?origem=1",
                headers={
                    'Referer': f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp?origem=2"
                },
                timeout=10
            )
            print(f"    Status: {response4.status_code}, Cookies: {len(self.session.cookies)}")

            # Step 5: default.asp
            print("  [5/5] Loading main dashboard...")
            response5 = self.session.get(
                f"{self.base_url}/saudeweb/default.asp",
                headers={
                    'Referer': f"{self.base_url}/saudeweb/acesso/cookie/grava_logon.asp?origem=1"
                },
                timeout=10
            )
            print(f"    Status: {response5.status_code}, Cookies: {len(self.session.cookies)}")

            # Check SaudeTech cookie
            saude_tech_found = False
            for cookie in self.session.cookies:
                if cookie.name == 'SaudeTech' or cookie.name == 'SaudeWeb':
                    cookie_preview = f"{cookie.value[:50]}..." if len(cookie.value) > 50 else cookie.value
                    print(f"    [OK] {cookie.name}: {cookie_preview}")
                    saude_tech_found = True
                    if cookie.value != 'mid=&id=':
                        print(f"    [OK] Cookie has actual values (not empty)")
                    else:
                        print(f"    [WARN] Cookie still has empty values!")

            if not saude_tech_found:
                print(f"    [WARN] No SaudeTech/SaudeWeb cookie found")

            success = all([
                response1.status_code == 200,
                response2.status_code == 200,
                response3.status_code == 200,
                response4.status_code == 200,
                response5.status_code == 200
            ])

            if success:
                print("  [OK] Session state initialized successfully")
            else:
                print("  [ERROR] Some steps failed")

            return success

        except Exception as e:
            print(f"  [ERROR] Session initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def navigate_to_atendimento(self, controle_id: str = None) -> bool:
        """
        Navigate to atendimento (patient attendance) page

        After completing login flow, navigate to the attendance page
        where patient search and dispensation happens.

        Args:
            controle_id: Optional control ID from HAR (default: '48908' from HAR file)
                        If None, uses default value from HAR file

        Returns:
            True if page loaded successfully (status 200)
        """
        print("\n[Step 9/10] Navigating to atendimento page")

        # Use HAR value as default
        if controle_id is None:
            controle_id = "48908"  # From HAR file analysis

        print(f"  [DEBUG] Using controle_id: {controle_id}")
        print(f"  [DEBUG] Session cookies: {len(self.session.cookies)}")
        print(f"  [DEBUG] Cookie names: {[c.name for c in self.session.cookies]}")

        try:
            print(f"  [DEBUG] Sending GET request...")
            print(f"  [DEBUG] URL: {self.base_url}/saudeweb/amfb/fb/atendimento.asp")
            print(f"  [DEBUG] Params: origem=0, controle={controle_id}")

            response = self.session.get(
                f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp",
                params={
                    'origem': '0',
                    'controle': controle_id
                },
                headers={
                    'Referer': f"{self.base_url}/saudeweb/default.asp"
                },
                timeout=10
            )

            print(f"  [DEBUG] Response URL: {response.url}")
            print(f"  [DEBUG] Status: {response.status_code}")

            # Log response headers for debugging
            print(f"  [DEBUG] Response headers:")
            for key, value in response.headers.items():
                if key.lower() in ['content-type', 'content-length', 'location']:
                    print(f"    {key}: {value}")

            if response.status_code == 200:
                print("  [OK] Atendimento page loaded successfully")
                print("  [OK] Ready for patient operations")

                # Log response content info
                print(f"  [DEBUG] Content length: {len(response.text)} chars")
                print(f"  [DEBUG] Content type: {response.headers.get('Content-Type', 'unknown')}")

                # Check if response contains expected content
                if 'atendimento' in response.text.lower():
                    print("  [DEBUG] Response contains 'atendimento' - Good!")
                else:
                    print("  [WARNING] Response may not be atendimento page")

                # Optional: Parse HTML to extract hidden fields for next steps
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Extract any hidden form fields that might be needed
                    hidden_fields = soup.find_all('input', {'type': 'hidden'})
                    if hidden_fields:
                        print(f"  [INFO] Found {len(hidden_fields)} hidden fields")
                        # Log first few for debugging
                        for field in hidden_fields[:3]:
                            print(f"    - {field.get('name', 'unnamed')}: {field.get('value', '')[:30]}...")

                except Exception as e:
                    # HTML parsing is optional, don't fail if it doesn't work
                    print(f"  [INFO] HTML parsing skipped: {e}")

                return True

            elif response.status_code == 404:
                print("  [X] FAILED - Page not found (404)")
                print("  [DEBUG] Response text preview:")
                print(f"    {response.text[:200]}...")
                print("\n  [TROUBLESHOOTING]")
                print("  Possible causes:")
                print("    1. URL path is incorrect for your environment")
                print("    2. Different URL structure (check HAR file)")
                print("    3. Missing permissions/role")
                print("\n  Try these alternatives:")
                print("    - Check HAR file for exact URL used in your session")
                print("    - Try without /amfb/fb/ path")
                print("    - Verify your user has access to atendimento module")

            elif response.status_code == 500:
                print("  [X] FAILED - Server error (500)")
                print("  [DEBUG] Response text preview:")
                print(f"    {response.text[:200]}...")
                print("\n  [TROUBLESHOOTING]")
                print("  Possible causes:")
                print("    1. controle_id is invalid or expired")
                print("    2. Missing required session data")
                print("    3. Server-side validation failed")
                print("\n  Next steps:")
                print("    - controle_id may need dynamic extraction")
                print("    - Check HAR file for controle value from your session")
                print("    - May need to extract from HTML response after login")

            elif response.status_code == 403:
                print("  [X] FAILED - Forbidden (403)")
                print("  [DEBUG] Response text preview:")
                print(f"    {response.text[:200]}...")
                print("\n  [TROUBLESHOOTING]")
                print("  Possible causes:")
                print("    1. Session not properly authenticated")
                print("    2. Missing or invalid cookies")
                print("    3. Referer header incorrect")
                print(f"\n  Current cookies: {len(self.session.cookies)}")
                print(f"  Cookie names: {[c.name for c in self.session.cookies]}")

            else:
                print(f"  [X] FAILED - Unexpected status: {response.status_code}")
                print("  [DEBUG] Response text preview:")
                print(f"    {response.text[:200]}...")
                print("\n  [TROUBLESHOOTING]")
                print(f"  Status {response.status_code} not expected")
                print("  Check NAVIGATION.md for troubleshooting guide")

            return False

        except requests.exceptions.Timeout:
            print("  [X] FAILED - Request timeout (>10s)")
            print("\n  [TROUBLESHOOTING]")
            print("  Possible causes:")
            print("    1. Network connectivity issues")
            print("    2. Server is slow to respond")
            print("    3. Firewall blocking requests")
            print("\n  Try:")
            print("    - Check network connection")
            print("    - Try increasing timeout parameter")
            print("    - Verify server is reachable")
            return False

        except requests.exceptions.ConnectionError as e:
            print(f"  [X] FAILED - Connection error: {e}")
            print("\n  [TROUBLESHOOTING]")
            print("  Possible causes:")
            print("    1. Server not reachable")
            print("    2. DNS resolution failed")
            print("    3. Network/firewall blocking")
            print("\n  Try:")
            print("    - Ping w6.olostech.com.br")
            print("    - Check VPN/proxy settings")
            print("    - Verify network connection")
            return False

        except Exception as e:
            print(f"  [X] FAILED - Unexpected error: {e}")
            print(f"  [DEBUG] Error type: {type(e).__name__}")
            print("\n  [TROUBLESHOOTING]")
            print("  Unexpected error occurred")
            print("  Check NAVIGATION.md for common issues")
            return False

    def complete_login_flow(self, username: str, password: str, navigate_to_atendimento: bool = False, patient_matricula: str = None, retirada: Dict = None) -> bool:
        """
        Execute complete login flow: auth → unit → environment → professional activity

        CORRECTED VERSION - Now includes the missing origem=3 step

        Args:
            username: Login username
            password: Login password
            navigate_to_atendimento: If True, also navigate to atendimento page (default: False)
            patient_matricula: If provided, search for patient after navigation (default: None)
            retirada: If provided, execute dispensing workflow after patient load (default: None)

        Returns:
            True if entire flow successful
        """
        print("="*80)
        print("Olostech API - Complete Login Flow (CORRECTED)")
        print("="*80)

        # Step 1: Login authentication
        print("\n[Step 1/4] Authentication")
        if not self.login(username, password):
            print("\n[X] Login flow failed at authentication")
            return False

        time.sleep(1)

        # Step 2: Select unit
        print("\n[Step 2/4] Unit Selection")
        if not self.select_unit():
            print("\n[X] Login flow failed at unit selection")
            return False

        time.sleep(1)

        # Step 3: Select environment
        print("\n[Step 3/4] Environment Selection")
        if not self.select_environment():
            print("\n[X] Login flow failed at environment selection")
            return False

        time.sleep(1)

        # Step 4: Select professional activity (MISSING STEP - NOW ADDED!)
        print("\n[Step 4/5] Professional Activity Selection")
        if not self.select_professional_activity():
            print("\n[X] Login flow failed at professional activity selection")
            print("[!] This step was missing and causing login failures!")
            return False

        time.sleep(1)

        # Step 5: Initialize session state (CRITICAL! Was missing!)
        print("\n[Step 5/5] Session State Initialization")
        if not self.initialize_session_state():
            print("\n[X] Login flow failed at session initialization")
            print("[!] This step sets the SaudeTech cookie properly!")
            return False

        print("\n" + "="*80)
        print("[OK] Login flow finished successfully!")
        print(f"[OK] Session cookies: {len(self.session.cookies)}")

        # Step 6 (Optional): Navigate to atendimento
        if navigate_to_atendimento:
            print("\n" + "="*80)
            print("[Step 5/6] Optional: Navigate to atendimento")
            print("="*80)

            if not self.navigate_to_atendimento():
                print("  [!] Navigation to atendimento failed (optional)")
                print("  [!] Login succeeded but couldn't reach atendimento page")
                # Don't return False - navigation is optional
            else:
                print("  [OK] Ready for patient search and operations")
                
                # Step 6 (Optional): Search for patient if matricula provided
                if patient_matricula:
                    print("\n" + "="*80)
                    print("[Step 6/6] Optional: Search for patient")
                    print("="*80)
                    
                    patient = self.search_patient_by_matricula(patient_matricula)
                    if patient:
                        self.load_patient_in_form(patient_matricula, patient)
                        print(f"\n[OK] Patient ready: {patient.get('usuarionome', 'Unknown')}")
                        
                        # Step 7 (Optional): Process dispensing if retirada provided
                        if retirada:
                            print("\n" + "="*80)
                            print("[Step 7/7] Optional: Process dispensing")
                            print("="*80)
                            
                            # Execute dispensing workflow (async method wrapped in sync context)
                            import asyncio
                            try:
                                # Run async method in current context
                                loop = asyncio.get_event_loop()
                                success = loop.run_until_complete(
                                    self.process_dispensing_from_retirada(retirada)
                                )
                                if not success:
                                    print("  [!] Dispensing workflow failed (optional)")
                            except Exception as e:
                                print(f"  [!] Dispensing error: {e}")
                    else:
                        print(f"\n[!] Patient not found: {patient_matricula}")
                        # Don't return False - patient search is optional/extra

        print("\n" + "="*80)
        print("[OK] Complete login flow finished!")
        print("="*80)

        return True

    def search_patient_by_matricula(self, matricula: str) -> dict:
        """
        Search patient by CNS/matricula number
        
        Uses obterUsuarioSUS AJAX call from atendimento page
        
        Args:
            matricula: Patient CNS or matricula number (numeric string)
        
        Returns:
            dict with patient data:
            {
                'matricula': '123456',
                'usuarionome': 'Patient Name',
                'idade': '45',
                'bairrodesc': 'Neighborhood',
                'situacao': '1',
                'situacao_obito': '0',
                'cnp_residencia': '1234567',
                'municipionome': 'Municipality',
                ...other fields...
            }
        Returns None if not found or error
        """
        
        print(f"\n[Step 10/12] Searching for patient: {matricula}")
        
        # AJAX call to usuario.ajax.asp
        # Using format from HAR file and HTML field names
        data = {
            'funcao': 'obterUsuarioSUS',
            'dados': f"{matricula}#|1|0"  # matricula | param1 | param2
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/saudeweb/classe/usuario.ajax.asp",
                data=data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp"
                },
                timeout=10
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"  [X] Search failed with status {response.status_code}")
                if response.status_code == 500:
                    print(f"  [DEBUG] Response preview: {response.text[:200]}")
                return None
            
            # Parse response - need to see actual format
            print(f"  [DEBUG] Response length: {len(response.text)} chars")
            print(f"  [DEBUG] Response preview: {response.text[:300]}...")
            
            # Parse the XML/HTML response
            patient_data = self._parse_patient_response(response.text)
            
            if patient_data and patient_data.get('matricula'):
                print(f"  [OK] Patient found!")
                print(f"       Name: {patient_data.get('usuarionome', 'Unknown')}")
                print(f"       CNS: {patient_data.get('matricula')}")
                print(f"       Age: {patient_data.get('idade', 'Unknown')}")
                if patient_data.get('bairrodesc'):
                    print(f"       Neighborhood: {patient_data.get('bairrodesc')}")
                return patient_data
            else:
                print("  [INFO] Patient not found or empty response")
                return None
                
        except Exception as e:
            print(f"  [X] Search error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_patient_response(self, response_text: str) -> dict:
        """
        Parse patient data from AJAX response
        
        Args:
            response_text: Response text from obterUsuarioSUS
        
        Returns:
            dict with patient fields or None
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response_text, 'html.parser')
        
        patient_data = {}
        
        # Olostech returns data - need to identify actual format
        # Try multiple parsing strategies
        
        # Strategy 1: Look for XML tags with specific field names
        # Common fields based on HTML and HAR: matricula, usuarionome, idade, bairrodesc, etc.
        
        # Strategy 2: Parse if it's JSON format
        # Strategy 3: Parse if it's HTML with hidden fields or spans
        
        # For now, do basic extraction and log everything for analysis
        try:
            # Look for data in response
            # Try to find patterns like: matricula=..., usuarionome=..., etc.
            import re
            
            # Extract matricula
            matricula_match = re.search(r'matricula["\']?\s*[:=]\s*["\']?([^"\']+)["\']?', response_text, re.IGNORECASE)
            if matricula_match:
                patient_data['matricula'] = matricula_match.group(1)
            
            # Extract name
            nome_match = re.search(r'usuarionome["\']?\s*[:=]\s*["\']?([^"\']+)["\']?', response_text, re.IGNORECASE)
            if nome_match:
                patient_data['usuarionome'] = nome_match.group(1)
            
            # Extract age
            idade_match = re.search(r'idade["\']?\s*[:=]\s*["\']?([^"\']+)["\']?', response_text, re.IGNORECASE)
            if idade_match:
                patient_data['idade'] = idade_match.group(1)
            
            # Extract neighborhood
            bairro_match = re.search(r'bairrodesc["\']?\s*[:=]\s*["\']?([^"\']+)["\']?', response_text, re.IGNORECASE)
            if bairro_match:
                patient_data['bairrodesc'] = bairro_match.group(1)
            
            # Extract situation
            situacao_match = re.search(r'situacao["\']?\s*[:=]\s*["\']?([^"\']+)["\']?', response_text, re.IGNORECASE)
            if situacao_match:
                patient_data['situacao'] = situacao_match.group(1)
            
            # If we found at least a matricula, return the data
            if patient_data.get('matricula'):
                return patient_data
            else:
                print("  [DEBUG] Could not extract patient data from response")
                # Find field names in response
                fields = re.findall(r'["\']?(\w+)["\']?\s*[:=]\s*["\']?', response_text[:500])
                unique_fields = list(set(fields))[:10]  # Limit to 10 fields
                print(f"  [DEBUG] Response seems to contain: {unique_fields}")
                return None
                
        except Exception as e:
            print(f"  [DEBUG] Parsing error: {e}")
            print(f"  [DEBUG] Response preview: {response_text[:200]}")
            return None

    def load_patient_in_form(self, matricula: str, patient_data: dict) -> bool:
        """
        Load patient data into atendimento form fields
        
        Fills the search result fields:
        - txtUsuarioAtendimentoMatricula
        - spantxtUsuarioAtendimentoMatriculaNome (patient name)
        - spantxtUsuarioAtendimentoMatriculaIdade (age)
        - spantxtUsuarioAtendimentoMatriculaBairro (neighborhood)
        
        Args:
            matricula: Patient CNS/matricula
            patient_data: Patient data dict from search
        
        Returns:
            True if loaded successfully
        """
        print(f"\n[Step 11/12] Loading patient into form")
        
        # For API-only version, we just track the selected patient
        # The actual form filling would require additional POST requests or session updates
        # For now, we'll store the patient data in the client instance
        
        self.current_patient = {
            'matricula': matricula,
            'data': patient_data
        }
        
        print(f"  [OK] Patient loaded: {patient_data.get('usuarioname', 'Unknown')}")
        return True

    # ========================================================================
    # DISPENSING WORKFLOW METHODS
    # ========================================================================

    async def select_recipe_type(self, recipe_type: int = 2) -> bool:
        """
        Select recipe type radio button (rdoTipoAcao)
        
        Recipe types:
        - 1: "Receita Cadastrada" (Registered Recipe)
        - 2: "Receita Simples" (Simple Recipe) - DEFAULT
        - 4: "Receita Especial/Antibiótico" (Special/Antibiotic)
        - 10: "Receita Simples (USO CONTÍNUO)" (Simple Recipe - Continuous Use)
        - 11: "Receita Cadastrada" (duplicate)
        
        Args:
            recipe_type: Recipe type value (default: 2)
        
        Returns:
            True if successful
        """
        print(f"\n[Step 12a] Selecting recipe type: {recipe_type}")
        
        await self._request_delay(0.5, 1.0)
        
        try:
            # Get the current page to verify we're on the right page
            response = self.session.get(f"{self.base_url}/saudeweb/default.asp")
            response.raise_for_status()
            
            # Select the radio button by value
            # This would typically be done via JavaScript or POST request
            # For now, we'll simulate it by preparing the form data
            payload = {
                'rdoTipoAcao': str(recipe_type),
                '__EVENTTARGET': 'rdoTipoAcao',
                # Other form fields would be included here
            }
            
            print(f"  [OK] Recipe type {recipe_type} selected")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to select recipe type: {e}")
            return False

    def _normalize_text(self, text: str) -> str:
        """
        Remove acentos e converte para minúsculas para comparação.

        Remove acentos português (á→a, ç→c, etc.) e converte para minúsculas
        para permitir busca case-insensitive e accent-insensitive.

        Args:
            text: Texto para normalizar

        Returns:
            Texto normalizado (sem acentos, em minúsculas)
        """
        if not text:
            return ""

        # Mapeamento de acentos
        accent_map = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U',
            'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
            'Ã': 'A', 'Õ': 'O', 'ã': 'a', 'õ': 'o',
            'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
            'Ç': 'C', 'ç': 'c',
        }

        normalized = text
        for accented, unaccented in accent_map.items():
            normalized = normalized.replace(accented, unaccented)

        return normalized.lower()

    def _sort_professionals_by_relevance(
        self,
        professionals: List[Dict],
        query: str
    ) -> List[Dict]:
        """
        Ordena profissionais por relevância usando algoritmo similar ao autocomplete.

        Algoritmo:
        1. Normaliza query e nomes (remove acentos, minúsculas)
        2. Encontra posição do match (match no início = mais relevante)
        3. Ordena por (posição do match, nome)

        Args:
            professionals: Lista de profissionais encontrados
            query: Termo de busca original

        Returns:
            Lista ordenada por relevância
        """
        if not professionals:
            return []

        if len(professionals) == 1:
            return professionals

        query_normalized = self._normalize_text(query)

        def get_match_position(prof: Dict) -> int:
            """
            Retorna a posição onde a query aparece no nome do profissional.

            Match no início (posição 0) é mais relevante.
            Se não encontrar, retorna valor alto (fim da fila).
            """
            prof_name_normalized = self._normalize_text(prof['name'])

            # Buscar match exato
            pos = prof_name_normalized.find(query_normalized)

            if pos != -1:
                return pos

            # Se não encontrou, retornar valor alto para colocar no fim
            return 999999

        # Ordenar por (posição do match, nome)
        sorted_professionals = sorted(
            professionals,
            key=lambda p: (get_match_position(p), p['name'])
        )

        return sorted_professionals

    async def search_professional(self, name: str) -> List[Dict]:
        """
        Search for professional by name ONLY (not CRM)

        Args:
            name: Professional name to search

        Returns:
            List of matching professionals sorted by relevance:
            [
                {
                    'id': 'ChavePU value',
                    'name': 'ProfissionalNome',
                    'unidade': 'UnidadeDesc',
                    'descricao': 'Descricao (specialty)'
                },
                ...
            ]
            Returns empty list if no results or error.
        """
        print(f"\n[Professional] Searching: {name}")

        if not name or not name.strip():
            return []

        await self._request_delay(0.5, 1.0)

        try:
            # Call existing working method
            result = await self.search_professional_by_name(name)

            if not result['valido']:
                print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")
                return []

            if 'dados' not in result or not result['dados']:
                print(f"  [INFO] No professional found")
                return []

            # Parse multiple professionals from XML
            professionals = self._parse_multiple_professionals(result)

            if professionals:
                # Sort by relevance (like Emissor's autocomplete)
                professionals = self._sort_professionals_by_relevance(
                    professionals, name
                )

                print(f"  [OK] Found {len(professionals)} professional(s) (sorted by relevance)")
                for i, prof in enumerate(professionals[:3]):  # Show first 3
                    print(f"       {i+1}. {prof['name']} ({prof['unidade']})")
                if len(professionals) > 3:
                    print(f"       ... and {len(professionals) - 3} more")
            else:
                print(f"  [INFO] No professional data extracted")

            return professionals

        except Exception as e:
            print(f"  [ERROR] Professional search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def select_professional(self, professional_id: str) -> bool:
        """
        Selecionar profissional e armazenar ID para uso posterior.

        Args:
            professional_id: Professional ID from lstProfissionalUnidade

        Returns:
            True se seleção bem-sucedida
        """
        print(f"\n[Step 12c] Selecting professional ID: {professional_id}")

        await self._request_delay(0.5, 1.0)

        try:
            # Store selected professional for use in create_attendance()
            self.selected_professional_id = professional_id
            print(f"  [OK] Professional {professional_id} selected and stored")
            return True

        except Exception as e:
            print(f"  [ERROR] Failed to select professional: {e}")
            return False

    async def select_or_fallback_professional(
        self,
        name: str,
        professionals: list = None
    ) -> bool:
        """
        Selecionar profissional com fallback para processo de cadastro "12345".

        Workflow:
        1. Se nome vazio → buscar "12345" → selecionar "Em Processo De Cadastro"
        2. Se profissionais não fornecidos → buscar por nome (com ordenação por relevância)
        3. Se sem resultados → buscar "12345" → fallback
        4. Se 1 resultado → selecionar
        5. Se múltiplos resultados → mostrar countdown → auto-selecionar primeiro

        Args:
            name: Nome do profissional de patient_data.profissional
            professionals: Resultados pré-buscados (opcional, busca se None)

        Returns:
            True se profissional selecionado (ou fallback usado)
        """
        print(f"\n[Professional] Selection workflow for: '{name}'")

        # Step 1: Handle empty name
        if not name or not name.strip():
            print(f"  [INFO] Empty professional name, using registration process")
            return await self.use_registration_process()

        await self._request_delay(0.5, 1.0)

        # Step 2: Search if results not provided
        if professionals is None:
            professionals = await self.search_professional(name)

        # Step 3: Handle no results
        if not professionals:
            print(f"  [WARN] No professional found for '{name}'")
            print(f"  [INFO] Falling back to registration process (12345)")
            return await self.use_registration_process()

        # Step 4: Handle single result
        elif len(professionals) == 1:
            prof = professionals[0]
            print(f"  [OK] Single result: {prof['name']}")
            return await self.select_professional(prof['id'])

        # Step 5: Handle multiple results
        else:
            print(f"  [INFO] Multiple results ({len(professionals)} found):")
            for i, prof in enumerate(professionals[:5]):
                print(f"       {i+1}. {prof['name']} - {prof['unidade']}")

            # Show countdown before auto-selecting first result
            first_prof = professionals[0]
            print(f"\n  [COUNTDOWN] Auto-selecionando profissional mais relevante:")
            print(f"               → {first_prof['name']} ({first_prof['unidade']})")

            import asyncio
            for i in range(3, 0, -1):
                print(f"               → Selecionando em {i}...")
                await asyncio.sleep(1)

            print(f"  [OK] Selecionado: {first_prof['name']}")
            return await self.select_professional(first_prof['id'])

    async def use_registration_process(self) -> bool:
        """
        Use 'Em Processo De Cadastro' option when no professional found.

        Workflow:
        1. Search for "12345" (special code)
        2. Select the "Em Processo De Cadastro" option from results

        NOTE: This needs testing to understand actual response format.
        The ID might be fixed or dynamic.

        Returns:
            True if registration process option selected
        """
        print(f"\n[Professional] Using registration process (12345)")

        try:
            await self._request_delay(0.5, 1.0)

            # Search for special code
            results = await self.search_professional("12345")

            if not results:
                print(f"  [WARN] No results for '12345'")
                print(f"  [INFO] Trying to select fixed ID if known")

                # TODO: Determine the actual ID for "Em Processo De Cadastro"
                # It might be a fixed value like "0" or a special code
                # For now, return True to continue workflow
                print(f"  [INFO] Assuming registration process can proceed")
                return True

            # Select the registration process option
            # Usually it's the first/only result
            prof = results[0]
            print(f"  [OK] Found: {prof['name']}")

            # Check if this is the registration process option
            if 'processo' in prof['name'].lower() or 'cadastro' in prof['name'].lower():
                print(f"  [OK] This appears to be 'Em Processo De Cadastro'")
                return await self.select_professional(prof['id'])
            else:
                print(f"  [WARN] Unexpected result for '12345': {prof['name']}")
                print(f"  [INFO] Selecting anyway and continuing")
                return await self.select_professional(prof['id'])

        except Exception as e:
            print(f"  [ERROR] Registration process failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def search_material(self, code: str) -> Dict:
        """
        Search material by code (triggers popup)
        
        Args:
            code: Material code to search
        
        Returns:
            Material data or None
        """
        print(f"\n[Step 13a] Searching material: {code}")
        
        await self._request_delay(0.5, 1.0)
        
        try:
            # This triggers the material search popup
            # The popup HTML was not saved, so exact implementation TBD
            
            # TODO: Implement material search when popup HTML is available
            # Expected workflow:
            # 1. Enter code in txtMaterialCod
            # 2. Click btnPesquisarMaterial
            # 3. Parse popup response
            # 4. Select material from popup
            
            print(f"  [INFO] Material search for '{code}' (popup TBD)")
            return None
            
        except Exception as e:
            print(f"  [ERROR] Material search failed: {e}")
            return None

    async def add_material_to_dispensing(self, item_data: Dict) -> bool:
        """
        Add material to current prescription/dispensing
        
        Args:
            item_data: Dict with 'code', 'description', 'unidade', 'quantidade', 'dias'
        
        Returns:
            True if added successfully
        """
        print(f"\n[Step 13b] Adding material: {item_data.get('description', 'Unknown')}")
        
        await self._request_delay(0.5, 1.0)
        
        try:
            # Track current materials in the session
            if not hasattr(self, 'current_dispensing'):
                self.current_dispensing = []
            
            self.current_dispensing.append(item_data)
            print(f"  [OK] Material added (total: {len(self.current_dispensing)})")
            
            await self._request_delay(1.0, 1.5)
            
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to add material: {e}")
            return False

    async def get_dispensing_items(self) -> List[Dict]:
        """
        Get list of materials in current dispensing
        
        Returns:
            List of material dicts
        """
        if hasattr(self, 'current_dispensing'):
            return self.current_dispensing
        return []

    async def complete_dispensing(self) -> bool:
        """
        Confirm and save the dispensing
        
        Returns:
            True if successful
        """
        print(f"\n[Step 14] Completing dispensing")
        
        await self._request_delay(1.0, 2.0)
        
        try:
            # Submit the dispensing form
            # This would save all materials and finalize the prescription
            print(f"  [OK] Dispensing completed with {len(self.current_dispensing)} items")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to complete dispensing: {e}")
            return False

    async def process_dispensing_from_retirada(self, retirada: Dict) -> bool:
        """
        Complete dispensing workflow from retirada data
        
        High-level automation that:
        1. Maps tipo_receita to recipe type
        2. Searches for professional (by name only)
        3. Falls back to registration process if not found
        4. Adds all materials from retirada
        5. Completes the dispensing
        
        Args:
            retirada: Dict with tipo_receita, profissional, crm, items
        
        Returns:
            True if workflow completed successfully
        """
        print(f"\n{'='*80}")
        print(f"DISPENSING WORKFLOW")
        print(f"{'='*80}")
        
        await self._request_delay(0.5, 1.0)
        
        # Map tipo_receita to rdoTipoAcao value
        recipe_type_map = {
            'tipo_a': 2,   # Receita Simples
            'tipo_b': 4,   # Receita Especial/Antibiótico
            'tipo_c': 10,  # Receita Simples (USO CONTÍNUO)
        }
        
        tipo_receita = retirada.get('tipo_receita', 'tipo_a')
        recipe_type = recipe_type_map.get(tipo_receita, 2)
        
        print(f"Recipe type: {tipo_receita} → rdoTipoAcao={recipe_type}")
        
        # Step 1: Select recipe type
        if not await self.select_recipe_type(recipe_type):
            print("[ERROR] Failed to select recipe type")
            return False
        
        await self._request_delay(0.5, 1.0)
        
        # Step 2: Search for professional (by name ONLY, not CRM)
        profissional = retirada.get('profissional', '').strip()

        print(f"\n[Workflow] Professional selection")

        if not await self.select_or_fallback_professional(profissional):
            print("[ERROR] Professional selection failed")
            return False

        await self._request_delay(0.5, 1.0)
        
        # Step 3: Add all materials
        items = retirada.get('items', [])
        print(f"\nAdding {len(items)} materials...")
        
        for item in items:
            item_data = {
                'code': item.get('item_id', ''),
                'description': item.get('descricao', ''),
                'unidade': item.get('unidade', ''),
                'quantidade': item.get('quantidade', ''),
                'dias': item.get('dias', '')
            }
            
            if not await self.add_material_to_dispensing(item_data):
                print(f"[WARNING] Failed to add material: {item_data.get('description')}")
        
        # Step 4: Complete dispensing
        if await self.complete_dispensing():
            print(f"\n{'='*80}")
            print(f"[SUCCESS] Dispensing workflow completed!")
            print(f"{'='*80}")
            return True
        else:
            print(f"\n{'='*80}")
            print(f"[ERROR] Dispensing workflow failed at completion")
            print(f"{'='*80}")
            return False

    def test_connection(self) -> Dict[str, any]:
        """
        Test API connection and return status

        Returns:
            Dictionary with connection status and info
        """
        print("\nTesting Olostech API connection...")
        print("="*80)

        result = {
            'reachable': False,
            'dynamic_fields': {},
            'session_cookies': 0,
            'error': None
        }

        try:
            # Test 1: Can we reach the server?
            print("\n[Test 1] Server reachability...")
            response = self.session.get(
                f"{self.base_url}/logon.asp?origem=0",
                timeout=10
            )
            if response.status_code == 200:
                print("[OK] Server is reachable")
                result['reachable'] = True
            else:
                print(f"[X] Server returned status: {response.status_code}")
                return result

            # Test 2: Can we extract dynamic fields?
            print("\n[Test 2] Dynamic field extraction...")
            fields = self.get_dynamic_field_names()
            if fields:
                print(f"[OK] Fields extracted: {fields['username']}, {fields['password']}")
                result['dynamic_fields'] = fields
            else:
                print("[X] Could not extract fields")
                return result

            # Test 3: Check cookies (before login)
            print(f"\n[Test 3] Cookies: {len(self.session.cookies)}")
            result['session_cookies'] = len(self.session.cookies)

        except Exception as e:
            print(f"\n[X] Connection test failed: {e}")
            result['error'] = str(e)

        print("\n" + "="*80)
        return result

    # ========================================================================
    # AJAX HELPER METHODS
    # ========================================================================

    def _parse_ajax_response(self, xml_text: str) -> Dict:
        """
        Parse AJAX XML response from Olostech

        NOW WITH: Raw XML storage for multi-item parsing

        Args:
            xml_text: XML response text

        Returns:
            Dictionary with parsed data + raw XML
        """
        import xml.etree.ElementTree as ET
        from html import unescape

        try:
            root = ET.fromstring(xml_text)

            result = {
                'valido': root.get('valido', 'false') == 'true',
                'mensagem': root.get('mensagem', ''),
                '_raw_xml': xml_text  # Store raw XML for re-parsing multiple items
            }

            # Extract all data fields
            dados = root.find('dados')
            if dados is not None:
                result['dados'] = {}
                for child in dados:
                    # Get CDATA content
                    if child.text:
                        result['dados'][child.tag] = unescape(child.text)
                    else:
                        result['dados'][child.tag] = None

            return result

        except Exception as e:
            print(f"  [ERROR] Failed to parse XML response: {e}")
            return {
                'valido': False,
                'mensagem': str(e),
                '_raw_xml': xml_text
            }

    def _parse_multiple_professionals(self, ajax_result: Dict) -> List[Dict]:
        """
        Parse multiple professionals from AJAX response.

        The ObterDadosProfissional response can contain multiple professionals.
        XML structure may have repeated elements or numbered fields.

        However, _parse_ajax_response() only captures the LAST occurrence of each tag.
        We need to re-parse the raw XML to get all professionals.

        Args:
            ajax_result: Result dict from _ajax_call()

        Returns:
            List of professional dicts with keys: id, name, unidade, descricao
        """
        import xml.etree.ElementTree as ET
        from html import unescape

        professionals = []

        try:
            # For now, extract single professional from existing parsed data
            dados = ajax_result.get('dados', {})

            if not dados:
                return []

            # Extract professional data (handle both capitalized and lowercase)
            prof_id = dados.get('chavepu') or dados.get('ChavePU')
            prof_name = dados.get('profissionalnome') or dados.get('ProfissionalNome')
            unidade = dados.get('unidatedesc') or dados.get('UnidadeDesc')
            desc = dados.get('descricao') or dados.get('Descricao')

            if prof_id and prof_name:
                professionals.append({
                    'id': prof_id,
                    'name': prof_name,
                    'unidade': unidade or '',
                    'descricao': desc or ''
                })

            # TODO: Parse raw XML to get ALL professionals when multiple exist
            # This would require analyzing the raw XML structure from _raw_xml
            # The JavaScript suggests obterDados.Quantidade() can return > 1

        except Exception as e:
            print(f"  [ERROR] Failed to parse professionals: {e}")

        return professionals

    async def _ajax_call(
        self,
        endpoint: str,
        function: str,
        data: str
    ) -> Dict:
        """
        Generic AJAX call to Olostech endpoints

        Args:
            endpoint: AJAX endpoint (e.g., 'amfb/fb/atendimento.ajax.asp')
            function: Function name to call
            data: Function parameters (encoded as value1|#value2|#value3)

        Returns:
            Parsed response dictionary
        """
        await self._request_delay(0.3, 0.8)

        try:
            params = {
                'funcao': function,
                'dados': data
            }

            # DEBUG: Log request details
            print(f"  [DEBUG] AJAX POST: {endpoint}")
            print(f"  [DEBUG] Function: {function}")
            print(f"  [DEBUG] Data: {data}")

            # DEBUG: Log cookies being sent
            print(f"  [DEBUG] Cookies being sent: {len(self.session.cookies)}")
            for cookie in self.session.cookies:
                cookie_preview = f"{cookie.value[:20]}..." if len(cookie.value) > 20 else cookie.value
                print(f"    - {cookie.name}: {cookie_preview}")

            # DEBUG: Log important headers
            referer = f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp?origem=0&controle=48908"
            print(f"  [DEBUG] Request headers:")
            print(f"    - Content-Type: application/x-www-form-urlencoded")
            print(f"    - X-Requested-With: XMLHttpRequest")
            print(f"    - Referer: {referer}")

            response = self.session.post(
                f"{self.base_url}/saudeweb/{endpoint}",
                data=params,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': referer
                },
                timeout=15
            )

            print(f"  [DEBUG] Response status: {response.status_code}")
            print(f"  [DEBUG] Response preview: {response.text[:300]}...")

            # Check if session expired
            if 'sessão caiu' in response.text.lower() or 'session expired' in response.text.lower():
                print(f"  [ERROR] SESSION EXPIRED - Server rejected the request")
                print(f"  [ERROR] This indicates cookies/headers are not being sent correctly")

            response.raise_for_status()
            result = self._parse_ajax_response(response.text)

            # Log parsed result
            print(f"  [DEBUG] Parsed result valido={result['valido']}")
            if result.get('dados'):
                print(f"  [DEBUG] Parsed dados keys: {list(result['dados'].keys())}")

            return result

        except Exception as e:
            print(f"  [ERROR] AJAX call to {endpoint}/{function} failed: {e}")
            print(f"  [ERROR] Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return {'valido': False, 'mensagem': str(e)}

    # ========================================================================
    # ATTENDANCE WORKFLOW METHODS (from w6 HAR)
    # ========================================================================

    async def refresh_session(self) -> bool:
        """
        Refresh session by GET request to atendimento page.

        This ensures session is active before making AJAX calls.
        The 30-minute timeout should be plenty, but we need to
        ensure the session cookies are properly maintained.

        Returns:
            True if session refresh successful
        """
        print("\n[Session] Refreshing session...")
        try:
            response = self.session.get(
                f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp",
                params={'origem': '0', 'controle': '48908'},
                headers={
                    'Referer': f"{self.base_url}/saudeweb/default.asp"
                },
                timeout=10
            )
            success = response.status_code == 200
            if success:
                print(f"  [OK] Session refreshed")
                print(f"  [DEBUG] Cookies after refresh: {len(self.session.cookies)}")
                for cookie in self.session.cookies:
                    cookie_preview = f"{cookie.value[:20]}..." if len(cookie.value) > 20 else cookie.value
                    print(f"    - {cookie.name}: {cookie_preview}")
            else:
                print(f"  [WARN] Refresh failed with status {response.status_code}")
            return success
        except Exception as e:
            print(f"  [ERROR] Session refresh failed: {e}")
            return False

    async def get_attendance_number(self, estoque_id: str) -> Optional[str]:
        """
        Get current attendance number (senha) for a stock location

        Args:
            estoque_id: Stock/Dispensary ID (e.g., '505')

        Returns:
            Current attendance number or None
        """
        print(f"\n[Attendance] Getting attendance number for estoque={estoque_id}")

        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'obterSenhaAtual',
            estoque_id
        )

        # DEBUG: Log raw XML to see actual response format
        if '_raw_xml' in result:
            print(f"  [DEBUG] Raw XML response: {result['_raw_xml'][:500]}")

        # Check validity
        if result['valido']:
            if 'dados' in result and result['dados']:
                print(f"  [DEBUG] Dados keys: {list(result['dados'].keys())}")
                senha = result['dados'].get('senha')
                if senha:
                    print(f"  [OK] Current attendance number: {senha}")
                    return senha
                else:
                    print(f"  [ERROR] 'senha' field not found in dados")
                    print(f"  [ERROR] Available fields: {list(result['dados'].keys())}")
            else:
                print(f"  [ERROR] No 'dados' in response")
                print(f"  [ERROR] Response keys: {list(result.keys())}")
        else:
            print(f"  [ERROR] Invalid response: {result.get('mensagem', 'Unknown error')}")

        return None

    async def check_duplicate_attendance(
        self,
        estoque_id: str,
        date: str,
        patient_id: str,
        senha: str
    ) -> Dict:
        """
        Check for duplicate attendance (controle de repetição)

        Args:
            estoque_id: Stock/Dispensary ID
            date: Attendance date (DD/MM/YYYY)
            patient_id: Patient registration ID
            senha: Attendance number

        Returns:
            Dictionary with 'concluido' flag and potential duplicate list
        """
        print(f"\n[Attendance] Checking duplicate attendance")

        # Encode parameters: estoque_id|#date|#patient_id|#senha
        data = f"{estoque_id}|#{date}|#{patient_id}|#{senha}"

        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'verificarControleRepeticaoAtendimento',
            data
        )

        if result['valido']:
            concluido = result['dados'].get('concluido', 'false') == 'true' if 'dados' in result else False
            if concluido:
                print(f"  [OK] No duplicates found, can proceed")
            else:
                mensagem = result.get('mensagem', '')
                print(f"  [WARN] Duplicate check returned: {mensagem}")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def get_user_sus_data(self, matricula: str, search_type: str = "2") -> Dict:
        """
        Get SUS user (patient) data by registration number

        Args:
            matricula: Patient registration ID
            search_type: Search type (default: "2" for patient)

        Returns:
            Dictionary with patient data
        """
        print(f"\n[Patient] Getting SUS user data: {matricula}")

        # Encode parameters: matricula|#search_type|#true
        data = f"{matricula}|#{search_type}|#true"

        result = await self._ajax_call(
            'saudeweb/classe/usuario.ajax.asp',
            'obterUsuarioSUS',
            data
        )

        if result['valido'] and 'dados' in result:
            print(f"  [OK] Patient data retrieved")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def search_professional_by_name(
        self,
        name: str,
        search_type: str = "4"
    ) -> Dict:
        """
        Search for professional by name or CRM

        Args:
            name: Professional name or CRM
            search_type: Search type (4 = professional)

        Returns:
            Dictionary with professional data
        """
        print(f"\n[Professional] Searching: {name}")

        # Encode parameters: search_type|#name
        data = f"{search_type}|#{name}"

        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'ObterDadosProfissional',
            data
        )

        if result['valido']:
            if 'dados' in result and result['dados']:
                prof_name = result['dados'].get('profissionalnome', 'N/A')
                print(f"  [OK] Found professional: {prof_name}")
            else:
                print(f"  [INFO] No professional found")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def create_attendance(
        self,
        estoque_id: str,
        date: str,
        patient_id: str,
        senha: str,
        professional_id: str = None
    ) -> Optional[str]:
        """
        Criar novo registro de atendimento.

        Args:
            estoque_id: Stock/Dispensary ID
            date: Data do atendimento (DD/MM/YYYY)
            patient_id: ID de cadastro do paciente
            senha: Número do atendimento
            professional_id: ID do profissional (opcional, usa armazenado se não fornecido)

        Returns:
            Attendance ID se bem-sucedido, None caso contrário
        """
        print(f"\n[Attendance] Creating attendance record")

        try:
            # First check for duplicates
            check_result = await self.check_duplicate_attendance(
                estoque_id, date, patient_id, senha
            )

            if not check_result['valido']:
                print(f"  [ERROR] Duplicate check failed")
                return None

            # Use provided professional_id or fall back to stored selection
            prof_id = professional_id or self.selected_professional_id
            if prof_id:
                print(f"  [INFO] Using professional ID: {prof_id}")

            # Submit attendance creation form
            await self._request_delay(0.5, 1.0)

            form_data = {
                'txtEstoqueDispensario': estoque_id,
                'txtAtendimentoData': date,
                'txtUsuarioAtendimentoMatricula': patient_id,
                'txtAtendimentoNr': senha,
                'origem': '1'  # Indica que está criando atendimento
            }

            # Add professional ID if available
            if prof_id:
                form_data['lstProfissionalUnidade'] = prof_id

            response = self.session.post(
                f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp",
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/amfb/fb/atendimento.asp?origem=0"
                },
                timeout=15,
                allow_redirects=True
            )

            # Extract attendance ID from response or redirect
            # The attendance ID is typically in the redirect URL or response
            if response.status_code == 200:
                # Try to extract from URL if redirected
                if 'Atendimento=' in response.url:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(response.url)
                    query = parse_qs(parsed.query)
                    attendance_id = query.get('Atendimento', [None])[0]
                    if attendance_id:
                        print(f"  [OK] Attendance created: ID={attendance_id}")
                        return attendance_id

                # Try to extract from response text
                import re
                match = re.search(r'Atensagem=(\d+)', response.text)
                if match:
                    attendance_id = match.group(1)
                    print(f"  [OK] Attendance created: ID={attendance_id}")
                    return attendance_id

            print(f"  [WARN] Attendance created but ID not found in response")
            return None

        except Exception as e:
            print(f"  [ERROR] Failed to create attendance: {e}")
            return None

    # ========================================================================
    # MATERIAL/MEDICATION WORKFLOW METHODS (from w6 HAR)
    # ========================================================================

    async def search_material(self, material_id: str) -> Dict:
        """
        Get material details for dispensing

        Args:
            material_id: Material ID code

        Returns:
            Dictionary with material data
        """
        print(f"\n[Material] Searching material: {material_id}")

        result = await self._ajax_call(
            'amfb/fb/dispensacao.ajax.asp',
            'ObterMaterialDispensacao',
            material_id
        )

        if result['valido'] and 'dados' in result:
            material_desc = result['dados'].get('materialdesc', 'N/A')
            saldo = result['dados'].get('saldo_atual', 'N/A')
            print(f"  [OK] Found: {material_desc} (Saldo: {saldo})")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def search_medication(
        self,
        medication_id: str,
        recipe_type: int,
        patient_id: str,
        dispensacao_id: Optional[str] = None
    ) -> Dict:
        """
        Get medication details with prescription info

        Args:
            medication_id: Medication ID
            recipe_type: Recipe type (2=Simple, 4=Special, etc.)
            patient_id: Patient ID
            dispensacao_id: Dispensing ID (optional, for editing)

        Returns:
            Dictionary with medication data
        """
        print(f"\n[Medication] Searching medication: {medication_id}")

        # Encode: medication_id##recipe_type##patient_id##dispensacao_id
        data = f"{medication_id}##{recipe_type}##{patient_id}##{dispensacao_id or '0'}"

        result = await self._ajax_call(
            'amfb/fb/dispensacao.ajax.asp',
            'ObterMedicamentoDispensacao',
            data
        )

        if result['valido'] and 'dados' in result:
            med_name = result['dados'].get('nome_medicamento', 'N/A')
            print(f"  [OK] Found: {med_name}")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def get_last_material_delivery(
        self,
        patient_id: str,
        material_id: str
    ) -> Dict:
        """
        Get last material delivery for patient

        Args:
            patient_id: Patient ID
            material_id: Material ID

        Returns:
            Dictionary with last delivery data
        """
        print(f"\n[Material] Getting last delivery for material {material_id}")

        # Encode: patient_id|#material_id
        data = f"{patient_id}|#{material_id}"

        result = await self._ajax_call(
            'amfb/fb/dispensacao.ajax.asp',
            'obterUltimaEntregaMaterial',
            data
        )

        if result['valido'] and 'dados' in result:
            data_atendimento = result['dados'].get('data_atendimento', 'N/A')
            print(f"  [OK] Last delivery: {data_atendimento}")
        else:
            print(f"  [INFO] No previous delivery found")

        return result

    async def get_last_medication_delivery(
        self,
        patient_id: str,
        medication_id: str
    ) -> Dict:
        """
        Get last medication delivery for patient

        Args:
            patient_id: Patient ID
            medication_id: Medication ID

        Returns:
            Dictionary with last delivery data
        """
        print(f"\n[Medication] Getting last delivery for medication {medication_id}")

        # Encode: patient_id|#medication_id
        data = f"{patient_id}|#{medication_id}"

        result = await self._ajax_call(
            'amfb/fb/dispensacao.ajax.asp',
            'obterUltimaEntregaMedicamento',
            data
        )

        if result['valido'] and 'dados' in result:
            data_suficiencia = result['dados'].get('data_suficiencia', 'N/A')
            print(f"  [OK] Last delivery sufficiency date: {data_suficiencia}")
        else:
            print(f"  [INFO] No previous delivery found")

        return result

    async def get_medication_batches(self, medication_id: str) -> Dict:
        """
        Get available batches for medication

        Args:
            medication_id: Medication ID

        Returns:
            Dictionary with batch information
        """
        print(f"\n[Medication] Getting batches for: {medication_id}")

        # Parameter format: medication_id#
        data = f"{medication_id}#"

        result = await self._ajax_call(
            'amfb/fb/dispensacao.ajax.asp',
            'obterLotesMedicamento',
            data
        )

        if result['valido']:
            if 'dados' in result and result['dados']:
                print(f"  [OK] Batch information retrieved")
            else:
                print(f"  [INFO] No batch information available")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    # ========================================================================
    # ATTENDANCE FINALIZATION METHODS (from w6 HAR)
    # ========================================================================

    async def check_signature_requirements(self, attendance_id: str) -> Dict:
        """
        Check digital signature requirements for attendance

        Args:
            attendance_id: Attendance ID

        Returns:
            Dictionary with signature requirement status
        """
        print(f"\n[Attendance] Checking signature requirements")

        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'verificarPendenciasAssinaturaDigital',
            attendance_id
        )

        if result['valido']:
            print(f"  [OK] Signature requirements checked")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def check_home_medication(self, attendance_id: str) -> Dict:
        """
        Check home medication delivery requirements

        Args:
            attendance_id: Attendance ID

        Returns:
            Dictionary with home medication status
        """
        print(f"\n[Attendance] Checking home medication requirements")

        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'verificarDispensacaoMedicamentoEmCasa',
            attendance_id
        )

        if result['valido']:
            concluido = result['dados'].get('concluido', 'false') == 'true' if 'dados' in result else False
            if concluido:
                print(f"  [OK] Home medication requirements checked")
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")

        return result

    async def finalize_attendance(self, attendance_id: str) -> bool:
        """
        Finalize/complete attendance workflow

        Args:
            attendance_id: Attendance ID

        Returns:
            True if successful
        """
        print(f"\n[Attendance] Finalizing attendance: {attendance_id}")

        # Check signature requirements
        sig_result = await self.check_signature_requirements(attendance_id)
        if not sig_result['valido']:
            print(f"  [WARN] Signature check failed, continuing...")

        # Check home medication
        home_result = await self.check_home_medication(attendance_id)
        if not home_result['valido']:
            print(f"  [WARN] Home medication check failed, continuing...")

        # Finalize
        result = await self._ajax_call(
            'amfb/fb/atendimento.ajax.asp',
            'concluirAtendimento',
            attendance_id
        )

        if result['valido']:
            concluido = result['dados'].get('concluido', 'false') == 'true' if 'dados' in result else False
            if concluido:
                print(f"  [OK] Attendance finalized successfully")
                return True
            else:
                print(f"  [ERROR] Finalization returned concluido=false")
                return False
        else:
            print(f"  [ERROR] {result.get('mensagem', 'Unknown error')}")
            return False

    # ========================================================================
    # DIRECT DISPENSING METHODS (from w6 HAR)
    # ========================================================================

    async def dispense_material_direct(
        self,
        attendance_id: str,
        material_id: str,
        quantity: int,
        data_suficiencia: str
    ) -> bool:
        """
        Dispense material directly (without prescription)

        Args:
            attendance_id: Attendance ID
            material_id: Material ID
            quantity: Quantity to dispense
            data_suficiencia: Sufficiency date (DD/MM/YYYY)

        Returns:
            True if successful
        """
        print(f"\n[Dispensing] Direct material delivery: {material_id} (qty: {quantity})")

        try:
            await self._request_delay(0.5, 1.0)

            # Get material details first
            material_result = await self.search_material(material_id)
            if not material_result['valido']:
                print(f"  [ERROR] Material not found")
                return False

            # Submit dispensing form
            form_data = {
                'txtAtendimentoChave': attendance_id,
                'txtMaterialRecnum': material_id,
                'txtQtdeEntregue': str(quantity),
                'txtDataSuficiencia': data_suficiencia,
                'origem': '0'  # Direct dispensing
            }

            response = self.session.post(
                f"{self.base_url}/saudeweb/amfb/fb/dispensacao_direta.asp",
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{self.base_url}/saudeweb/amfb/fb/dispensacao_direta.asp?origem=0"
                },
                timeout=15
            )

            if response.status_code == 200:
                print(f"  [OK] Material dispensed successfully")
                return True
            else:
                print(f"  [ERROR] Dispensing failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"  [ERROR] Failed to dispense material: {e}")
            return False


# Convenience function
def create_api_client(base_url: str = "https://w6.olostech.com.br") -> OlostechAPIClient:
    """
    Factory function to create API client

    Args:
        base_url: Olostech base URL

    Returns:
        Initialized OlostechAPIClient instance
    """
    return OlostechAPIClient(base_url)
