#!/usr/bin/env python3
"""
Generate documentation for the hospital simulation project using Sphinx and autodoc.

This script sets up and runs Sphinx to create HTML documentation
for all Python modules in the project. Documentation is saved to the ./docs directory.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def ensure_dir(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_docs():
    """Generate HTML documentation using Sphinx with autodoc."""
    # Get project root (parent of src directory)
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Add project root to Python path so modules can be found
    sys.path.insert(0, str(project_root))
    print(f"Adding {project_root} to Python path")
    
    # Set up paths
    docs_dir = project_root / 'docs'
    sphinx_src_dir = docs_dir / 'source'
    sphinx_build_dir = docs_dir / 'build' / 'html'
    
    # Clean previous build if exists
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    
    # Create docs directory structure
    ensure_dir(docs_dir)
    ensure_dir(sphinx_src_dir)
    ensure_dir(sphinx_src_dir / '_static')
    ensure_dir(sphinx_src_dir / '_templates')
    
    # Create Sphinx configuration file
    conf_content = '''# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'Hospital Simulation & AI Prediction System'
copyright = '2024, IA Medical Team'
author = 'IA Medical Team'
release = '1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
autodoc_member_order = 'bysource'
napoleon_google_docstring = True
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

# Add the project root directory to the Python path
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../src'))
'''
    
    with open(sphinx_src_dir / 'conf.py', 'w') as f:
        f.write(conf_content)
    
    # Create main index.rst file
    index_content = '''Hospital Simulation & AI Prediction System Documentation
=======================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   modules

Welcome to the Hospital Simulation & AI Prediction System documentation. 
This documentation is automatically generated from docstrings in the code.

Project Overview
----------------

This project provides a comprehensive hospital simulation system featuring:

* **Discrete Event Simulation**: Realistic hospital operations with patient arrivals and treatments
* **Real-time Monitoring**: Live hospital metrics with interactive dashboards
* **AI-Powered Predictions**: Machine learning models for danger prediction and forecasting
* **Multi-specialty Support**: Different medical specialties with varying characteristics
* **Data Analytics**: Comprehensive analysis of patient flow and resource utilization

The simulation uses SimPy for discrete event simulation, Flask for the web dashboard,
and scikit-learn for machine learning predictions.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
'''
    
    with open(sphinx_src_dir / 'index.rst', 'w') as f:
        f.write(index_content)
    
    # Create modules.rst
    modules_content = '''API Reference
=============

.. toctree::
   :maxdepth: 4

   src

'''
    
    with open(sphinx_src_dir / 'modules.rst', 'w') as f:
        f.write(modules_content)
    
    # Create src.rst for the main source directory
    src_content = '''src package
===========

.. automodule:: src
   :members:
   :undoc-members:
   :show-inheritance:

Subpackages
-----------

.. toctree::
   :maxdepth: 4

   src.data
   src.ml
   src.simulation
   src.utils
   src.visualizations

Submodules
----------

.. toctree::

   src.config
   src.run_dashboard
   src.run_ml
   src.run_simulation

'''
    
    with open(sphinx_src_dir / 'src.rst', 'w') as f:
        f.write(src_content)
    
    # Generate RST files for each package
    src_dir = project_root / 'src'
    packages = ['data', 'ml', 'simulation', 'utils', 'visualizations']
    
    for package in packages:
        package_dir = src_dir / package
        if package_dir.exists():
            # Find all Python files in the package
            py_files = list(package_dir.glob('*.py'))
            py_files = [f for f in py_files if f.name != '__init__.py']
            
            # Create package RST file
            package_content = f'''src.{package} package
{'=' * (len(package) + 12)}

.. automodule:: src.{package}
   :members:
   :undoc-members:
   :show-inheritance:

'''
            
            if py_files:
                package_content += '''Submodules
----------

.. toctree::

'''
                for py_file in py_files:
                    module_name = py_file.stem
                    package_content += f'   src.{package}.{module_name}\n'
                
                package_content += '\n'
                
                # Create individual module RST files
                for py_file in py_files:
                    module_name = py_file.stem
                    module_content = f'''src.{package}.{module_name} module
{'=' * (len(package) + len(module_name) + 12)}

.. automodule:: src.{package}.{module_name}
   :members:
   :undoc-members:
   :show-inheritance:
'''
                    
                    with open(sphinx_src_dir / f'src.{package}.{module_name}.rst', 'w') as f:
                        f.write(module_content)
            
            with open(sphinx_src_dir / f'src.{package}.rst', 'w') as f:
                f.write(package_content)
    
    # Create RST files for top-level modules
    top_level_modules = ['config', 'run_dashboard', 'run_ml', 'run_simulation']
    
    for module in top_level_modules:
        module_file = src_dir / f'{module}.py'
        if module_file.exists():
            module_content = f'''src.{module} module
{'=' * (len(module) + 11)}

.. automodule:: src.{module}
   :members:
   :undoc-members:
   :show-inheritance:
'''
            
            with open(sphinx_src_dir / f'src.{module}.rst', 'w') as f:
                f.write(module_content)
    
    # Try to install required packages
    try:
        print("Installing documentation dependencies...")
        subprocess.run([
            sys.executable, 
            "-m", "pip", "install", 
            "sphinx", "sphinx_rtd_theme"
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Could not install required packages. Please run:")
        print("pip install sphinx sphinx_rtd_theme")
        return False
    
    # Build the documentation
    try:
        print("Building documentation...")
        
        # Run sphinx-build
        result = subprocess.run([
            sys.executable,
            "-m", "sphinx",
            "-b", "html",
            str(sphinx_src_dir),
            str(sphinx_build_dir)
        ], check=True, capture_output=True, text=True, cwd=str(project_root))
        
        print(f"Documentation successfully generated in {sphinx_build_dir}")
        print(f"Open {sphinx_build_dir / 'index.html'} in your browser to view")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error building documentation: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

if __name__ == "__main__":
    success = generate_docs()
    if not success:
        sys.exit(1)