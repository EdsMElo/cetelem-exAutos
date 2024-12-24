import os
import subprocess
import sys
import venv

# Função para criar o ambiente virtual
def create_virtual_env(env_dir='.venv-exAutos'):
    """Cria um ambiente virtual."""
    venv.EnvBuilder(with_pip=True).create(env_dir)

# Função para ativar o ambiente virtual e instalar dependências
def install_requirements(env_dir='.venv-exAutos'):
    """Ativa o ambiente virtual e instala os pacotes do requirements.txt."""
    if os.name == 'nt':
        activate_script = os.path.join(env_dir, 'Scripts', 'activate.bat')
        python_executable = os.path.join(env_dir, 'Scripts', 'python.exe')
    else:
        activate_script = os.path.join(env_dir, 'bin', 'activate')
        python_executable = os.path.join(env_dir, 'bin', 'python')

    # Instalar dependências usando o pip do ambiente virtual
    subprocess.check_call([python_executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

if __name__ == '__main__':
    env_dir = '.venv-exAutos'
    print(f"Creating virtual environment in {env_dir}...")
    create_virtual_env(env_dir)
    
    print("Installing requirements...")
    install_requirements(env_dir)
    
    print("Setup complete. Virtual environment is ready.")