from github import Github
import base64

class GitHubService:
    def __init__(self, token):
        self.github = Github(token)
    
    def get_repository(self, repo_full_name):
        return self.github.get_repo(repo_full_name)
    
    def get_file_content(self, repo, file_path, ref='main'):
        try:
            file_content = repo.get_contents(file_path, ref=ref)
            if file_content.encoding == 'base64':
                return base64.b64decode(file_content.content).decode('utf-8')
            return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            return None
    
    def get_directory_structure(self, repo, path='', ref='main'):
        contents = []
        try:
            items = repo.get_contents(path, ref=ref)
            for item in items:
                if item.type == 'dir':
                    contents.append({
                        'path': item.path,
                        'type': 'directory'
                    })
                    contents.extend(self.get_directory_structure(repo, item.path, ref))
                else:
                    contents.append({
                        'path': item.path,
                        'type': 'file',
                        'size': item.size
                    })
        except Exception as e:
            pass
        return contents
    
    def get_relevant_files(self, repo, max_files=20):
        structure = self.get_directory_structure(repo)
        
        files = [item for item in structure if item['type'] == 'file']
        
        priority_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs']
        skip_patterns = ['node_modules', '.git', 'dist', 'build', '__pycache__']
        
        filtered_files = []
        for file_info in files:
            skip = False
            for pattern in skip_patterns:
                if pattern in file_info['path']:
                    skip = True
                    break
            if not skip:
                filtered_files.append(file_info)
        
        priority_files = [f for f in filtered_files if any(f['path'].endswith(ext) for ext in priority_extensions)]
        
        selected_files = priority_files[:max_files] if len(priority_files) > 0 else filtered_files[:max_files]
        
        files_with_content = []
        for file_info in selected_files:
            content = self.get_file_content(repo, file_info['path'])
            if content:
                files_with_content.append({
                    'path': file_info['path'],
                    'content': content
                })
        
        return files_with_content
    
    def create_pull_request(self, repo, title, body, head_branch, base_branch='main'):
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            return {
                'success': True,
                'pr_url': pr.html_url,
                'pr_number': pr.number
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_branch(self, repo, branch_name, source_branch='main'):
        source = repo.get_branch(source_branch)
        try:
            repo.create_git_ref(ref=f'refs/heads/{branch_name}', sha=source.commit.sha)
            return True
        except Exception as e:
            return False
    
    def update_file(self, repo, file_path, content, message, branch):
        try:
            file = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=file_path,
                message=message,
                content=content,
                sha=file.sha,
                branch=branch
            )
            return True
        except Exception as e:
            try:
                repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch
                )
                return True
            except Exception as create_error:
                return False
