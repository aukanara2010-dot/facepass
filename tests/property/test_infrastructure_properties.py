"""
Property-based tests for infrastructure configuration.

These tests validate universal correctness properties of the Fecapass
Docker architecture infrastructure.
"""

import os
from pathlib import Path
import pytest


class TestProjectStructure:
    """Property 5: Project Directory Structure Completeness
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    
    For any valid Fecapass project, all five required directories 
    (/app, /core, /services, /workers, /models) should exist in the project root.
    """
    
    def test_required_directories_exist(self):
        """Test that all required project directories exist."""
        # Get project root (two levels up from this test file)
        project_root = Path(__file__).parent.parent.parent
        
        # Required directories as per Requirements 2.1-2.5
        required_directories = [
            "app",      # Requirement 2.1: API logic and routes
            "core",     # Requirement 2.2: Configuration and database connections
            "services", # Requirement 2.3: AI processing and vector operations
            "workers",  # Requirement 2.4: Celery task definitions
            "models",   # Requirement 2.5: SQLAlchemy and Pydantic schemas
        ]
        
        missing_directories = []
        for directory in required_directories:
            dir_path = project_root / directory
            if not dir_path.exists() or not dir_path.is_dir():
                missing_directories.append(directory)
        
        assert not missing_directories, (
            f"Missing required directories: {missing_directories}. "
            f"All directories {required_directories} must exist in project root."
        )
    
    def test_directories_are_python_packages(self):
        """Test that all required directories are valid Python packages."""
        project_root = Path(__file__).parent.parent.parent
        
        required_directories = ["app", "core", "services", "workers", "models"]
        
        missing_init_files = []
        for directory in required_directories:
            init_file = project_root / directory / "__init__.py"
            if not init_file.exists() or not init_file.is_file():
                missing_init_files.append(f"{directory}/__init__.py")
        
        assert not missing_init_files, (
            f"Missing __init__.py files: {missing_init_files}. "
            f"All directories must be valid Python packages."
        )



class TestRequirementsTxt:
    """Property 6: Python Dependencies Completeness
    
    **Validates: Requirements 3.1-3.11**
    
    For any valid requirements.txt file, it should contain all 11 required packages:
    fastapi, uvicorn, sqlalchemy, pgvector, boto3, insightface, onnxruntime, 
    celery, redis, psycopg2-binary, and python-dotenv.
    """
    
    def test_all_required_packages_present(self):
        """Test that requirements.txt contains all required packages."""
        project_root = Path(__file__).parent.parent.parent
        requirements_file = project_root / "requirements.txt"
        
        # Ensure requirements.txt exists
        assert requirements_file.exists(), "requirements.txt file must exist in project root"
        
        # Read requirements.txt content
        with open(requirements_file, 'r') as f:
            content = f.read().lower()
        
        # Required packages as per Requirements 3.1-3.11
        required_packages = {
            "fastapi": "3.1",      # Requirement 3.1: Web framework
            "uvicorn": "3.2",      # Requirement 3.2: ASGI server
            "sqlalchemy": "3.3",   # Requirement 3.3: ORM
            "pgvector": "3.4",     # Requirement 3.4: Vector operations
            "boto3": "3.5",        # Requirement 3.5: S3 integration
            "insightface": "3.6",  # Requirement 3.6: Face recognition
            "onnxruntime": "3.7",  # Requirement 3.7: AI model inference
            "celery": "3.8",       # Requirement 3.8: Task queue
            "redis": "3.9",        # Requirement 3.9: Celery broker
            "psycopg2-binary": "3.10",  # Requirement 3.10: PostgreSQL connectivity
            "python-dotenv": "3.11",    # Requirement 3.11: Environment variable management
        }
        
        missing_packages = []
        for package, requirement in required_packages.items():
            if package not in content:
                missing_packages.append(f"{package} (Requirement {requirement})")
        
        assert not missing_packages, (
            f"Missing required packages in requirements.txt: {missing_packages}. "
            f"All packages must be present as per Requirements 3.1-3.11."
        )
    
    def test_requirements_file_is_readable(self):
        """Test that requirements.txt is a valid text file."""
        project_root = Path(__file__).parent.parent.parent
        requirements_file = project_root / "requirements.txt"
        
        assert requirements_file.exists(), "requirements.txt must exist"
        assert requirements_file.is_file(), "requirements.txt must be a file"
        
        # Try to read the file
        try:
            with open(requirements_file, 'r') as f:
                content = f.read()
            assert len(content) > 0, "requirements.txt must not be empty"
        except Exception as e:
            pytest.fail(f"Failed to read requirements.txt: {e}")



class TestEnvExample:
    """Property 11: Environment Template Documentation
    
    **Validates: Requirements 8.6**
    
    For any configuration variable in .env.example, it should be accompanied 
    by a comment explaining its purpose, ensuring developers understand what 
    each variable controls.
    """
    
    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        project_root = Path(__file__).parent.parent.parent
        env_example_file = project_root / ".env.example"
        
        assert env_example_file.exists(), ".env.example file must exist in project root"
        assert env_example_file.is_file(), ".env.example must be a file"
    
    def test_all_variables_have_comments(self):
        """Test that all configuration variables have explanatory comments."""
        project_root = Path(__file__).parent.parent.parent
        env_example_file = project_root / ".env.example"
        
        with open(env_example_file, 'r') as f:
            lines = f.readlines()
        
        # Track variables and their preceding comments
        variables_without_comments = []
        previous_line_was_comment = False
        previous_line_was_empty = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and section headers
            if not line or line.startswith('#'):
                previous_line_was_comment = line.startswith('#') and not line.startswith('# ===')
                previous_line_was_empty = not line
                continue
            
            # Check if this is a variable assignment
            if '=' in line and not line.startswith('#'):
                variable_name = line.split('=')[0].strip()
                
                # Check if there was a comment in the previous non-empty line
                if not previous_line_was_comment:
                    variables_without_comments.append(variable_name)
                
                previous_line_was_comment = False
                previous_line_was_empty = False
        
        assert not variables_without_comments, (
            f"Variables without explanatory comments: {variables_without_comments}. "
            f"All variables must have comments explaining their purpose (Requirement 8.6)."
        )
    
    def test_required_configuration_sections_present(self):
        """Test that .env.example contains all required configuration sections."""
        project_root = Path(__file__).parent.parent.parent
        env_example_file = project_root / ".env.example"
        
        with open(env_example_file, 'r') as f:
            content = f.read()
        
        # Required configuration sections as per Requirements 8.2-8.5
        required_sections = {
            "S3": "8.2",           # S3 configuration variables
            "Database": "8.3",     # Database connection variables
            "Redis": "8.4",        # Redis configuration variables
            "Celery": "8.5",       # Celery configuration variables
        }
        
        missing_sections = []
        for section, requirement in required_sections.items():
            if section.lower() not in content.lower():
                missing_sections.append(f"{section} (Requirement {requirement})")
        
        assert not missing_sections, (
            f"Missing required configuration sections: {missing_sections}. "
            f"All sections must be documented in .env.example."
        )
    
    def test_critical_variables_present(self):
        """Test that critical environment variables are defined in .env.example."""
        project_root = Path(__file__).parent.parent.parent
        env_example_file = project_root / ".env.example"
        
        with open(env_example_file, 'r') as f:
            content = f.read()
        
        # Critical variables that must be present
        critical_variables = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "S3_ENDPOINT",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
            "S3_BUCKET",
            "REDIS_HOST",
            "CELERY_BROKER_URL",
        ]
        
        missing_variables = []
        for variable in critical_variables:
            if variable not in content:
                missing_variables.append(variable)
        
        assert not missing_variables, (
            f"Missing critical variables in .env.example: {missing_variables}. "
            f"All critical configuration variables must be documented."
        )
