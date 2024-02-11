import yaml
import re
from typing import Dict, Any
from .Logger import Logger
from ...config import Config
from ..storage_interface import StorageInterface


class AgentUtils:

    def __init__(self):
        self.config = Config()

    def load_agent_data(self, agent_name):
        try:
            self.config.reload()

            agent = self.config.find_agent_config(agent_name)
            settings = self.config.data['settings']

            # Check for a Persona override in the agent's configuration
            agent_persona_override = agent.get('Persona', None)

            # Use the overridden persona if available, or default to the system's predefined persona
            persona_file = agent_persona_override or settings['configuration']['Persona']

            # Check if the selected persona exists
            if persona_file not in self.config.data['personas']:
                raise FileNotFoundError(
                    f"Persona file for '{persona_file}' not found. Please check your persona configuration.")

            # Load the selected persona
            persona = self.config.data['personas'][persona_file]

            # Check for API and model_name overrides in the agent's ModelOverrides
            agent_api_override = agent.get('ModelOverrides', {}).get('API', None)
            agent_model_override = agent.get('ModelOverrides', {}).get('Model', None)

            # Use overrides if available, otherwise default to the settings
            api = agent_api_override or settings['models']['ModelSettings']['API']
            model = agent_model_override or settings['models']['ModelSettings']['Model']

            # Load default model parameter settings
            default_params = settings['models']['ModelSettings']['Params']

            # Load model-specific settings (if any)
            model_params = settings['models']['ModelLibrary'][api]['models'].get(model, {}).get('params', {})

            # Merge default settings with model-specific settings
            combined_params = {**default_params, **model_params}

            # Apply agent's parameter overrides (if any)
            agent_params_overrides = agent.get('ModelOverrides', {}).get('Params', {})
            final_model_params = {**combined_params, **agent_params_overrides}

            # Initialize agent data
            agent_data: Dict[str, Any] = dict(
                name=agent_name,
                settings=settings,
                llm=self.config.get_llm(api, model),
                params=final_model_params,
                prompts=agent['Prompts'],
                storage=StorageInterface().storage_utils,
                persona=persona,
            )

            return agent_data
        except FileNotFoundError as e:
            # Handle file not found errors specifically
            raise FileNotFoundError(f"Configuration or persona file not found: {e}")
        except KeyError as e:
            # Handle missing keys in configuration
            raise KeyError(f"Missing key in configuration: {e}")
        except Exception as e:
            # Handle other general exceptions
            raise Exception(f"Error loading agent data: {e}")

    # Might strip when removing salience
    def prepare_objective(self):
        while True:
            user_input = input("\nDefine Objective (leave empty to use defaults): ")
            if user_input.lower() == '':
                return None
            else:
                self.config.data['settings']['directives']['Objective'] = user_input
                return user_input

    def parse_yaml_string(self, yaml_string):
        try:
            cleaned_string = self.extract_yaml_block(yaml_string)
            return yaml.safe_load(cleaned_string)
        except yaml.YAMLError as e:
            raise ValueError(f"Error decoding YAML string: {e}")

    @staticmethod
    def extract_yaml_block(text):
        try:
            # Regex pattern to capture content between ```yaml and ```
            pattern = r"```yaml(.*?)```"
            match = re.search(pattern, text, re.DOTALL)

            if match:
                # Return the extracted content
                return match.group(1).strip()
            else:
                # Return None or an empty string if no match is found
                return None
        except Exception as e:
            # Handle unexpected errors during regex operation
            raise Exception(f"Error extracting YAML block: {e}")
