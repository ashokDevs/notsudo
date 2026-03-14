import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FormatterConfig:
    formatter_type: str
    format_command: str
    file_extensions: list[str]


EXTENSION_TO_FORMATTER = {
    # JavaScript/TypeScript/Web
    '.js': 'prettier',
    '.jsx': 'prettier',
    '.ts': 'prettier',
    '.tsx': 'prettier',
    '.json': 'prettier',
    '.css': 'prettier',
    '.scss': 'prettier',
    '.html': 'prettier',
    '.md': 'prettier',
    '.yaml': 'prettier',
    '.yml': 'prettier',
    '.py': 'black',
}


class FormatterDetectorService:
    PRETTIER_CONFIG_FILES = {
        '.prettierrc',
        '.prettierrc.json',
        '.prettierrc.js',
        '.prettierrc.cjs',
        '.prettierrc.mjs',
        '.prettierrc.yaml',
        '.prettierrc.yml',
        '.prettierrc.toml',
        'prettier.config.js',
        'prettier.config.cjs',
        'prettier.config.mjs',
    }

    ESLINT_CONFIG_FILES = {
        '.eslintrc',
        '.eslintrc.json',
        '.eslintrc.js',
        '.eslintrc.cjs',
        '.eslintrc.yaml',
        '.eslintrc.yml',
        'eslint.config.js',
        'eslint.config.mjs',
        'eslint.config.cjs',
    }

    PYTHON_FORMATTER_INDICATORS = {
        'black': ['[tool.black]', '[tool.black.'],
        'isort': ['[tool.isort]', '[tool.isort.'],
        'autopep8': ['[tool.autopep8]', '[autopep8]'],
    }

    def detect_formatters(self, repo_path: str) -> list[FormatterConfig]:
        formatters = []
        file_list = self._get_file_list(repo_path)
        filenames = {Path(f).name for f in file_list}
        
        # Check for Prettier
        prettier_config = self._detect_prettier(repo_path, filenames)
        if prettier_config:
            formatters.append(prettier_config)
            logger.info("formatter_detected", formatter="prettier")

        if not prettier_config:
            eslint_config = self._detect_eslint(filenames)
            if eslint_config:
                formatters.append(eslint_config)
                logger.info("formatter_detected", formatter="eslint")

        python_formatters = self._detect_python_formatters(repo_path, filenames)
        formatters.extend(python_formatters)
        
        if not formatters:
            logger.info("no_formatters_detected")
        
        return formatters

    def _get_file_list(self, repo_path: str) -> list[str]:
        files = []
        for root, dirs, filenames in os.walk(repo_path):
            # Skip .git and node_modules directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv'}]
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, repo_path)
                files.append(rel_path)
        return files

    def _detect_prettier(self, repo_path: str, filenames: set[str]) -> Optional[FormatterConfig]:
        has_prettier_config = bool(filenames & self.PRETTIER_CONFIG_FILES)

        if not has_prettier_config and 'package.json' in filenames:
            try:
                package_json_path = Path(repo_path) / 'package.json'
                if package_json_path.exists():
                    with open(package_json_path, 'r') as f:
                        package_data = json.load(f)
                    if 'prettier' in package_data:
                        has_prettier_config = True
                    elif 'devDependencies' in package_data and 'prettier' in package_data['devDependencies']:
                        has_prettier_config = True
                    elif 'dependencies' in package_data and 'prettier' in package_data['dependencies']:
                        has_prettier_config = True
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("package_json_parse_error", error=str(e))

        if has_prettier_config:
            return FormatterConfig(
                formatter_type='prettier',
                format_command='npx prettier --write {file}',
                file_extensions=['.js', '.jsx', '.ts', '.tsx', '.json', '.css', '.scss', '.html', '.md', '.yaml', '.yml']
            )

        return None

    def _detect_eslint(self, filenames: set[str]) -> Optional[FormatterConfig]:
        if filenames & self.ESLINT_CONFIG_FILES:
            return FormatterConfig(
                formatter_type='eslint',
                format_command='npx eslint --fix {file}',
                file_extensions=['.js', '.jsx', '.ts', '.tsx']
            )
        return None

    def _detect_python_formatters(self, repo_path: str, filenames: set[str]) -> list[FormatterConfig]:
        formatters = []

        if 'pyproject.toml' in filenames:
            try:
                pyproject_path = Path(repo_path) / 'pyproject.toml'
                if pyproject_path.exists():
                    content = pyproject_path.read_text()

                    if '[tool.black]' in content or 'black' in content.lower():
                        formatters.append(FormatterConfig(
                            formatter_type='black',
                            format_command='black {file}',
                            file_extensions=['.py']
                        ))
                        logger.info("formatter_detected", formatter="black")

                    if '[tool.isort]' in content:
                        formatters.append(FormatterConfig(
                            formatter_type='isort',
                            format_command='isort {file}',
                            file_extensions=['.py']
                        ))
                        logger.info("formatter_detected", formatter="isort")
            except IOError as e:
                logger.warning("pyproject_parse_error", error=str(e))

        return formatters

    def get_formatter_for_file(self, file_path: str, formatters: list[FormatterConfig]) -> Optional[FormatterConfig]:
        ext = Path(file_path).suffix.lower()

        for formatter in formatters:
            if ext in formatter.file_extensions:
                return formatter

        return None

    def get_format_command(self, file_path: str, formatter: FormatterConfig) -> str:
        return formatter.format_command.replace('{file}', file_path)


_formatter_detector_service: Optional[FormatterDetectorService] = None


def get_formatter_detector_service() -> FormatterDetectorService:
    global _formatter_detector_service
    if _formatter_detector_service is None:
        _formatter_detector_service = FormatterDetectorService()
    return _formatter_detector_service
