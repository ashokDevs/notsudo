from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StackConfig:
    stack_type: str
    runtime: str
    package_manager: str
    install_command: str
    test_command: str
    build_command: Optional[str] = None
    typecheck_command: Optional[str] = None
    dockerfile_path: Optional[str] = None
    docker_compose_path: Optional[str] = None


STACK_CONFIGS = {
    'python': StackConfig(
        stack_type='python',
        runtime='python:3.11-slim',
        package_manager='pip',
        install_command='pip install -r requirements.txt',
        test_command='pytest',
        build_command=None,
        typecheck_command=None  # Will be set dynamically if mypy configured
    ),
    'python-poetry': StackConfig(
        stack_type='python',
        runtime='python:3.11-slim',
        package_manager='poetry',
        install_command='pip install poetry && poetry install',
        test_command='poetry run pytest',
        build_command=None,
        typecheck_command=None  # Will be set dynamically if mypy configured
    ),
    'nodejs-npm': StackConfig(
        stack_type='nodejs',
        runtime='node:20-slim',
        package_manager='npm',
        install_command='npm install',
        test_command='npm test',
        build_command='npm run build',
        typecheck_command=None  # Will be set dynamically if tsconfig.json exists
    ),
    'nodejs-yarn': StackConfig(
        stack_type='nodejs',
        runtime='node:20-slim',
        package_manager='yarn',
        install_command='yarn install',
        test_command='yarn test',
        build_command='yarn build',
        typecheck_command=None  # Will be set dynamically if tsconfig.json exists
    ),
    'nodejs-pnpm': StackConfig(
        stack_type='nodejs',
        runtime='node:20-slim',
        package_manager='pnpm',
        install_command='pnpm install',
        test_command='pnpm test',
        build_command='pnpm build',
        typecheck_command=None  # Will be set dynamically if tsconfig.json exists
    ),
}


class StackDetectorService:
    MARKER_FILES = {
        'requirements.txt': 'python',
        'pyproject.toml': 'python-poetry',
        'setup.py': 'python',
        'package.json': 'nodejs',
        'pom.xml': 'java',
        'build.gradle': 'java',
        'go.mod': 'go',
        'Cargo.toml': 'rust',
    }
    
    DOCKER_FILES = {
        'Dockerfile',
        'dockerfile',
    }
    
    DOCKER_COMPOSE_FILES = {
        'docker-compose.yml',
        'docker-compose.yaml',
        'compose.yml',
        'compose.yaml',
    }

    def detect_from_file_list(self, file_paths: list[str]) -> Optional[StackConfig]:
        filenames = {path.split('/')[-1] for path in file_paths}
        path_map = {path.split('/')[-1]: path for path in file_paths}
        
        # Detect base stack config
        stack_config = self._detect_stack(filenames)
        if stack_config is None:
            return None
        
        # Detect Docker configuration and enhance the config
        dockerfile_path = self._find_dockerfile(file_paths)
        compose_path = self._find_docker_compose(file_paths)
        
        # Detect type checking configuration
        typecheck_command = self._detect_typecheck_config(filenames, stack_config)
        
        # Return new config with enhancements if any
        from dataclasses import replace
        return replace(
            stack_config,
            dockerfile_path=dockerfile_path,
            docker_compose_path=compose_path,
            typecheck_command=typecheck_command
        )
    
    def _detect_typecheck_config(self, filenames: set[str], stack_config: StackConfig) -> Optional[str]:
        """Detect type checking configuration and return appropriate command."""
        if stack_config.stack_type == 'nodejs':
            # TypeScript: check for tsconfig.json
            if 'tsconfig.json' in filenames:
                return 'npx tsc --noEmit'
        
        elif stack_config.stack_type == 'python':
            # Python: check for mypy configuration
            if 'mypy.ini' in filenames or '.mypy.ini' in filenames:
                if stack_config.package_manager == 'poetry':
                    return 'poetry run mypy .'
                return 'mypy --ignore-missing-imports .'
            # Also check pyproject.toml for [tool.mypy] section (simplified check)
            if 'pyproject.toml' in filenames:
                # For poetry projects with pyproject.toml, enable mypy if available
                if stack_config.package_manager == 'poetry':
                    return 'poetry run mypy . || true'  # Don't fail if mypy not installed
        
        return None
    
    def _detect_stack(self, filenames: set[str]) -> Optional[StackConfig]:
        """Detect the base technology stack from filenames."""
        if 'package.json' in filenames:
            if 'yarn.lock' in filenames:
                return STACK_CONFIGS['nodejs-yarn']
            elif 'pnpm-lock.yaml' in filenames:
                return STACK_CONFIGS['nodejs-pnpm']
            else:
                return STACK_CONFIGS['nodejs-npm']
        
        if 'pyproject.toml' in filenames:
            return STACK_CONFIGS['python-poetry']
        
        if 'requirements.txt' in filenames or 'setup.py' in filenames:
            return STACK_CONFIGS['python']
        
        return None
    
    def _find_dockerfile(self, file_paths: list[str]) -> Optional[str]:
        """Find Dockerfile in the file list, preferring root-level files."""
        # Priority order: root Dockerfile > nested Dockerfile
        candidates = []
        for path in file_paths:
            filename = path.split('/')[-1]
            if filename.lower() == 'dockerfile':
                depth = path.count('/')
                candidates.append((depth, path))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        # Check for .devcontainer Dockerfile
        for path in file_paths:
            if '.devcontainer' in path and 'dockerfile' in path.lower():
                return path
        
        return None
    
    def _find_docker_compose(self, file_paths: list[str]) -> Optional[str]:
        """Find docker-compose file in the file list."""
        for path in file_paths:
            filename = path.split('/')[-1]
            if filename in self.DOCKER_COMPOSE_FILES:
                return path
        return None
    
    def has_docker_config(self, file_paths: list[str]) -> bool:
        """Check if the project has any Docker configuration."""
        return (
            self._find_dockerfile(file_paths) is not None or
            self._find_docker_compose(file_paths) is not None
        )

    def detect_from_github_repo(self, github_service, repo) -> Optional[StackConfig]:
        structure = github_service.get_directory_structure(repo, path='', ref='main')
        file_paths = [item['path'] for item in structure if item['type'] == 'file']
        return self.detect_from_file_list(file_paths)

