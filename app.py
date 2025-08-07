from dotenv import load_dotenv
import streamlit as st
import requests
import time
import os
import json
from typing import List, Optional
import tempfile

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🇸🇬 Singapore AI Dietician",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8006")

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #d32f2f;
        margin-bottom: 2rem;
    }
    .recommendation-box {
        background-color: #f8f9fa;
        border-left: 5px solid #d32f2f;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
    .nutrition-metric {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        text-align: center;
        margin: 0.5rem;
    }
    .compliance-score {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem;
    }
    .score-high { background-color: #4caf50; }
    .score-medium { background-color: #ff9800; }
    .score-low { background-color: #f44336; }
    .alternative-box {
        background-color: #e8f5e8;
        border: 1px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "selected_menu_items" not in st.session_state:
    st.session_state.selected_menu_items = []
if "processing_job_id" not in st.session_state:
    st.session_state.processing_job_id = None
if "extracted_menu_options" not in st.session_state:
    st.session_state.extracted_menu_options = []
if "document_processed" not in st.session_state:
    st.session_state.document_processed = False
# Persistent state that survives form submissions
if "extracted_items_persistent" not in st.session_state:
    st.session_state.extracted_items_persistent = []
if "doc_processed_persistent" not in st.session_state:
    st.session_state.doc_processed_persistent = False
# API key management
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False


def get_headers():
    """Get headers with API key for authenticated requests"""
    if not st.session_state.api_key:
        return {"Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {st.session_state.api_key}",
        "Content-Type": "application/json",
    }


def check_backend_health():
    """Check if the backend is running"""
    try:
        # Check public health endpoint first
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            return True

        # Fallback to root endpoint
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def test_api_key(api_key=None):
    """Test if API key is working"""
    if not api_key and not st.session_state.api_key:
        return False, "No API key provided"

    test_key = api_key if api_key else st.session_state.api_key
    headers = {
        "Authorization": f"Bearer {test_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(f"{BACKEND_URL}/api-info", headers=headers, timeout=5)
        return response.status_code == 200, response
    except Exception as e:
        return False, str(e)


def analyze_menu_api(
    menu_items: List[str],
    dietary_preferences: Optional[List[str]] = None,
    health_conditions: Optional[List[str]] = None,
    age_group: str = "adult",
):
    """Call the backend API to analyze menu items"""
    try:
        payload = {
            "menu_items": menu_items,
            "dietary_preferences": dietary_preferences or [],
            "health_conditions": health_conditions or [],
            "age_group": age_group,
        }

        response = requests.post(
            f"{BACKEND_URL}/analyze-menu",
            json=payload,
            headers=get_headers(),
            timeout=120,  # Extended timeout for AI processing
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The AI analysis is taking longer than expected.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(
            "🔌 Cannot connect to the backend. Please ensure the FastAPI server is running."
        )
        return None
    except Exception as e:
        st.error(f"❌ Error communicating with backend: {str(e)}")
        return None


def get_food_recommendations_api(query: str):
    """Get food recommendations from the backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/get-recommendations",
            params={"query": query},
            headers=get_headers(),
            timeout=60,
        )

        if response.status_code == 200:
            return response.json()["recommendations"]
        else:
            st.error(f"Backend error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        st.error(f"❌ Error getting recommendations: {str(e)}")
        return None


def start_document_processing_job(file_path: str):
    """Start document processing job and return job_id"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/extract-menu-items",
            params={"file_path": file_path},
            headers=get_headers(),
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Backend error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        st.error(f"❌ Error starting document processing: {str(e)}")
        return None


def get_job_status(job_id: str):
    """Get job status from backend"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/jobs/{job_id}", headers=get_headers(), timeout=10
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # Job not found - this is expected if job was cleaned up
            return {"status": "not_found", "error": "Job not found or expired"}
        else:
            st.error(f"Backend returned {response.status_code}: {response.text}")
            return None
    except requests.exceptions.Timeout:
        st.warning("⏱️ Request timed out while checking job status")
        return None
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend")
        return None
    except Exception as e:
        st.error(f"❌ Error getting job status: {str(e)}")
        return None


def extract_menu_from_job(job_id: str):
    """Extract menu items from completed document processing job"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/jobs/{job_id}/extract-menu",
            headers=get_headers(),
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning("Job not found for menu extraction")
            return None
        else:
            st.error(
                f"Menu extraction failed: {response.status_code} - {response.text}"
            )
            return None
    except requests.exceptions.Timeout:
        st.warning("⏱️ Menu extraction request timed out")
        return None
    except Exception as e:
        st.error(f"❌ Error extracting menu: {str(e)}")
        return None


def extract_menu_items_from_content(content: str):
    """Extract menu items from document content using AI"""
    try:
        # Use a simple AI call to extract menu items
        prompt = f"""
        Extract menu items from this restaurant menu content. Return only the food item names, one per line.
        Focus on actual food dishes, not prices, descriptions, or categories.
        
        Menu content:
        {content[:2000]}  # Limit content to avoid token limits
        
        Return menu items as a simple list, one item per line:
        """

        response = requests.post(
            f"{BACKEND_URL}/get-recommendations",
            params={"query": f"Extract menu items from: {content}"},
            headers=get_headers(),
            timeout=30,
        )

        if response.status_code == 200:
            ai_response = response.json()["recommendations"]

            # Simple parsing to extract menu items
            import re

            # Extract lines that look like menu items (contain letters and may have prices)
            lines = content.split("\n")
            menu_items = []

            for line in lines:
                line = line.strip()
                # Skip empty lines, images, and metadata
                if (
                    line
                    and not line.startswith("{")
                    and not line.startswith("·")
                    and not line.startswith("?")
                    and len(line) > 3
                    and not line.isnumeric()
                    and "img_path" not in line
                ):

                    # Clean up the line - remove prices and extra info
                    cleaned = re.sub(r"\d+\.\d+", "", line)  # Remove prices like "9.90"
                    cleaned = re.sub(r"/\d+\.\d+", "", cleaned)  # Remove "/11.90"
                    cleaned = re.sub(r"\+\s*\d+", "", cleaned)  # Remove "+1"
                    cleaned = re.sub(r"[|].*", "", cleaned)  # Remove everything after |
                    cleaned = cleaned.strip()

                    # Skip very short items or obvious categories
                    if (
                        len(cleaned) > 5
                        and cleaned
                        not in ["LUNCH SPECIALS", "BURGERS/MAINS", "MON-THU", "TILL4PM"]
                        and not cleaned.startswith("·")
                    ):
                        menu_items.append(cleaned)

            # Remove duplicates and limit to reasonable number
            unique_items = list(dict.fromkeys(menu_items))[:15]
            return unique_items

        else:
            # Fallback: simple text parsing without AI
            return parse_menu_items_simple(content)

    except Exception as e:
        st.warning(f"AI extraction failed: {e}, using simple parsing")
        return parse_menu_items_simple(content)


def parse_menu_items_simple(content: str):
    """Simple menu item extraction without AI"""
    import re

    lines = content.split("\n")
    menu_items = []

    for line in lines:
        line = line.strip()
        # Skip empty lines, images, and metadata
        if (
            line
            and not line.startswith("{")
            and not line.startswith("·")
            and not line.startswith("?")
            and len(line) > 5
            and not line.isnumeric()
            and "img_path" not in line
            and "type" not in line
        ):

            # Clean up the line
            cleaned = re.sub(
                r"\d+\.\d+.*$", "", line
            )  # Remove prices and everything after
            cleaned = re.sub(r"/.*$", "", cleaned)  # Remove variants
            cleaned = cleaned.strip()

            if len(cleaned) > 3 and cleaned not in [
                "LUNCH SPECIALS",
                "BURGERS/MAINS",
                "MON-THU",
                "TILL4PM",
            ]:
                menu_items.append(cleaned)

    # Remove duplicates and limit
    unique_items = list(dict.fromkeys(menu_items))[:12]
    return unique_items


def poll_job_until_complete(job_id: str):
    """Poll job status until completion - similar to the reference structure"""
    max_polls = 100  # Prevent infinite polling (5 minutes at 3 second intervals)
    poll_count = 0

    while True:
        status_data = get_job_status(job_id)
        poll_count += 1

        if not status_data:
            st.error(f"❌ Could not get job status (attempt {poll_count})")
            return None

        status = status_data.get("status", "unknown")

        if status == "completed":
            return status_data
        elif status == "failed":
            st.error(f"❌ Job failed: {status_data.get('error', 'Unknown error')}")
            return None
        elif status == "not_found":
            st.error("❌ Job not found or expired")
            return None
        elif status in ["pending", "running"]:
            # Show progress if available
            progress = status_data.get("progress", 0)
            # if progress > 0:
            #     st.write(f"Progress: {progress}% (Poll {poll_count})")
            # else:
            #     st.write(f"Status: {status} (Poll {poll_count})")

            # Wait before next check
            time.sleep(8)
        else:
            st.warning(f"Unknown status: {status} (Poll {poll_count})")
            time.sleep(8)

    # If we get here, we've exceeded max polls
    st.error("❌ Job polling timed out after 5 minutes")
    return None


def main():
    # Header
    st.markdown(
        '<h1 class="main-header">🇸🇬 Singapore AI Dietician</h1>', unsafe_allow_html=True
    )
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">Get personalized dietary recommendations based on Singapore\'s My Healthy Plate guidelines</p>',
        unsafe_allow_html=True,
    )

    # Sidebar for configuration and info
    with st.sidebar:
        st.header("⚙️ Backend Status")

        # Check backend health
        if check_backend_health():
            st.success("✅ Backend connected")
        else:
            st.error("❌ Backend disconnected")
            st.warning(
                "Please start the FastAPI backend:\n```bash\npython app/main.py\n```"
            )
            return

        st.divider()

        # API Key Configuration
        st.header("🔐 API Key Authentication")

        api_key_input = st.text_input(
            "Enter your API Key:",
            type="password",
            value=st.session_state.api_key,
            placeholder="fai_xxxxxxxxxxxxxxxxxxxxxxxx",
            help="Enter your Food AI API key to access the protected endpoints",
        )

        # Update session state when input changes
        if api_key_input != st.session_state.api_key:
            st.session_state.api_key = api_key_input
            st.session_state.api_key_valid = False

        # Test API key button
        if st.button("🔍 Test API Key", disabled=not api_key_input.strip()):
            with st.spinner("Testing API key..."):
                is_valid, response = test_api_key(api_key_input)

            if is_valid:
                st.session_state.api_key_valid = True
                st.success("✅ API key is valid!")

                # Show API key info if available
                if isinstance(response, requests.Response):
                    try:
                        data = response.json()
                        key_info = data.get("api_key", {})
                        rate_info = data.get("rate_limit", {})

                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Rate Limit", rate_info.get("limit", "N/A"))
                        with col2:
                            st.metric("Remaining", rate_info.get("remaining", "N/A"))

                        if key_info.get("permissions"):
                            st.write(
                                f"**Permissions:** {', '.join(key_info['permissions'])}"
                            )

                    except:
                        pass
            else:
                st.session_state.api_key_valid = False
                st.error("❌ Invalid API key")
                error_msg = (
                    str(response)
                    if isinstance(response, str)
                    else "Authentication failed"
                )
                st.error(f"Error: {error_msg}")

        # Show current API key status
        if st.session_state.api_key:
            if st.session_state.api_key_valid:
                st.success("🟢 API key authenticated")
            else:
                st.warning("🟡 API key not tested - click 'Test API Key' above")
        else:
            st.info("🔑 Enter an API key to access protected features")

        st.divider()

        # Singapore Guidelines Info
        with st.expander("📋 Singapore My Healthy Plate Guidelines"):
            st.markdown(
                """
            **Half Plate (50%)**  
            🥬 Fruits & Vegetables  
            *Minimum 2 servings each daily*
            
            **Quarter Plate (25%)**  
            🌾 Wholegrains  
            *Rich in vitamins B, E, minerals*
            
            **Quarter Plate (25%)**  
            🍗 Lean Meat & Others  
            *2-3 servings daily (3 for seniors 50+)*
            """
            )

        st.divider()

        # Official Guidelines Access
        with st.expander("🏛️ Official Singapore Guidelines"):
            st.markdown("**Access official Health Promotion Board guidelines**")

            guideline_categories = [
                "my_healthy_plate",
                "nutritional_targets",
                "age_specific",
                "sodium_guidelines",
                "beverage_guidelines",
                "healthier_choice_symbol",
            ]

            selected_category = st.selectbox(
                "Select guideline category:",
                options=guideline_categories,
                help="Choose a category to view official Singapore health guidelines",
            )

            if st.button("📋 View Guidelines"):
                with st.spinner("Fetching official guidelines..."):
                    try:
                        response = requests.get(
                            f"{BACKEND_URL}/singapore-guidelines/{selected_category}",
                            headers=get_headers(),
                        )
                        if response.status_code == 200:
                            guidelines = response.json()
                            st.json(guidelines)
                        else:
                            st.error("Failed to fetch guidelines")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    # Main content - only show if backend is available and API key is provided
    if not check_backend_health():
        st.stop()

    # Check if API key is provided for protected features
    if not st.session_state.api_key:
        st.warning("🔑 **API Key Required**")
        st.info(
            "Please enter your API key in the sidebar to access the Singapore AI Dietician features."
        )

        # Show some information about the API
        st.markdown(
            """
        ### 🇸🇬 Singapore AI Dietician API
        
        This application provides AI-powered dietary recommendations based on Singapore's official health guidelines.
        
        **Features:**
        - 🍽️ Menu analysis with nutritional insights
        - 📋 Compliance with Singapore's My Healthy Plate guidelines  
        - 🥗 Personalized dietary recommendations
        - 📄 Document upload and menu extraction
        - 🔍 Food recommendations based on health conditions
        
        **To get started:**
        1. 🔑 Obtain an API key (format: `fai_xxxxxxxxxx`)
        2. 📝 Enter your API key in the sidebar (password field)
        3. ✅ Click "Test API Key" to validate
        4. 🚀 Start analyzing menus!
        
        **Need an API key?**
        - Contact the administrator to get your personal API key
        - API keys provide rate limiting and access control
        - Different keys have different permission levels
        """
        )
        st.stop()

    elif not st.session_state.api_key_valid:
        st.warning("🟡 **API Key Not Validated**")
        st.info(
            "Your API key hasn't been tested yet. Please click 'Test API Key' in the sidebar to validate it."
        )
        st.stop()

    # Enhanced Menu Analysis Section
    st.subheader("🍽️ Menu Analysis")

    # Step 1: Menu Input Options
    input_method = st.radio(
        "How would you like to provide menu information?",
        ["📄 Upload menu image/document", "📝 Type menu items"],
        horizontal=True,
    )

    if input_method == "📄 Upload menu image/document":
        uploaded_file = st.file_uploader(
            "Upload Menu (Image, PDF, etc.)",
            type=["pdf", "png", "jpg", "jpeg", "docx"],
            help="Upload restaurant menu images or documents",
        )

        if uploaded_file:
            # Check if we haven't processed this file yet
            file_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"

            if file_key not in st.session_state:
                # Automatically start processing when file is uploaded
                with st.spinner(f"🔍 Processing {uploaded_file.name}..."):
                    # Save uploaded file temporarily
                    temp_path = os.path.join(
                        tempfile.gettempdir(), f"temp_{uploaded_file.name}"
                    )
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Start document processing job
                    result = start_document_processing_job(temp_path)

                if result and result.get("job_id"):
                    job_id = result["job_id"]
                    st.info(f"📄 Document processing started! Job ID: {job_id}")

                    # Poll until completion - following the reference pattern
                    with st.spinner(
                        "Processing document... This may take a few minutes for PDFs."
                    ):
                        final_result = poll_job_until_complete(job_id)

                    if final_result:
                        st.success("✅ Document processing completed!")

                        # Try to extract menu items
                        extraction_result = extract_menu_from_job(job_id)

                        if extraction_result and extraction_result.get(
                            "document_content"
                        ):
                            content = extraction_result["document_content"]
                            st.success("✅ Document content extracted!")

                            # Show content in expander
                            with st.expander("📄 Extracted Document Content"):
                                st.text_area(
                                    "Content:", value=content, height=200, disabled=True
                                )

                            # Extract actual menu items from the content using AI
                            with st.spinner(
                                "🤖 Extracting menu items from document..."
                            ):
                                extracted_menu_items = extract_menu_items_from_content(
                                    content
                                )

                            if extracted_menu_items:
                                st.success(
                                    f"✅ Found {len(extracted_menu_items)} menu items!"
                                )

                                # Use extracted items as options, with ability to add more
                                all_options = extracted_menu_items
                                # Remove duplicates while preserving order
                                seen = set()
                                unique_options = []
                                for item in all_options:
                                    if item.lower() not in seen:
                                        seen.add(item.lower())
                                        unique_options.append(item)

                                # Store in session state to prevent refresh issues
                                st.session_state.extracted_menu_options = unique_options
                                st.session_state.document_processed = True
                                # Also store in a more permanent way
                                st.session_state["extracted_items_persistent"] = (
                                    unique_options
                                )
                                st.session_state["doc_processed_persistent"] = True
                                # Mark this file as processed to prevent re-processing
                                st.session_state[file_key] = True
                        else:
                            st.error("Failed to extract content from document.")
                            # Fallback to common items
                            fallback_items = [
                                "Chicken Rice",
                                "Laksa",
                                "Char Kway Teow",
                                "Prawn Mee",
                                "Bak Chor Mee",
                                "Fish and Chips",
                                "Nasi Lemak",
                                "Kaya Toast",
                            ]
                            st.session_state.selected_menu_items = fallback_items[:3]
                            st.info("Using common Singapore dishes as fallback.")

                elif result and result.get("status") == "fallback_success":
                    # Handle fallback case (no job_id but fallback items provided)
                    st.warning(
                        "⚠️ Document processing encountered issues, using fallback items."
                    )
                    if result.get("error"):
                        with st.expander("Error Details"):
                            st.error(result["error"])

                    fallback_items = result.get(
                        "menu_items",
                        [
                            "Chicken Rice",
                            "Laksa",
                            "Char Kway Teow",
                            "Prawn Mee",
                            "Bak Chor Mee",
                            "Fish and Chips",
                            "Nasi Lemak",
                            "Kaya Toast",
                        ],
                    )

                    # Store fallback items in session state
                    st.session_state["extracted_items_persistent"] = fallback_items
                    st.session_state["doc_processed_persistent"] = True
                    # Mark this file as processed
                    st.session_state[file_key] = True
                    st.info(f"Using {len(fallback_items)} common Singapore dishes.")

                elif result and result.get("status") == "cache_hit":

                    extracted_menu_items = result.get("menu_items", [])
                    st.success(f"✅ Found {len(extracted_menu_items)} menu items!")

                    # Use extracted items as options, with ability to add more
                    all_options = extracted_menu_items
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_options = []
                    for item in all_options:
                        if item.lower() not in seen:
                            seen.add(item.lower())
                            unique_options.append(item)

                    # Store in session state to prevent refresh issues
                    st.session_state.extracted_menu_options = unique_options
                    st.session_state.document_processed = True
                    # Also store in a more permanent way
                    st.session_state["extracted_items_persistent"] = unique_options
                    st.session_state["doc_processed_persistent"] = True
                    # Mark this file as processed to prevent re-processing
                    st.session_state[file_key] = True

                else:
                    st.error("❌ Failed to start document processing.")
                    if result:
                        st.error(f"Backend response: {result}")

                    # Clean up temp file
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            else:
                # File has already been processed
                st.success(f"✅ {uploaded_file.name} already processed!")

                # Show extracted items if available
                if st.session_state.get("extracted_items_persistent"):
                    items_count = len(st.session_state["extracted_items_persistent"])
                    st.info(f"Found {items_count} menu items from this document")

                    # Option to reprocess if needed
                    if st.button("🔄 Reprocess Document"):
                        # Clear the processed flag to allow reprocessing
                        if file_key in st.session_state:
                            del st.session_state[file_key]
                        st.rerun()

    # Menu selection section (outside of form to prevent state loss)
    st.subheader("📝 Menu Selection")

    # Check both regular and persistent state for extracted items
    has_extracted_items = st.session_state.get(
        "extracted_items_persistent"
    ) or st.session_state.get("extracted_menu_options")
    doc_processed = st.session_state.get(
        "doc_processed_persistent"
    ) or st.session_state.get("document_processed")

    if (
        input_method == "📄 Upload menu image/document"
        and doc_processed
        and has_extracted_items
    ):
        # Use persistent state if available, fallback to regular state
        menu_options = st.session_state.get(
            "extracted_items_persistent"
        ) or st.session_state.get("extracted_menu_options", [])

        st.success(f"📄 Document processed! Found {len(menu_options)} menu options.")

        # Menu selection interface (outside form)
        selected_from_doc = st.multiselect(
            "Select items to analyze:",
            options=menu_options,
            key="doc_menu_selection",
            help="Choose items extracted from your uploaded document",
        )

        # Allow custom additions
        custom_additions = st.text_input(
            "Add custom items (comma-separated):",
            key="custom_menu_additions",
            help="Add any items not found in the document",
        )

        # Combine selections
        all_selected = list(selected_from_doc)
        if custom_additions:
            custom_list = [
                item.strip() for item in custom_additions.split(",") if item.strip()
            ]
            all_selected.extend(custom_list)

        # Update session state
        st.session_state.selected_menu_items = all_selected

        # Show current selection
        if all_selected:
            st.success(
                f"✅ Selected {len(all_selected)} items: {', '.join(all_selected[:3])}{'...' if len(all_selected) > 3 else ''}"
            )
        else:
            st.info("👆 Select items above to analyze")

    # Input form with enhanced workflow
    with st.form("menu_analysis_form"):
        if input_method == "📝 Type menu items":
            menu_items_input = st.text_area(
                "Menu Items (one per line or comma-separated)",
                placeholder="Chicken Rice\nLaksa\nKaya Toast\nTeh Tarik",
                height=120,
                help="Enter Singapore dishes you want to analyze",
            )
        else:
            # For document upload method, use items from session state
            if st.session_state.selected_menu_items:
                menu_items_input = "\n".join(st.session_state.selected_menu_items)
                st.text_area(
                    "Items to Analyze:",
                    value=menu_items_input,
                    height=100,
                    disabled=True,
                    help="Items selected above (outside the form)",
                )
            else:
                menu_items_input = ""
                st.warning(
                    "⚠️ No items selected. Please select items from the menu above."
                )

        col1, col2 = st.columns(2)

        with col1:
            age_group = st.selectbox(
                "Age Group",
                options=["child", "adolescent", "adult", "senior"],
                index=2,
                help="Select your age group for personalized recommendations",
            )

        with col2:
            dietary_preferences = st.multiselect(
                "Dietary Preferences",
                options=[
                    "vegetarian",
                    "vegan",
                    "halal",
                    "kosher",
                    "gluten-free",
                    "dairy-free",
                    "low-sodium",
                    "low-sugar",
                    "keto",
                    "paleo",
                ],
                help="Select any dietary restrictions or preferences",
            )

        health_conditions = st.multiselect(
            "Health Conditions",
            options=[
                "diabetes",
                "hypertension",
                "heart-disease",
                "kidney-disease",
                "high-cholesterol",
                "obesity",
                "osteoporosis",
                "anemia",
            ],
            help="Select any relevant health conditions",
        )

        submitted = st.form_submit_button(
            "🔍 Analyze Menu for My Health Profile", type="primary"
        )

    # Process analysis
    if submitted and menu_items_input.strip():
        # Parse menu items
        menu_items = [
            item.strip()
            for item in menu_items_input.replace("\n", ",").split(",")
            if item.strip()
        ]

        if not menu_items:
            st.error("Please enter at least one menu item.")
            return

        # Show analysis
        with st.spinner("🤖 Analyzing your menu with Singapore dietary guidelines..."):
            results = analyze_menu_api(
                menu_items, dietary_preferences, health_conditions, age_group
            )

        if results:
            display_results(results, menu_items)

    elif submitted:
        st.error("Please enter at least one menu item to analyze.")

    # Additional feature: Food recommendations
    st.divider()
    st.subheader("🍽️ Get Food Recommendations")

    recommendation_query = st.text_input(
        "What kind of food are you looking for?",
        placeholder="e.g., healthy breakfast options, low-sodium lunch, vegetarian dinner",
        help="Ask for specific food recommendations based on your needs",
    )

    if st.button("🔍 Get Recommendations") and recommendation_query.strip():
        with st.spinner("🤖 Finding personalized food recommendations..."):
            recommendations = get_food_recommendations_api(recommendation_query)

            if recommendations:
                st.subheader("💡 Personalized Food Recommendations")
                st.markdown(
                    f'<div class="recommendation-box">{recommendations}</div>',
                    unsafe_allow_html=True,
                )


def display_results(results, menu_items):
    """Display analysis results"""
    st.success("✅ Analysis complete!")

    # Show analyzed items
    st.subheader("📋 Analyzed Menu Items")
    for i, item in enumerate(menu_items, 1):
        st.write(f"{i}. {item}")

    st.divider()

    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🥗 Recommendations",
            "📊 Nutritional Analysis",
            "🇸🇬 Guidelines Compliance",
            "🔄 Healthier Alternatives",
        ]
    )

    with tab1:
        st.subheader("🥗 Dietary Recommendations")
        if isinstance(results.get("recommendations"), list):
            for i, recommendation in enumerate(results["recommendations"], 1):
                st.markdown(
                    f'<div class="recommendation-box">{recommendation}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write(results.get("recommendations", "No recommendations available"))

    with tab2:
        st.subheader("📊 Nutritional Analysis")
        if results.get("nutritional_analysis"):
            nutrition_data = results["nutritional_analysis"]

            if isinstance(nutrition_data, dict):
                for key, value in nutrition_data.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            else:
                st.write(nutrition_data)
        else:
            st.info("No nutritional analysis available")

    with tab3:
        st.subheader("🇸🇬 Singapore Guidelines Compliance")
        if results.get("singapore_guidelines_compliance"):
            compliance_data = results["singapore_guidelines_compliance"]

            if isinstance(compliance_data, dict):
                for key, value in compliance_data.items():
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            else:
                st.write(compliance_data)
        else:
            st.info("No compliance analysis available")

    with tab4:
        st.subheader("🔄 Healthier Alternatives")
        if isinstance(results.get("alternatives"), list):
            for i, alternative in enumerate(results["alternatives"], 1):
                st.markdown(
                    f'<div class="alternative-box">{alternative}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write(results.get("alternatives", "No alternatives available"))


if __name__ == "__main__":
    main()
