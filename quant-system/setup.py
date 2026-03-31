# -*- coding: utf-8 -*-
"""
Quant System 安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取 README
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = '多维量化交易系统'

# 读取 requirements
requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
if os.path.exists(requirements_path):
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = []

setup(
    name='quant-system',
    version='1.0.0',
    author='Quant Team',
    author_email='quant@example.com',
    description='多维量化交易系统',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/quant-system',
    packages=find_packages(exclude=['tests', 'tests.*', 'docs', 'data', 'logs']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Office/Business :: Financial :: Investment',
    ],
    python_requires='>=3.8',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.1.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
        'docs': [
            'sphinx>=4.5.0',
            'sphinx-rtd-theme>=1.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'quant-system=main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
