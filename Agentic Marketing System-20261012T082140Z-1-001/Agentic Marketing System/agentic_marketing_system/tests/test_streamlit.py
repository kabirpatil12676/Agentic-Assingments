import pytest
from streamlit.testing.v1 import AppTest
import os

def test_streamlit_startup_and_render():
    # Set environment to demo mode for testing
    os.environ["DEMO_MODE"] = "true"
    
    # Run the streamlit app programmatically
    at = AppTest.from_file("dashboard/streamlit_app.py", default_timeout=20)
    at.run()
    
    # Verify no unhandled exceptions crashed the app
    assert not at.exception, f"Streamlit crashed with exception: {at.exception}"
    
    # Check that key sections loaded correctly
    # The title should be present
    assert len(at.title) > 0
    assert "Agentic AI Marketing Campaign Optimization" in at.title[0].value
    
    # Check subheaders
    subheaders = [sh.value for sh in at.subheader]
    assert any("Campaign Setup" in sh for sh in subheaders)
    
    # Since we can't easily click "Run Campaign" in this static headless test and await asyncio correctly
    # without a complex mock, we verify the structure loads without crashing.
    # We'll check that the Run button exists.
    assert "Run Campaign" in at.button[0].label

    # We verified Streamlit runtime initializes, components render, and no import/schema errors exist.
