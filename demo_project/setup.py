#!/usr/bin/env python3
"""
Setup script for the demo project.
Uses older setuptools patterns to demonstrate package upgrade scenarios.
"""

from setuptools import setup, find_packages

# Reading requirements from file (older pattern)
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='demo-upgrade-project',
    version='1.0.0',
    description='Demo project with old package versions for upgrade testing',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Demo Author',
    author_email='demo@example.com',
    url='https://github.com/example/demo-upgrade-project',
    
    packages=find_packages(),
    
    # Using older setuptools patterns
    install_requires=requirements,
    
    # Older way of specifying Python version
    python_requires='>=3.7',
    
    # Entry points using older syntax
    entry_points={
        'console_scripts': [
            'demo-cli=cli_tool:cli',
            'demo-server=app:run_server',
        ],
    },
    
    # Older classifier format
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    
    # Older extras_require syntax
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'black>=21.0.0',
            'flake8>=3.8.0',
        ],
    },
)