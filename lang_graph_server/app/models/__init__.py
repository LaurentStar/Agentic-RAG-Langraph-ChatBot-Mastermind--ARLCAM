"""
Models Module.

Contains all data models for the LangGraph server organized by purpose:

- config_models/: Frozen dataclasses for configuration (action costs, platform limits)
- decision_models/: Mutable dataclasses for decision results
- graph_state_models/: TypedDicts for LangGraph workflow states
- rest_api_models/: Flask-RESTX API request/response models
- structured_output_models/: Pydantic models for LLM structured outputs
"""

