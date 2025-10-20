import os

class LoadPrompts():
    @staticmethod
    def load_prompt_templates(folder_path:str, file_extension:str) -> dict:
        """Load all prompts from the prompts folders based on the file extension"""
        markdown_files = os.listdir(folder_path)
        markdown_prompt_templates = {}

        for file in markdown_files:
            file_path = folder_path / file
            root, extension = os.path.splitext(file_path.name)
            if extension == file_extension:
                with open(file_path, "r", encoding="utf-8") as f:
                    markdown_prompt_templates[file_path.name] = f.read()
        return markdown_prompt_templates