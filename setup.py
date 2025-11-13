"""
Setup script for the Jira scraping pipeline.
"""
from setuptools import setup, find_packages

setup(
    name="jira-scraper",
    version="1.0.0",
    description="Data scraping and transformation pipeline for Apache Jira",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "tenacity>=8.2.3",
        "python-dotenv>=1.0.0",
        "tqdm>=4.66.1",
    ],
    python_requires=">=3.8",
)

